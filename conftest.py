import sys

import pytest


@pytest.fixture(autouse=True, scope="session")
def add_doctest_context(doctest_namespace):  # noqa: PT004
    from workflow import State
    from workflow import Workflow
    from workflow.utils import run_async_from_sync

    class ContribAsyncio:
        """
        Using `run_async_from_sync` to be injected in the doctests to better integration with an
        already running loop, as all of our examples are also automated executed as doctests.

        On real life code you should use standard `import asyncio; asyncio.run(main())`.
        """

        def __init__(self):
            self.run = run_async_from_sync

    doctest_namespace["State"] = State
    doctest_namespace["Workflow"] = Workflow
    doctest_namespace["asyncio"] = ContribAsyncio()


def pytest_ignore_collect(collection_path, path, config):
    if sys.version_info >= (3, 10):  # noqa: UP036
        return None

    if "django_project" in str(path):
        return True
