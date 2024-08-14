from workflow import State
from workflow import Workflow


def test_assign_events_on_transitions():
    class TrafficLightMachine(Workflow):
        "A traffic light flow"

        green = State(initial=True)
        yellow = State()
        red = State()

        green.to(yellow, event="cycle slowdown slowdown")
        yellow.to(red, event="cycle stop")
        red.to(green, event="cycle go")

        def on_cycle(self, event_data, event: str):
            assert event_data.event == event
            return (
                f"Running {event} from {event_data.transition.source.id} to "
                f"{event_data.transition.target.id}"
            )

    workflow = TrafficLightMachine()

    assert workflow.send("cycle") == "Running cycle from green to yellow"
    assert workflow.send("cycle") == "Running cycle from yellow to red"
    assert workflow.send("cycle") == "Running cycle from red to green"
