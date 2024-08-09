from __future__ import annotations

import itertools
import logging
from typing import List
from typing import Optional

import agentkit.llms.loop_action as la
from agentkit.actions.action import Action
from agentkit.llms.client.chat import AIChatCompletion
from agentkit.llms.client.chat import AIChatCompletionException
from agentkit.llms.client.tools import Tools
from agentkit.llms.exception_handler import ChatLoopInfo
from agentkit.llms.exception_handler import ExceptionHandler
from agentkit.telemetry import traceable
from agentkit.utils import DEFAULT_ACTION_SCOPE
from agentkit.utils.tokens import TokenUsageTracker
from litellm import completion
from litellm import completion_with_fallbacks
from litellm import model_list
from openai import Stream


class FunctionCallingLoopException(AIChatCompletionException):
    pass


class Agent(AIChatCompletion):
    def __init__(
        self,
        fallbacks: bool = False,
        api_key: str | None = None,
        model: model_list = "gpt-4o-mini",
        token_usage_tracker=None,
        logger=None,
    ):
        super().__init__(model, token_usage_tracker, logger)
        self.api_key = api_key
        self.model = model
        self.chat_loop = self.create_chat_loop(
            completion_with_fallbacks if fallbacks else completion
        )

    def create_chat_loop(self, original_create_method):
        def wrapper_for_logging(
            *args,
            logger: logging.Logger | None = None,
            logging_name: Optional[str] = None,
            logging_metadata: Optional[dict] = None,
            logging_level=logging.INFO,
            exception_handler: ExceptionHandler = None,
            **kwargs,
        ):
            DEFAULT_LOGGING_NAME = "agentkit_initial_chat_completion"

            def new_create(
                actions: List[Action] = [],
                orch=None,
                token_usage_tracker=None,
                *args,
                **kwargs,
            ):
                self.validate_orch(orch)

                chat_completion_create_method = original_create_method
                if logger:
                    chat_completion_create_method = traceable(
                        name=(logging_name or DEFAULT_LOGGING_NAME) + ".chat.completions.create",
                        logger=logger,
                        metadata=logging_metadata,
                        level=logging_level,
                    )(original_create_method)

                if token_usage_tracker is None:
                    token_usage_tracker = TokenUsageTracker()

                self.argument_check(*args, **kwargs)

                messages = kwargs.get("messages")
                model = kwargs.get("model")

                action_handler, orch = self.build_orch(actions, orch)

                tools = Tools.from_expr(orch[DEFAULT_ACTION_SCOPE])
                chat_loop_action = la.Unknown

                while True:
                    try:
                        if bool(tools):
                            tools_argument = tools.to_arguments()
                            api_response = chat_completion_create_method(
                                *args,
                                **kwargs,
                                **tools_argument,
                            )
                        else:
                            api_response = chat_completion_create_method(
                                *args,
                                **kwargs,
                            )

                        chat_loop_action = self.handle_response(
                            api_response,
                            token_usage_tracker,
                            messages,
                            model,
                            tools,
                            orch,
                            action_handler,
                            logger,
                        )
                    except Exception as e:
                        if exception_handler:
                            chat_loop_action = exception_handler.handle_exception(
                                e,
                                ChatLoopInfo(
                                    context={
                                        "response": api_response,
                                        "tools": tools,
                                        "messages": messages,
                                        "model": model,
                                        "orch": orch,
                                    }
                                ),
                            )

                        else:
                            raise e

                    if isinstance(chat_loop_action, la.ReturnRightAway):
                        return chat_loop_action.content
                    elif isinstance(chat_loop_action, la.Continue):
                        tools = chat_loop_action.functions
                    else:
                        raise FunctionCallingLoopException(
                            f"Unsupported chat loop action: {chat_loop_action}"
                        )

            if logger:
                return traceable(
                    name=logging_name or DEFAULT_LOGGING_NAME,
                    logger=logger,
                    metadata=logging_metadata,
                    level=logging_level,
                )(new_create)(*args, **kwargs)
            else:
                return new_create(*args, **kwargs)

        return wrapper_for_logging

    def create(self, *args, **kwargs):
        logging.info("Creating chat loop.")
        kwargs.update(model=self.model)
        if self.api_key:
            kwargs["api_key"] = self.api_key
        return self.chat_loop(*args, **kwargs)

    @staticmethod
    def argument_check(
        *args,
        **kwargs,
    ):
        if "messages" not in kwargs:
            raise FunctionCallingLoopException(
                "messages keyword argument is required for chat completion"
            )
        if "model" not in kwargs:
            raise FunctionCallingLoopException(
                "model keyword argument is required for chat completion"
            )

        if "tools" in kwargs:
            raise FunctionCallingLoopException(
                "tools keyword argument is not allowed for this method, use actions instead"
            )

        if "tool_choice" in kwargs:
            raise FunctionCallingLoopException(
                "tool_choice keyword argument is not allowed for this method, use actions instead"
            )

    def handle_response(
        self,
        api_response,
        token_usage_tracker,
        messages,
        model,
        tools,
        orch,
        action_handler,
        logger=None,
    ) -> la.LoopAction:
        # logic to handle streaming API response
        if isinstance(api_response, Stream):
            api_response = self._handle_stream_response(api_response)

            if isinstance(api_response, itertools._tee):
                # if it's a tee object, return right away
                return la.ReturnRightAway(content=api_response)
        else:
            token_usage_tracker.track_usage(api_response.usage)

        choice = api_response.choices[0]
        message = choice.message

        if message.tool_calls:
            tools, (stop, resp) = self._invoke_tool(
                messages,
                model,
                message,
                message.tool_calls,
                tools,
                orch,
                action_handler,
            )
            if stop:
                return la.ReturnRightAway(content=resp)
            else:
                return la.Continue(functions=tools)
        elif message.content is not None:
            # ignore last message in the function loop
            # messages += [{"role": "assistant", "content": message["content"]}]
            if choice.finish_reason == "stop":
                """
                Stop Reasons:

                - Occurs when the API returns a message that is complete or is concluded by one of the stop sequences defined via the 'stop' parameter.

                See https://platform.openai.com/docs/guides/gpt/chat-completions-api for details.
                """

                return la.ReturnRightAway(content=api_response)
        else:
            raise FunctionCallingLoopException(
                f"Unsupported response from OpenAI api: {api_response}"
            )
