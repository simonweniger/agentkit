"""
Enum campaign flow
=====================

A :ref:`Workflow` that demonstrates declaring :ref:`States from Enum types` as source for
``States`` definition.

"""

from enum import Enum

from workflow import Workflow
from workflow.states import States


class CampaignStatus(Enum):
    DRAFT = 1
    PRODUCING = 2
    CLOSED = 3


class CampaignMachine(Workflow):
    "A workflow flow"

    states = States.from_enum(
        CampaignStatus,
        initial=CampaignStatus.DRAFT,
        final=CampaignStatus.CLOSED,
        use_enum_instance=True,
    )

    add_job = states.DRAFT.to(states.DRAFT) | states.PRODUCING.to(states.PRODUCING)
    produce = states.DRAFT.to(states.PRODUCING)
    deliver = states.PRODUCING.to(states.CLOSED)


# %%
# Asserting campaign flow declaration

assert CampaignMachine.DRAFT.initial
assert not CampaignMachine.DRAFT.final

assert not CampaignMachine.PRODUCING.initial
assert not CampaignMachine.PRODUCING.final

assert not CampaignMachine.CLOSED.initial
assert CampaignMachine.CLOSED.final


# %%
# Testing our campaign flow

workflow = CampaignMachine()
res = workflow.send("produce")

assert workflow.DRAFT.is_active is False
assert workflow.PRODUCING.is_active is True
assert workflow.CLOSED.is_active is False
assert workflow.current_state == workflow.PRODUCING
assert workflow.current_state_value == CampaignStatus.PRODUCING
