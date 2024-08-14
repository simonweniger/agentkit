from django.contrib.auth import get_user_model
from django.db import models

from agentkit.mixins import MachineMixin

User = get_user_model()


class WorkflowSteps(models.TextChoices):
    DRAFT = "draft"
    PUBLISHED = "published"


class Workflow(models.Model, MachineMixin):
    state_machine_name = "workflow.statemachines.WorfklowWorkflow"
    state_machine_attr = "wf"
    bind_events_as_methods = True

    state = models.CharField(
        max_length=30, choices=WorkflowSteps.choices, default=WorkflowSteps.DRAFT
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True)
    is_active = models.BooleanField(default=False)
