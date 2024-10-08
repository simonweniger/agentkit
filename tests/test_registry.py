from unittest import mock

import pytest


@pytest.fixture()
def django_autodiscover_modules():
    auto_discover_modules = mock.MagicMock()

    with mock.patch("workflow.registry.autodiscover_modules", new=auto_discover_modules):
        yield auto_discover_modules


def test_should_register_a_state_machine(caplog, django_autodiscover_modules):
    from workflow import State
    from workflow import Workflow
    from workflow import registry

    class CampaignMachine(Workflow):
        "A workflow flow"

        draft = State(initial=True)
        producing = State()

        add_job = draft.to(draft) | producing.to(producing)
        produce = draft.to(producing)

    assert "CampaignMachine" in registry._REGISTRY
    assert registry.get_machine_cls("tests.test_registry.CampaignMachine") == CampaignMachine

    with pytest.warns(DeprecationWarning):
        assert registry.get_machine_cls("CampaignMachine") == CampaignMachine


def test_load_modules_should_call_autodiscover_modules(django_autodiscover_modules):
    from workflow.registry import load_modules

    # given
    modules = ["a", "c", "workflow", "statemachines"]

    # when
    load_modules(modules)

    # then
    django_autodiscover_modules.assert_has_calls(mock.call(m) for m in modules)
