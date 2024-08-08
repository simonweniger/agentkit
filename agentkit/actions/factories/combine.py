import collections
from typing import List

from agentkit.actions import Action
from agentkit.actions.factories.function import action
from agentkit.utils.pydantic_utils import create_pydantic_model_from_func


def combine(
    acts: List[Action], name: str = None, description: str = None, reducer=None
) -> Action:
    # TODO: make action has a default of None, so the mode can choose to use it or not
    if reducer is None:
        def default_reducer(results):
            return "\n".join(str(e) for e in results)
        reducer = default_reducer

    def func(*args, **kwargs):
        value_list = list(kwargs.values())
        if args:
            raise ValueError(
                "Invalid input: The method should not have positional arguments",
                f"args: {args}",
            )

        ans = []
        for a, i in zip(acts, value_list, strict=False):
            try:
                ans += [a(**i)]
            except Exception as e:
                raise ValueError(
                    f"Failed to invoke {a.name} with the value of {i}: {e}",
                )

        return reducer(ans)

    # Build the name string using all action names from acts
    action_names = "_".join(a.name.lower() for a in acts)
    if name is None:
        name = f"combine_{action_names}"

    if description is None:
        description = ""

    func.__doc__ = description
    func.__name__ = name

    params = collections.OrderedDict()
    for act in acts:
        params[act.name] = (act.pydantic_model, ...)

    return action(
        name=name.title(),
        pydantic_model=create_pydantic_model_from_func(
            func.__name__.title(), func, override_params=params
        ),
    )(func)
