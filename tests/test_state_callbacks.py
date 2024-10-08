from unittest import mock

import pytest


@pytest.fixture()
def event_mock():
    return mock.MagicMock()


@pytest.fixture()
def traffic_light_machine(event_mock):  # noqa: C901
    from workflow import State
    from workflow import Workflow

    class TrafficLightMachineStateEvents(Workflow):
        "A traffic light flow"

        green = State(initial=True)
        yellow = State()
        red = State()

        cycle = green.to(yellow) | yellow.to(red) | red.to(green)

        def on_enter_state(self, event_data):
            event_mock.on_enter_state(event_data.transition.target)

        def on_exit_state(self, event_data):
            event_mock.on_exit_state(event_data.state)

        def on_enter_green(self):
            event_mock.on_enter_green(self)

        def on_exit_green(self):
            event_mock.on_exit_green(self)

        def on_enter_yellow(self):
            event_mock.on_enter_yellow(self)

        def on_exit_yellow(self):
            event_mock.on_exit_yellow(self)

        def on_enter_red(self):
            event_mock.on_enter_red(self)

        def on_exit_red(self):
            event_mock.on_exit_red(self)

    return TrafficLightMachineStateEvents


class TestStateCallbacks:
    def test_should_call_on_enter_generic_state(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()
        flow.cycle()
        assert event_mock.on_enter_state.call_args_list == [
            mock.call(flow.green),
            mock.call(flow.yellow),
        ]

    def test_should_call_on_exit_generic_state(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()
        flow.cycle()
        event_mock.on_exit_state.assert_called_once_with(flow.green)

    def test_should_call_on_enter_of_specific_state(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()
        flow.cycle()
        event_mock.on_enter_yellow.assert_called_once_with(flow)

    def test_should_call_on_exit_of_specific_state(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()
        flow.cycle()
        event_mock.on_exit_green.assert_called_once_with(flow)

    def test_should_be_on_the_previous_state_when_exiting(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()

        def assert_is_green_from_state(s):
            assert s.value == "green"

        def assert_is_green(m):
            assert m.green.is_active

        event_mock.on_exit_state.side_effect = assert_is_green_from_state
        event_mock.on_exit_green.side_effect = assert_is_green

        flow.cycle()

    def test_should_be_on_the_next_state_when_entering(self, event_mock, traffic_light_machine):
        flow = traffic_light_machine()

        def assert_is_yellow_from_state(s):
            assert s.value == "yellow"

        def assert_is_yellow(m):
            assert m.yellow.is_active

        event_mock.on_enter_state.side_effect = assert_is_yellow_from_state
        event_mock.on_enter_yellow.side_effect = assert_is_yellow

        flow.cycle()
