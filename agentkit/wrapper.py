import logging

from litellm import completion
from litellm import completion_with_fallbacks
from litellm import model_list

from agentkit.llms.client.tools.chat_loop import create_chat_loop


class Agent:
    def __init__(
        self,
        fallbacks: bool = False,
        api_key: str | None = None,
        model: model_list = "gpt-4o-mini",
    ):
        self.api_key = api_key
        self.model = model
        self.chat_loop = create_chat_loop(completion_with_fallbacks if fallbacks else completion)

    def create(self, *args, **kwargs):
        logging.info("Creating chat loop.")
        kwargs.update(model=self.model)
        if self.api_key:
            kwargs["api_key"] = self.api_key
        return self.chat_loop(*args, **kwargs)
