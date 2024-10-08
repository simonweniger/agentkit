"""
Async without external loop
===========================

Demonstrates that the state flow can have async callbacks even if the calling context
is synchronous.

"""

from workflow import State
from workflow import Workflow


class AsyncWorkflow(Workflow):
    initial = State("Initial", initial=True)
    processing = State()
    final = State("Final", final=True)

    start = initial.to(processing)
    finish = processing.to(final)

    async def on_start(self):
        return "starting"

    async def on_finish(self):
        return "finishing"


# %%
# Executing
# ---------


def sync_main():
    workflow = AsyncWorkflow()
    result = workflow.start()
    print(f"Start result is {result}")
    result = workflow.send("finish")
    print(f"Finish result is {result}")
    print(workflow.current_state)
    assert workflow.current_state == workflow.final


if __name__ == "__main__":
    sync_main()
