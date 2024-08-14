import pytest

from workflow import State
from workflow import Workflow


@pytest.fixture()
def sm_class():
    class WF(Workflow):
        pending = State(initial=True)
        waiting_approval = State()
        approved = State(final=True)

        start = pending.to(waiting_approval)
        approve = waiting_approval.to(approved)

    return WF


class TestState:
    def test_name_derived_from_id(self, sm_class):
        assert sm_class.pending.name == "Pending"
        assert sm_class.waiting_approval.name == "Waiting approval"
        assert sm_class.approved.name == "Approved"

    def test_state_from_instance_is_hashable(self, sm_class):
        workflow = sm_class()
        states_set = {workflow.pending, workflow.waiting_approval, workflow.approved, workflow.approved}
        assert states_set == {workflow.pending, workflow.waiting_approval, workflow.approved}

    def test_state_knows_if_its_initial(self, sm_class):
        workflow = sm_class()
        assert workflow.pending.initial
        assert not workflow.waiting_approval.initial
        assert not workflow.approved.initial

    def test_state_knows_if_its_final(self, sm_class):
        workflow = sm_class()
        assert not workflow.pending.final
        assert not workflow.waiting_approval.final
        assert workflow.approved.final
