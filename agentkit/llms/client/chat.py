from __future__ import annotations

import itertools
import json
import logging
import time
from collections import defaultdict
from typing import List

from agentkit.actions.action import Action
from agentkit.actions.action import ActionHandlers
from agentkit.llms.client.tools import Tools
from agentkit.telemetry import traceable
from agentkit.utils import DEFAULT_ACTION_SCOPE
from agentkit.utils.stream import get_first_element_and_iterator
from agentkit.utils.stream import merge_dicts
from agentkit.utils.tokens import TokenUsageTracker
from litellm import completion
from openai import Stream
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall


class AIChatCompletionException(Exception):
    def __init__(self, message="", extra_info=None):
        super().__init__(message)
        self.extra_info = extra_info or {}

    def __str__(self):
        # Customize the string representation to include extra_info
        extra_info_str = ", ".join(f"{key}: {value}" for key, value in self.extra_info.items())
        return f"{super().__str__()} | Additional Info: [{extra_info_str}]"


class AIChatCompletion:
    def __init__(self, model, token_usage_tracker=None, logger=None):
        self.model = model
        self.logger = logger or logging.getLogger(__name__)
        self.token_usage_tracker = token_usage_tracker or TokenUsageTracker()
        # self.client = OpenAI()

    @staticmethod
    def _invoke_tool(
        messages,
        model,
        response_msg,
        tool_calls,
        tools,
        orch,
        action_handler: ActionHandlers,
    ):
        messages += [response_msg]

        # if multiple type of functions are invoked, ignore orch and `stop` option
        called_tools = defaultdict(list)

        # TODO: right now invoke all tools iteratively, implement async tool invocation
        for tool_call in tool_calls:
            if isinstance(tool_call, ChatCompletionMessageToolCall):
                tool_call = tool_call.model_dump()

            name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]

            if action_handler.contains(name):
                try:
                    arguments = json.loads(tool_call["function"]["arguments"])
                except json.decoder.JSONDecodeError as e:
                    raise AIChatCompletionException(
                        e,
                        extra_info={
                            "message": "Parsing function call arguments from OpenAI response ",
                            "arguments": tool_call["function"]["arguments"],
                            "timestamp": time.time(),
                            "model": model,
                        },
                    ) from e

                # Invoke action
                tool_response = action_handler[name](**arguments)

                called_tools[name].append(tool_response)

                stop = action_handler[name].stop
                messages += [
                    {
                        "tool_call_id": tool_call["id"],
                        "role": "tool",
                        "name": name,
                        "content": str(tool_response),
                    },
                ]

            else:
                # TODO: allow user to add callback for unavailable tool
                unavailable_tool_msg = f"""{name} is not a valid tool name, use one of the following:
                {', '.join([tool['function']['name'] for tool in tools.tools])}"""  # noqa: E501

                raise AIChatCompletionException(unavailable_tool_msg)

        if len(called_tools) == 1:
            # Update new functions for next OpenAI api call
            name = list(called_tools.keys())[0]

            # use tools in orch[DEFAULT_ACTION_SCOPE] if expr is DEFAULT_ACTION_SCOPE
            expr = orch[name] if orch[name] != DEFAULT_ACTION_SCOPE else orch[DEFAULT_ACTION_SCOPE]
            return (
                Tools.from_expr(
                    expr,
                ),
                (stop, called_tools[name]),
            )
        else:
            # if multiple type of functions are invoked, use the same set of tools next api call
            return (
                tools,
                (False, list(called_tools.values())),
            )

    @staticmethod
    def _handle_stream_response(api_response):
        first_element, iterator = get_first_element_and_iterator(api_response)

        if first_element.choices[0].delta.content is not None:
            # if the first element is a message, return generator right away.
            return iterator
        else:
            # if the first element is a tool call, merge all tool calls into first response and return it  # noqa: E501
            tool_call_elements = list(iterator)

            deltas = {}
            for element in tool_call_elements:
                delta = element.choices[0].delta.model_dump()
                deltas = merge_dicts(deltas, delta)

            chat_completion_message_tool_call = defaultdict(dict)
            for tool_delta in deltas["tool_calls"]:
                chat_completion_message_tool_call[tool_delta["index"]] = merge_dicts(
                    chat_completion_message_tool_call[tool_delta["index"]],
                    tool_delta,
                )
                tool_delta.pop("index")

            deltas["tool_calls"] = list(chat_completion_message_tool_call.values())

            # (HACK) Remove the 'function_call' field, otherwise calling the API will fail
            if "function_call" in deltas:
                del deltas["function_call"]

            first_element.choices[0].message = ChatCompletionMessage(**deltas)

            return first_element

    @staticmethod
    def build_orch(actions: List[Action] = None, orch=None):
        action_handler = ActionHandlers()
        orch = AIChatCompletion._initialize_orch(actions, orch)
        AIChatCompletion._populate_action_handler(action_handler, actions, orch)
        AIChatCompletion._set_default_orch(action_handler, orch)
        return action_handler, orch

    @staticmethod
    def _initialize_orch(actions, orch):
        orch = orch or {}
        if DEFAULT_ACTION_SCOPE not in orch:
            orch[DEFAULT_ACTION_SCOPE] = actions
        return orch

    @staticmethod
    def _populate_action_handler(action_handler, actions, orch):
        for element in itertools.chain(actions or [], orch.values()):
            if isinstance(element, list):
                for action in element:
                    action_handler.name_to_action[action.name] = action
            elif isinstance(element, Action):
                action_handler.name_to_action[element.name] = element

    @staticmethod
    def _set_default_orch(action_handler, orch):
        for action_name in action_handler.name_to_action:
            if action_name not in orch:
                orch[action_name] = DEFAULT_ACTION_SCOPE

    def create(
        self,
        orch=None,
        actions: List[Action] = None,
        *args,
        **kwargs,
    ):
        if "model" not in kwargs:
            kwargs["model"] = self.model
        logging.info("Creating chat completion in tools")

        return AIChatCompletion.wrap_chat_completion_create(completion)(
            *args,
            actions=actions,
            orch=orch,
            logger=self.logger,
            token_usage_tracker=self.token_usage_tracker,
            **kwargs,
        )

    @staticmethod
    def validate_orch(orch):
        if orch is not None:
            for key in orch.keys():
                if not isinstance(key, str):
                    raise AIChatCompletionException(
                        f"Orch keys must be action name (str), found {type(key)}"
                    )

    @staticmethod
    def wrap_chat_completion_create(original_create_method):
        def wrapper_for_logging(
            *args,
            logger=None,
            logging_name=None,
            logging_metadata=None,
            logging_level=logging.INFO,
            **kwargs,
        ):
            # DEFAULT_LOGGING_NAME = "actionweaver_initial_chat_completion"
            def new_create(actions=None, orch=None, token_usage_tracker=None, *args, **kwargs):
                AIChatCompletion.validate_orch(orch)
                chat_completion_create_method = AIChatCompletion._get_create_method(
                    original_create_method,
                    logger,
                    logging_name,
                    logging_metadata,
                    logging_level,
                )
                token_usage_tracker = token_usage_tracker or TokenUsageTracker()
                AIChatCompletion._validate_required_args(kwargs)
                action_handler, orch = AIChatCompletion.build_orch(actions or [], orch)
                return AIChatCompletion._process_chat_completion(
                    chat_completion_create_method,
                    action_handler,
                    orch,
                    token_usage_tracker,
                    *args,
                    **kwargs,
                )

            return new_create(*args, **kwargs) if logger else new_create(*args, **kwargs)

        return wrapper_for_logging

    @staticmethod
    def _get_create_method(original_method, logger, logging_name, logging_metadata, logging_level):
        if not logger:
            return original_method
        return traceable(
            name=f"{logging_name or 'agentkit_initial_chat_completion'}.chat.completions.create",
            logger=logger,
            metadata=logging_metadata,
            level=logging_level,
        )(original_method)

    @staticmethod
    def _validate_required_args(kwargs):
        if "messages" not in kwargs:
            raise AIChatCompletionException(
                "messages keyword argument is required for chat completion"
            )
        if "model" not in kwargs:
            raise AIChatCompletionException(
                "model keyword argument is required for chat completion"
            )

    @staticmethod
    def _process_chat_completion(
        create_method, action_handler, orch, token_usage_tracker, *args, **kwargs
    ):
        messages = kwargs.get("messages")
        model = kwargs.get("model")
        tools = Tools.from_expr(orch[DEFAULT_ACTION_SCOPE])

        while True:
            api_response = AIChatCompletion._make_api_call(create_method, tools, *args, **kwargs)
            if isinstance(api_response, Stream):
                return AIChatCompletion._handle_stream_response(api_response)

            token_usage_tracker.track_usage(api_response.usage)
            response = AIChatCompletion._process_api_response(
                api_response, messages, model, tools, orch, action_handler
            )

            if response is not None:
                return response

    @staticmethod
    def _process_api_response(api_response, messages, model, tools, orch, action_handler):
        choice = api_response.choices[0]
        message = choice.message

        if message.tool_calls:
            tools, (stop, resp) = AIChatCompletion._invoke_tool(
                messages, model, message, message.tool_calls, tools, orch, action_handler
            )
            return resp if stop else None
        elif message.content is not None:
            return api_response if choice.finish_reason == "stop" else None
        else:
            raise AIChatCompletionException(
                f"Unsupported response from OpenAI api: {api_response}"
            )

    @staticmethod
    def _make_api_call(create_method, tools, *args, **kwargs):
        tools_argument = tools.to_arguments()
        if tools_argument["tools"]:
            return create_method(*args, **kwargs, **tools_argument)
        else:
            return create_method(*args, **kwargs)
