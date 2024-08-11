from __future__ import annotations

import itertools
import json
import logging
import time
from collections import defaultdict
from functools import wraps
from typing import List

import litellm
from agentkit.actions.action import Action, ActionHandlers
from agentkit.llms.general.tools import Tools
from agentkit.telemetry import traceable
from agentkit.utils import DEFAULT_ACTION_SCOPE
from agentkit.utils.stream import get_first_element_and_iterator, merge_dicts
from agentkit.utils.tokens import TokenUsageTracker
from openai import Stream
from openai.types.chat.chat_completion_message import ChatCompletionMessage
from openai.types.chat.chat_completion_message_tool_call import ChatCompletionMessageToolCall


class ChatCompletionException(Exception):
    def __init__(self, message="", extra_info=None):
        super().__init__(message)
        self.extra_info = extra_info or {}

    def __str__(self):
        extra_info_str = ", ".join(f"{key}: {value}" for key, value in self.extra_info.items())
        return f"{super().__str__()} | Additional Info: [{extra_info_str}]"


class ChatCompletion:
    DEFAULT_LOGGING_NAME = "agentkit_chat_completion"

    def __init__(
        self,
        model=None,
        token_usage_tracker=None,
        logger: logging.Logger | None = None,
        logging_name: str | None = None,
        logging_metadata: dict | None = None,
        logging_level=logging.INFO,
    ):
        self.model = model
        self.token_usage_tracker = token_usage_tracker or TokenUsageTracker()
        self.logger = logger
        self.logging_name = logging_name or self.DEFAULT_LOGGING_NAME
        self.logging_metadata = logging_metadata
        self.logging_level = logging_level

    @classmethod
    def create(cls, **kwargs):
        instance = cls(**kwargs)
        if instance.logger:
            return traceable(
                name=instance.logging_name,
                logger=instance.logger,
                metadata=instance.logging_metadata,
                level=instance.logging_level,
            )(instance)
        return instance

    def validate_orch(self, orch):
        if orch is not None:
            for key in orch.keys():
                if not isinstance(key, str):
                    raise ChatCompletionException(
                        f"Orch keys must be action name (str), found {type(key)}"
                    )

    def build_orch(self, actions: List[Action], orch=None):
        action_handler = ActionHandlers()

        if orch is None:
            orch = {}
        if DEFAULT_ACTION_SCOPE not in orch:
            orch[DEFAULT_ACTION_SCOPE] = actions

        buf = actions + list(orch.values())
        for element in buf:
            if isinstance(element, list):
                for e in element:
                    action_handler.name_to_action[e.name] = e
            elif isinstance(element, Action):
                action_handler.name_to_action[element.name] = element

        for _, action in action_handler.name_to_action.items():
            if action.name not in orch:
                orch[action.name] = DEFAULT_ACTION_SCOPE

        return action_handler, orch

    def argument_check(self, **kwargs):
        if "messages" not in kwargs:
            raise ChatCompletionException(
                "messages keyword argument is required for chat completion"
            )
        if "model" not in kwargs and not self.model:
            raise ChatCompletionException("model keyword argument is required for chat completion")
        if "tools" in kwargs:
            raise ChatCompletionException(
                "tools keyword argument is not allowed for this method, use actions instead"
            )
        if "tool_choice" in kwargs:
            raise ChatCompletionException(
                "tool_choice keyword argument is not allowed for this method, use actions instead"
            )

    def invoke_tool(self, messages, model, response_msg, tool_calls, action_handler, orch, tools):
        messages += [response_msg]
        called_tools = defaultdict(list)

        for tool_call in tool_calls:
            if isinstance(tool_call, ChatCompletionMessageToolCall):
                tool_call = tool_call.model_dump()

            name = tool_call["function"]["name"]
            arguments = tool_call["function"]["arguments"]

            if action_handler.contains(name):
                try:
                    arguments = json.loads(arguments)
                except json.decoder.JSONDecodeError as e:
                    raise ChatCompletionException(
                        "Failed to parse function call arguments from OpenAI response",
                        extra_info={
                            "arguments": arguments,
                            "timestamp": time.time(),
                            "model": model,
                        },
                    ) from e

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
                raise ChatCompletionException(
                    f"{name} is not a valid function name",
                    extra_info={"timestamp": time.time(), "model": model},
                )

        if len(called_tools) == 1:
            name = list(called_tools.keys())[0]
            expr = orch[name] if orch[name] != DEFAULT_ACTION_SCOPE else orch[DEFAULT_ACTION_SCOPE]
            return Tools.from_expr(expr), (stop, called_tools[name])
        else:
            return tools, (False, list(called_tools.values()))

    def handle_stream_response(self, api_response):
        first_element, iterator = get_first_element_and_iterator(api_response)

        if first_element.choices[0].delta.content is not None:
            return iterator
        else:
            l = list(iterator)
            deltas = {}
            for element in l:
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

            if "function_call" in deltas:
                del deltas["function_call"]

            first_element.choices[0].message = ChatCompletionMessage(**deltas)
            return first_element

    @wraps(litellm.completion)
    def __call__(self, *args, **kwargs):
        return self.create_chat_completion(*args, **kwargs)

    def create_chat_completion(self, *args, **kwargs):
        self.argument_check(**kwargs)

        if "model" not in kwargs and self.model:
            kwargs["model"] = self.model

        actions = kwargs.pop("actions", None)
        orch = kwargs.pop("orch", None)

        if actions is None:
            raise ChatCompletionException("actions must be provided")

        self.validate_orch(orch)
        action_handler, orch = self.build_orch(actions, orch)
        tools = Tools.from_expr(orch[DEFAULT_ACTION_SCOPE])

        messages = kwargs.get("messages")
        model = kwargs.get("model")

        chat_completion_create_method = self.get_chat_completion_method()

        while True:
            api_response = chat_completion_create_method(
                *args,
                **kwargs,
                **(tools.to_arguments() if bool(tools) else {}),
            )

            if isinstance(api_response, Stream):
                api_response = self.handle_stream_response(api_response)
                if isinstance(api_response, itertools._tee):
                    return api_response
            else:
               if hasattr(api_response, 'usage'):
                    self.token_usage_tracker.track_usage(api_response.usage)

            choice = api_response.choices[0]
            message = choice.message

            if message.tool_calls:
                tools, (stop, resp) = self.invoke_tool(
                    messages, model, message, message.tool_calls, action_handler, orch, tools
                )
                if stop:
                    return resp
            elif message.content is not None:
                if choice.finish_reason == "stop":
                    return api_response
            else:
                raise ChatCompletionException(
                    f"Unsupported response from OpenAI api: {api_response}"
                )

    def get_chat_completion_method(self):
        if self.logger:
            return traceable(
                name=f"{self.logging_name}.chat.completions.create",
                logger=self.logger,
                metadata=self.logging_metadata,
                level=self.logging_level,
            )(litellm.completion)
        else:
            return litellm.completion


def completion(*args, **kwargs):
    """
    A standalone function that creates a ChatCompletion instance and calls it.
    This function supports both simple usage and usage with logging.
    """
    # Extract ChatCompletion-specific kwargs
    completion_kwargs = {
        k: kwargs.pop(k)
        for k in [
            "model",
            "logger",
            "logging_name",
            "logging_metadata",
            "logging_level",
        ]
        if k in kwargs
    }


    # Extract TokenUsageTracker
    token_usage_tracker = kwargs.pop("token_usage_tracker", None)

    # Create a ChatCompletion instance
    chat_completion = ChatCompletion.create(
        token_usage_tracker=token_usage_tracker, **completion_kwargs
    )

    # Call the instance with the remaining args and kwargs
    return chat_completion(*args, **kwargs)
