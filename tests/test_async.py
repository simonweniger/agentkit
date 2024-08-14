import re

import pytest

from workflow import State
from workflow import Workflow
from workflow.exceptions import InvalidStateValue


@pytest.fixture()
def async_order_control_machine():  # noqa: C901
    class OrderControl(Workflow):
        waiting_for_payment = State(initial=True)
        processing = State()
        shipping = State()
        completed = State(final=True)

        add_to_order = waiting_for_payment.to(waiting_for_payment)
        receive_payment = waiting_for_payment.to(
            processing, cond="payments_enough"
        ) | waiting_for_payment.to(waiting_for_payment, unless="payments_enough")
        process_order = processing.to(shipping, cond="payment_received")
        ship_order = shipping.to(completed)

        def __init__(self):
            self.order_total = 0
            self.payments = []
            self.payment_received = False
            super().__init__()

        async def payments_enough(self, amount):
            return sum(self.payments) + amount >= self.order_total

        async def before_add_to_order(self, amount):
            self.order_total += amount
            return self.order_total

        async def before_receive_payment(self, amount):
            self.payments.append(amount)
            return self.payments

        async def after_receive_payment(self):
            self.payment_received = True

        async def on_enter_waiting_for_payment(self):
            self.payment_received = False

    return OrderControl


async def test_async_order_control_machine(async_order_control_machine):
    workflow = async_order_control_machine()

    assert await workflow.add_to_order(3) == 3
    assert await workflow.add_to_order(7) == 10

    assert await workflow.receive_payment(4) == [4]
    assert workflow.waiting_for_payment.is_active

    with pytest.raises(workflow.TransitionNotAllowed):
        await workflow.process_order()

    assert workflow.waiting_for_payment.is_active

    assert await workflow.receive_payment(6) == [4, 6]
    await workflow.process_order()

    await workflow.ship_order()
    assert workflow.order_total == 10
    assert workflow.payments == [4, 6]
    assert workflow.completed.is_active


def test_async_state_from_sync_context(async_order_control_machine):
    """Test that an async state flow can be used from a synchronous context"""

    workflow = async_order_control_machine()

    assert workflow.add_to_order(3) == 3
    assert workflow.add_to_order(7) == 10

    assert workflow.receive_payment(4) == [4]
    assert workflow.waiting_for_payment.is_active

    with pytest.raises(workflow.TransitionNotAllowed):
        workflow.process_order()

    assert workflow.waiting_for_payment.is_active

    assert workflow.send("receive_payment", 6) == [4, 6]  # test the sync version of the `.send()` method
    workflow.send("process_order")  # test the sync version of the `.send()` method

    workflow.ship_order()
    assert workflow.order_total == 10
    assert workflow.payments == [4, 6]
    assert workflow.completed.is_active


async def test_async_state_should_be_initialized(async_order_control_machine):
    """Test that the state flow is initialized before any event is triggered

    Given how async works on python, there's no built-in way to activate the initial state that
    may depend on async code from the Workflow.__init__ method.

    We do a `_ensure_is_initialized()` check before each event, but to check the current state
    just before the state flow is created, the user must await the activation of the initial
    state explicitly.
    """

    workflow = async_order_control_machine()
    with pytest.raises(
        InvalidStateValue,
        match=re.escape(
            r"There's no current state set. In async code, "
            r"did you activate the initial state? (e.g., `await workflow.activate_initial_state()`)"
        ),
    ):
        assert workflow.current_state == workflow.waiting_for_payment

    await workflow.activate_initial_state()
    assert workflow.current_state == workflow.waiting_for_payment
