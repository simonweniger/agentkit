from typing import List

from agentkit.actions import Action
from agentkit.actions.factories.function import action
from agentkit.utils.pydantic_utils import create_pydantic_model_from_func


def default_reducer(results):
    return "\n".join(str(e) for e in results)


def validate_input(args, kwargs, act_name):
    if args or len(kwargs) > 1:
        raise ValueError("""
            Invalid input: The method should not have positional arguments and should only accept one keyword argument""")
    if kwargs:
        key, value = next(iter(kwargs.items()))
        if key != act_name or not isinstance(value, list):
            raise ValueError(
                f"Invalid input: The method should accept a single keyword argument '{act_name}' with a list value"
            )


def repeat(act: Action, name: str = None, description: str = None, reducer=default_reducer):
    def func(*args, **kwargs):
        validate_input(args, kwargs, act.name)
        return reducer([act(**e) for e in next(iter(kwargs.values()))] if kwargs else [])

    if name is None:
        name = act.name

    if description is None:
        description = act.description

    func.__name__ = act.__name__
    func.__doc__ = description

    return action(
        name=name,
        pydantic_model=create_pydantic_model_from_func(
            func.__name__.title(),
            func,
            override_params={act.name: (List[act.pydantic_model], ...)},
        ),
        stop=act.stop,
    )(func)
