import pytest

from workflow.state import State
from workflow.workflow import Workflow

EXPECTED_LOG_ADD = """Frodo on: draft--(add_job)-->draft
Frodo enter: draft from add_job
Frodo on: draft--(produce)-->producing
Frodo enter: producing from produce
"""

EXPECTED_LOG_CREATION = """Frodo enter: draft from __initial__
Frodo on: draft--(add_job)-->draft
Frodo enter: draft from add_job
Frodo on: draft--(produce)-->producing
Frodo enter: producing from produce
"""


class TestObserver:
    def test_add_log_observer(self, campaign_machine, capsys):
        class LogObserver:
            def __init__(self, name):
                self.name = name

            def on_transition(self, event, state, target):
                print(f"{self.name} on: {state.id}--({event})-->{target.id}")

            def on_enter_state(self, target, event):
                print(f"{self.name} enter: {target.id} from {event}")

        workflow = campaign_machine()

        workflow.add_listener(LogObserver("Frodo"))

        workflow.add_job()
        workflow.produce()

        captured = capsys.readouterr()
        assert captured.out == EXPECTED_LOG_ADD

    def test_log_observer_on_creation(self, campaign_machine, capsys):
        class LogObserver:
            def __init__(self, name):
                self.name = name

            def on_transition(self, event, state, target):
                print(f"{self.name} on: {state.id}--({event})-->{target.id}")

            def on_enter_state(self, target, event):
                print(f"{self.name} enter: {target.id} from {event}")

        workflow = campaign_machine(listeners=[LogObserver("Frodo")])

        workflow.add_job()
        workflow.produce()

        captured = capsys.readouterr()
        assert captured.out == EXPECTED_LOG_CREATION

    def test_deprecated_api(self, campaign_machine, capsys):
        class LogObserver:
            def __init__(self, name):
                self.name = name

            def on_transition(self, event, state, target):
                print(f"{self.name} on: {state.id}--({event})-->{target.id}")

            def on_enter_state(self, target, event):
                print(f"{self.name} enter: {target.id} from {event}")

        workflow = campaign_machine()

        with pytest.warns(
            DeprecationWarning, match="Method `add_observer` has been renamed to `add_listener`."
        ):
            workflow.add_observer(LogObserver("Frodo"))

        workflow.add_job()
        workflow.produce()

        captured = capsys.readouterr()
        assert captured.out == EXPECTED_LOG_ADD


def test_regression_456():
    class TestListener:
        def __init__(self):
            pass

    class MyMachine(Workflow):
        first = State("FIRST", initial=True)

        second = State("SECOND")

        first_selected = second.to(first)

        second_selected = first.to(second)

        @first.exit
        def exit_first(self) -> None:
            print("exit SLEEPING")

    m = MyMachine()
    m.add_listener(TestListener())

    m.send("second_selected")
