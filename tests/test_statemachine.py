import pytest

from workflow import State
from workflow import Workflow
from workflow import exceptions
from tests.models import MyModel


def test_machine_repr(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)
    assert (
        repr(flow) == "CampaignMachine(model=MyModel({'state': 'draft'}), "
        "state_field='state', current_state='draft')"
    )


def test_machine_should_be_at_start_state(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert [s.value for s in campaign_machine.states] == [
        "closed",
        "draft",
        "producing",
    ]
    assert [t.name for t in campaign_machine.events] == [
        "add_job",
        "deliver",
        "produce",
    ]

    assert model.state == "draft"
    assert flow.current_state == flow.draft


def test_machine_should_only_allow_only_one_initial_state():
    with pytest.raises(exceptions.InvalidDefinition):

        class CampaignMachine(Workflow):
            "A workflow flow"

            draft = State(initial=True)
            producing = State()
            closed = State(
                "Closed", initial=True
            )  # Should raise an Exception right after the class is defined

            add_job = draft.to(draft) | producing.to(producing)
            produce = draft.to(producing)
            deliver = producing.to(closed)


def test_machine_should_activate_initial_state(mocker):
    spy = mocker.Mock()

    class CampaignMachine(Workflow):
        "A workflow flow"

        draft = State(initial=True)
        producing = State()
        closed = State(final=True)

        add_job = draft.to(draft) | producing.to(producing)
        produce = draft.to(producing)
        deliver = producing.to(closed)

        def on_enter_draft(self):
            spy("draft")
            return "draft"

    workflow = CampaignMachine()

    spy.assert_called_once_with("draft")
    assert workflow.current_state == workflow.draft
    assert workflow.draft.is_active

    spy.reset_mock()
    # trying to activate the initial state again should does nothing
    assert workflow.activate_initial_state() is None

    spy.assert_not_called()
    assert workflow.current_state == workflow.draft
    assert workflow.draft.is_active


def test_machine_should_not_allow_transitions_from_final_state():
    with pytest.raises(exceptions.InvalidDefinition):

        class CampaignMachine(Workflow):
            "A workflow flow"

            draft = State(initial=True)
            producing = State()
            closed = State(final=True)

            add_job = draft.to(draft) | producing.to(producing) | closed.to(draft)
            produce = draft.to(producing)
            deliver = producing.to(closed)


def test_should_change_state(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert model.state == "draft"
    assert flow.current_state == flow.draft

    flow.produce()

    assert model.state == "producing"
    assert flow.current_state == flow.producing


def test_should_run_a_transition_that_keeps_the_state(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert model.state == "draft"
    assert flow.current_state == flow.draft

    flow.add_job()
    assert model.state == "draft"
    assert flow.current_state == flow.draft

    flow.produce()
    assert model.state == "producing"
    assert flow.current_state == flow.producing

    flow.add_job()
    assert model.state == "producing"
    assert flow.current_state == flow.producing


def test_should_change_state_with_multiple_machine_instances(campaign_machine):
    model1 = MyModel()
    model2 = MyModel()
    machine1 = campaign_machine(model1)
    machine2 = campaign_machine(model2)

    assert machine1.current_state == campaign_machine.draft
    assert machine2.current_state == campaign_machine.draft

    p1 = machine1.produce
    p2 = machine2.produce

    p2()
    assert machine1.current_state == campaign_machine.draft
    assert machine2.current_state == campaign_machine.producing

    p1()
    assert machine1.current_state == campaign_machine.producing
    assert machine2.current_state == campaign_machine.producing


@pytest.mark.parametrize(
    ("current_state", "transition"),
    [
        ("draft", "deliver"),
        ("closed", "add_job"),
    ],
)
def test_call_to_transition_that_is_not_in_the_current_state_should_raise_exception(
    campaign_machine, current_state, transition
):
    model = MyModel(state=current_state)
    flow = campaign_machine(model)

    assert flow.current_state.value == current_state

    with pytest.raises(exceptions.TransitionNotAllowed):
        flow.send(transition)


def test_machine_should_list_allowed_events_in_the_current_state(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert model.state == "draft"
    assert [t.name for t in flow.allowed_events] == ["add_job", "produce"]

    flow.produce()
    assert model.state == "producing"
    assert [t.name for t in flow.allowed_events] == ["add_job", "deliver"]

    deliver = flow.allowed_events[1]

    deliver()
    assert model.state == "closed"
    assert flow.allowed_events == []


def test_machine_should_run_a_transition_by_his_key(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert model.state == "draft"

    flow.send("add_job")
    assert model.state == "draft"
    assert flow.current_state == flow.draft

    flow.send("produce")
    assert model.state == "producing"
    assert flow.current_state == flow.producing


def test_machine_should_raise_an_exception_if_a_transition_by_his_key_is_not_found(
    campaign_machine,
):
    model = MyModel()
    flow = campaign_machine(model)

    assert model.state == "draft"

    with pytest.raises(exceptions.TransitionNotAllowed):
        flow.send("go_horse")


def test_machine_should_use_and_model_attr_other_than_state(campaign_machine):
    model = MyModel(status="producing")
    flow = campaign_machine(model, state_field="status")

    assert getattr(model, "state", None) is None
    assert model.status == "producing"
    assert flow.current_state == flow.producing

    flow.deliver()

    assert model.status == "closed"
    assert flow.current_state == flow.closed


def test_cant_assign_an_invalid_state_directly(campaign_machine):
    flow = campaign_machine()
    with pytest.raises(exceptions.InvalidStateValue):
        flow.current_state_value = "non existing state"


def test_should_allow_validate_data_for_transition(campaign_machine_with_validator):
    model = MyModel()
    flow = campaign_machine_with_validator(model)

    with pytest.raises(LookupError):
        flow.produce()

    flow.produce(goods="something")

    assert model.state == "producing"


def test_should_check_if_is_in_status(campaign_machine):
    model = MyModel()
    flow = campaign_machine(model)

    assert flow.draft.is_active
    assert not flow.producing.is_active
    assert not flow.closed.is_active

    flow.produce()

    assert not flow.draft.is_active
    assert flow.producing.is_active
    assert not flow.closed.is_active

    flow.deliver()

    assert not flow.draft.is_active
    assert not flow.producing.is_active
    assert flow.closed.is_active


def test_defined_value_must_be_assigned_to_models(campaign_machine_with_values):
    model = MyModel()
    flow = campaign_machine_with_values(model)

    assert model.state == 1
    flow.produce()
    assert model.state == 2
    flow.deliver()
    assert model.state == 3


def test_state_machine_without_model(campaign_machine):
    flow = campaign_machine()
    assert flow.draft.is_active
    assert not flow.producing.is_active
    assert not flow.closed.is_active

    flow.produce()

    assert not flow.draft.is_active
    assert flow.producing.is_active
    assert not flow.closed.is_active


@pytest.mark.parametrize(
    ("model", "machine_name", "start_value"),
    [
        (None, "campaign_machine", "producing"),
        (None, "campaign_machine_with_values", 2),
        (MyModel(), "campaign_machine", "producing"),
        (MyModel(), "campaign_machine_with_values", 2),
    ],
)
def test_state_machine_with_a_start_value(request, model, machine_name, start_value):
    machine_cls = request.getfixturevalue(machine_name)
    flow = machine_cls(model, start_value=start_value)
    assert not flow.draft.is_active
    assert flow.producing.is_active
    assert not model or model.state == start_value


@pytest.mark.parametrize(
    ("model", "machine_name", "start_value"),
    [
        (None, "campaign_machine", "tapioca"),
        (None, "campaign_machine_with_values", 99),
        (MyModel(), "campaign_machine", "tapioca"),
        (MyModel(), "campaign_machine_with_values", 99),
    ],
)
def test_state_machine_with_a_invalid_start_value(request, model, machine_name, start_value):
    machine_cls = request.getfixturevalue(machine_name)
    with pytest.raises(exceptions.InvalidStateValue):
        machine_cls(model, start_value=start_value)


def test_state_machine_with_a_invalid_model_state_value(request, campaign_machine):
    machine_cls = campaign_machine
    model = MyModel(state="tapioca")
    workflow = machine_cls(model)

    with pytest.raises(
        exceptions.InvalidStateValue, match="'tapioca' is not a valid state value."
    ):
        assert workflow.current_state == workflow.draft


def test_should_not_create_instance_of_abstract_machine():
    class EmptyMachine(Workflow):
        "An empty flow"

        pass

    with pytest.raises(exceptions.InvalidDefinition):
        EmptyMachine()


def test_should_not_create_instance_of_machine_without_states():
    s1 = State()
    with pytest.raises(exceptions.InvalidDefinition):

        class OnlyTransitionMachine(Workflow):
            t1 = s1.to.itself()


def test_should_not_create_instance_of_machine_without_transitions():
    with pytest.raises(exceptions.InvalidDefinition):

        class NoTransitionsMachine(Workflow):
            "A flow without transitions"

            initial = State(initial=True)


def test_should_not_create_disconnected_machine():
    expected = (
        r"There are unreachable states. The workflow graph should have a single component. "
        r"Disconnected states: \['blue'\]"
    )
    with pytest.raises(exceptions.InvalidDefinition, match=expected):

        class BrokenTrafficLightMachine(Workflow):
            "A broken traffic light flow"

            green = State(initial=True)
            yellow = State()
            blue = State()  # This state is unreachable

            cycle = green.to(yellow) | yellow.to(green)


def test_should_not_create_big_disconnected_machine():
    expected = (
        r"There are unreachable states. The workflow graph should have a single component. "
        r"Disconnected states: \[.*\]$"
    )
    with pytest.raises(exceptions.InvalidDefinition, match=expected):

        class BrokenTrafficLightMachine(Workflow):
            "A broken traffic light flow"

            green = State(initial=True)
            yellow = State()
            magenta = State()  # This state is unreachable
            red = State()
            cyan = State()
            blue = State()  # This state is also unreachable

            cycle = green.to(yellow)
            diverge = green.to(cyan) | cyan.to(red)
            validate = yellow.to(green)


def test_state_value_is_correct():
    STATE_NEW = 0
    STATE_DRAFT = 1

    class ValueTestModel(Workflow, strict_states=False):
        new = State(STATE_NEW, value=STATE_NEW, initial=True)
        draft = State(STATE_DRAFT, value=STATE_DRAFT, final=True)

        write = new.to(draft)

    model = ValueTestModel()
    assert model.new.value == STATE_NEW
    assert model.draft.value == STATE_DRAFT


def test_final_states(campaign_machine_with_final_state):
    model = MyModel()
    flow = campaign_machine_with_final_state(model)
    final_states = flow.final_states
    assert len(final_states) == 1
    assert final_states[0].name == "Closed"


def test_should_not_override_states_properties(campaign_machine):
    flow = campaign_machine()
    with pytest.raises(exceptions.WorkflowError) as e:
        flow.draft = "something else"

    assert "State overriding is not allowed. Trying to add 'something else' to draft" in str(e)


class TestWarnings:
    def test_should_warn_if_model_already_has_attribute_and_binding_is_enabled(
        self, campaign_machine_with_final_state, capsys
    ):
        class Model:
            state = "draft"

            def produce(self):
                return f"producing from {self.__class__.__name__!r}"

        model = Model()

        workflow = campaign_machine_with_final_state(model)
        with pytest.warns(
            UserWarning, match="Attribute 'produce' already exists on <tests.test.*"
        ):
            workflow.bind_events_to(model)

        assert model.produce() == "producing from 'Model'"
        assert workflow.current_state_value == "draft"

        assert workflow.produce() is None
        assert workflow.current_state_value == "producing"

        # event trigger bound to the model
        model.deliver()
        assert workflow.current_state_value == "closed"

    def test_should_warn_if_thereis_a_trap_state(self, capsys):
        with pytest.warns(
            UserWarning,
            match=r"have no outgoing transition: \['state_without_outgoing_transition'\]",
        ):

            class TrapWorkflow(Workflow):
                initial = State(initial=True)
                state_without_outgoing_transition = State()

                t = initial.to(state_without_outgoing_transition)

    def test_should_warn_if_no_path_to_a_final_state(self, capsys):
        with pytest.warns(
            UserWarning,
            match=r"have no path to a final state: \['producing'\]",
        ):

            class TrapWorkflow(Workflow):
                started = State(initial=True)
                closed = State(final=True)
                producing = State()

                start = started.to(producing)
                close = started.to(closed)
                add_job = producing.to.itself(internal=True)
