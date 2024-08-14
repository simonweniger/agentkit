### Issue 406

A Workflow that exercises the example given on issue
#[406](https://github.com/fgmacedo/python-statemachine/issues/406).

In this example, the event callback must be registered only once.

```py
>>> from workflow import State
>>> from workflow import Workflow

>>> class ExampleWorkflow(Workflow, strict_states=False):
...     Created = State(initial=True)
...     Inited = State(final=True)
...
...     initialize = Created.to(Inited)
...
...     @initialize.before
...     def before_initialize(self):
...         print("before init")
...
...     @initialize.on
...     def on_initialize(self):
...         print("on init")

>>> def test_sm():
...     workflow = ExampleWorkflow()
...     workflow.initialize()

```

Expected output:

```py
>>> test_sm()
before init
on init

```
