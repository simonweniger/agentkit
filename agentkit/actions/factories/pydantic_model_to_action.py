import uuid
from typing import Callable
from typing import List

from pydantic import BaseModel

from agentkit.actions import Action
from agentkit.actions.factories.function import action


def truncated_uuid4():
    return str(uuid.uuid4())[:8]


def action_from_model(
    model: BaseModel,
    stop=True,
    name: str = None,
    description: str = None,
    decorators: List[Callable[..., None]] = [],
) -> Action:
    def func(*args, **kwargs):
        if args:
            raise ValueError(
                f"Invalid input: The method should not have positional arguments and should only accept keyword arguments: {model.__name__.lower()} of type {model.__name__}",
                f"args: {args}",
                f"kwargs: {kwargs}",
            )

        return model.model_validate(kwargs)

    if name is None:
        name = f"Create{model.__name__}"

    if description is None:
        description = f"Extract {model.__name__}"

    func.__doc__ = description
    func.__name__ = f"create_{model.__name__.lower()}_from_pydantic_model"

    return action(
        name=name,
        pydantic_model=model,
        stop=stop,
        decorators=decorators,
    )(func)
