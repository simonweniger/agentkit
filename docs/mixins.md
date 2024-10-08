
# Mixins

Your {ref}`domain models` can be inherited from a custom mixin to auto-instantiate a {ref}`workflow`.

## MachineMixin


```{eval-rst}
.. autoclass:: workflow.mixins.MachineMixin
    :members:
    :undoc-members:
```

### Mixins example

Given a state flow definition:

```py
>>> from agentkit import Workflow, State

>>> from agentkit.mixins import MachineMixin

>>> class CampaignMachineWithKeys(Workflow):
...     "A workflow flow"
...     draft = State('Draft', initial=True, value=1)
...     producing = State('Being produced', value=2)
...     closed = State('Closed', value=3, final=True)
...     cancelled = State('Cancelled', value=4, final=True)
...
...     add_job = draft.to.itself() | producing.to.itself()
...     produce = draft.to(producing)
...     deliver = producing.to(closed)
...     cancel = cancelled.from_(draft, producing)

```

It can be attached to a model using mixin and the fully qualified name of the
class.


``` py
>>> class Workflow(MachineMixin):
...     state_machine_name = '__main__.CampaignMachineWithKeys'
...     state_machine_attr = 'workflow'
...     state_field_name = 'workflow_step'
...     bind_events_as_methods = True
...
...     workflow_step = 1
...

```

When an instance of `Workflow` is created, it receives an instance of `CampaignMachineWithKeys``
assigned using the `state_machine_attr` name. Also, the `current_state` is stored using the `state_field_name`, in this case, `workflow_step`.

``` py
>>> model = Workflow()

>>> isinstance(model.workflow, CampaignMachineWithKeys)
True

>>> model.workflow_step
1

>>> model.workflow.current_state == model.workflow.draft
True

>>> model.produce()  # `bind_events_as_methods = True` adds triggers to events in the mixin instance
>>> model.workflow_step
2

>>> model.workflow.cancel()  # You can still call the WF directly

>>> model.workflow_step
4

>>> model.workflow.current_state == model.workflow.cancelled
True

```

```{note}
On this example the `state_machine_name` is receiving a `__main__` module due
to the way `autodoc` works so we can have automated tests on the docs
examples.

On your code, use the fully qualified path to the workflow class.
```

```{seealso}
The [](integrations.md#django-integration) section.
```
