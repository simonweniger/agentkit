from typing import List

from agentkit.actions import Action
from agentkit.actions.factories.function import action
from agentkit.utils.pydantic_utils import create_pydantic_model_from_func


def combine(
    acts: List[Action | None], name: str = None, description: str = None, reducer=None
) -> Action:
    reducer = reducer
    func = create_combined_function(acts, reducer)
    name = name or generate_name(acts)
    description = description or ""
    return create_action(func, name, description, acts)


def create_combined_function(acts, reducer):
    def func(**kwargs):
        results = []
        for act in acts:
            if act is not None and act.name in kwargs:
                results.append(act(**kwargs[act.name]))
        return reducer(results)

    return func


def generate_name(acts):
    action_names = "_".join(a.name.lower() for a in acts if a is not None)
    return f"combine_{action_names}"


def create_action(func, name, description, acts):
    func.__doc__ = description
    func.__name__ = name
    params = {act.name: (act.pydantic_model | None) for act in acts if act is not None}
    return action(
        name=name.title(),
        pydantic_model=create_pydantic_model_from_func(
            func.__name__.title(), func, override_params=params
        ),
    )(func)
