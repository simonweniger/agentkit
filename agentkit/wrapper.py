from openai import OpenAI

from agentkit.llms.client.tools.chat_loop import create_chat_loop


class ActionWeaverLLMClientWrapper:
    def __init__(self, client:OpenAI):

        self.client = client
        if type(client) == OpenAI:
            self.chat_loop = create_chat_loop(client.chat.completions.create)
        else:
            raise NotImplementedError(f"Client type {type(client)} is not supported.")

    def create(self, *args, **kwargs):
        return self.chat_loop(*args, **kwargs)


def wrap(client: OpenAI):
    return ActionWeaverLLMClientWrapper(client)
