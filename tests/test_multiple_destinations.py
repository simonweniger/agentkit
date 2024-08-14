import pytest

from workflow import State
from workflow import Workflow
from workflow import exceptions


class Request:
    def __init__(self, state="requested"):
        self.state = None
        self._is_ok = False

    def is_ok(self):
        return self._is_ok


def test_transition_should_choose_final_state_on_multiple_possibilities(
    approval_machine, current_time
):
    # given
    model = Request()
    flow = approval_machine(model)

    model._is_ok = False

    # when
    assert flow.validate() == model

    # then
    assert model.rejected_at == current_time
    assert flow.rejected.is_active

    # given
    model._is_ok = True

    # when
    assert flow.retry() == model

    # then
    assert model.rejected_at is None
    assert flow.requested.is_active

    # when
    assert flow.validate() == model

    # then
    assert model.accepted_at == current_time
    assert flow.accepted.is_active


def test_transition_to_first_that_executes_if_multiple_targets():
    class ApprovalMachine(Workflow):
        "A workflow"

        requested = State(initial=True)
        accepted = State(final=True)
        rejected = State(final=True)

        validate = requested.to(accepted, rejected)

    flow = ApprovalMachine()

    flow.validate()
    assert flow.accepted.is_active


def test_do_not_transition_if_multiple_targets_with_guard():
    def never_will_pass(event_data):
        return False

    class ApprovalMachine(Workflow):
        "A workflow"

        requested = State(initial=True)
        accepted = State(final=True)
        rejected = State(final=True)

        validate = (
            requested.to(accepted, cond=never_will_pass)
            | requested.to(rejected, cond="also_never_will_pass")
            | requested.to(requested, cond="this_also_never_will_pass")
        )

        @property
        def also_never_will_pass(self):
            return False

        def this_also_never_will_pass(self, event_data):
            return False

    flow = ApprovalMachine()

    with pytest.raises(exceptions.TransitionNotAllowed):
        flow.validate()
    assert flow.requested.is_active


def test_check_invalid_reference_to_conditions():
    class ApprovalMachine(Workflow):
        "A workflow"

        requested = State(initial=True)
        accepted = State(final=True)
        rejected = State(final=True)

        validate = requested.to(accepted, cond="not_found_condition") | requested.to(rejected)

    with pytest.raises(exceptions.InvalidDefinition):
        ApprovalMachine()


def test_should_change_to_returned_state_on_multiple_target_with_combined_transitions():
    class ApprovalMachine(Workflow):
        "A workflow"

        requested = State(initial=True)
        accepted = State()
        rejected = State()
        completed = State(final=True)

        validate = (
            requested.to(accepted, cond="is_ok") | requested.to(rejected) | accepted.to(completed)
        )
        retry = rejected.to(requested)

        def on_validate(self):
            if self.accepted.is_active and self.model.is_ok():
                return "congrats!"

    # given
    model = Request()
    flow = ApprovalMachine(model)

    model._is_ok = False

    # when
    assert flow.validate() is None
    # then
    assert flow.rejected.is_active

    # given
    assert flow.retry() is None
    assert flow.requested.is_active
    model._is_ok = True

    # when
    assert flow.validate() is None
    # then
    assert flow.accepted.is_active

    # when
    assert flow.validate() == "congrats!"
    # then
    assert flow.completed.is_active

    with pytest.raises(exceptions.TransitionNotAllowed, match="Can't validate when in Completed."):
        assert flow.validate()


def test_transition_on_execute_should_be_called_with_run_syntax(approval_machine, current_time):
    # given
    model = Request()
    flow = approval_machine(model)

    model._is_ok = True

    # when
    assert flow.send("validate") == model
    # then
    assert model.accepted_at == current_time
    assert flow.accepted.is_active


def test_multiple_values_returned_with_multiple_targets():
    class ApprovalMachine(Workflow):
        "A workflow"

        requested = State(initial=True)
        accepted = State(final=True)
        denied = State(final=True)

        @requested.to(accepted, denied)
        def validate(self):
            return 1, 2

    flow = ApprovalMachine()

    assert flow.validate() == (
        1,
        2,
    )


@pytest.mark.parametrize(
    ("payment_failed", "expected_state"),
    [
        (False, "paid"),
        (True, "failed"),
    ],
)
def test_multiple_targets_using_or_starting_from_same_origin(payment_failed, expected_state):
    class InvoiceWorkflow(Workflow):
        unpaid = State(initial=True)
        paid = State(final=True)
        failed = State()

        pay = unpaid.to(paid, unless="payment_success") | failed.to(paid) | unpaid.to(failed)

        def payment_success(self, event_data):
            return payment_failed

    invoice_fsm = InvoiceWorkflow()
    invoice_fsm.pay()
    assert invoice_fsm.current_state.id == expected_state


def test_order_control(OrderControl):
    control = OrderControl()
    assert control.add_to_order(3) == 3
    assert control.add_to_order(7) == 10

    control.receive_payment(4)
    with pytest.raises(exceptions.TransitionNotAllowed):
        control.process_order()

    control.receive_payment(6)
    control.process_order()

    control.ship_order()
    assert control.order_total == 10
    assert control.payments == [4, 6]
    assert control.completed.is_active
