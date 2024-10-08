from inspect import isawaitable
from typing import TYPE_CHECKING

from agentkit.utils.workflow import run_async_from_sync

from agentkit.workflow.event import TriggerData

if TYPE_CHECKING:
    from agentkit import Workflow


class Event:
    def __init__(self, name: str):
        self.name: str = name

    def __repr__(self):
        return f"{type(self).__name__}({self.name!r})"

    def trigger(self, flow: "Workflow", *args, **kwargs):
        trigger_data = TriggerData(
            flow=flow,
            event=self.name,
            args=args,
            kwargs=kwargs,
        )
        flow._put_nonblocking(trigger_data)
        return flow._processing_loop()


def trigger_event_factory(event_instance: Event):
    """Build a method that sends specific `event` to the flow"""

    def trigger_event(self, *args, **kwargs):
        result = event_instance.trigger(self, *args, **kwargs)
        if not isawaitable(result):
            return result
        return run_async_from_sync(result)

    trigger_event.name = event_instance.name  # type: ignore[attr-defined]
    trigger_event.identifier = event_instance.name  # type: ignore[attr-defined]
    trigger_event._is_sm_event = True  # type: ignore[attr-defined]
    return trigger_event


def same_event_cond_builder(expected_event: str):
    """
    Builds a condition method that evaluates to ``True`` when the expected event is received.
    """

    def cond(*args, event: "str | None" = None, **kwargs) -> bool:
        return event == expected_event

    return cond
