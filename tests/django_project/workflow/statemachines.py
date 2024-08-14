from workflow import Workflow
from workflow.states import States

from .models import WorkflowSteps


class WorfklowWorkflow(Workflow):
    _ = States.from_enum(WorkflowSteps, initial=WorkflowSteps.DRAFT, final=WorkflowSteps.PUBLISHED)

    publish = _.DRAFT.to(_.PUBLISHED, cond="is_active")
    notify_user = _.DRAFT.to.itself(internal=True, cond="has_user")

    def has_user(self):
        return bool(self.model.user)
