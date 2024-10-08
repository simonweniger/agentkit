import pytest

from workflow import exceptions


@pytest.fixture()
def BaseMachine():
    from workflow import State
    from workflow import Workflow

    class BaseMachine(Workflow, strict_states=False):
        state_1 = State(initial=True)
        state_2 = State()
        trans_1_2 = state_1.to(state_2)
        trans_2_2 = state_2.to.itself(internal=True)

    return BaseMachine


@pytest.fixture()
def InheritedClass(BaseMachine):
    class InheritedClass(BaseMachine, strict_states=False):
        pass

    return InheritedClass


@pytest.fixture()
def ExtendedClass(BaseMachine):
    from workflow import State

    class ExtendedClass(BaseMachine):
        state_3 = State()
        trans_2_3 = BaseMachine.state_2.to(state_3)
        trans_3_3 = state_3.to.itself(internal=True)

    return ExtendedClass


@pytest.fixture()
def OverridedClass(BaseMachine):
    from workflow import State

    class OverridedClass(BaseMachine):
        state_2 = State()

        trans_1_2 = BaseMachine.state_1.to(state_2)
        trans_2_2 = state_2.to.itself(internal=True)

    return OverridedClass


@pytest.fixture()
def OverridedTransitionClass(BaseMachine):
    from workflow import State

    class OverridedTransitionClass(BaseMachine):
        state_3 = State()

        trans_1_2 = BaseMachine.state_1.to(state_3)
        trans_3_3 = state_3.to.itself(internal=True)

    return OverridedTransitionClass


def test_should_inherit_states_and_transitions(BaseMachine, InheritedClass):
    assert InheritedClass.states == [
        BaseMachine.state_1,
        BaseMachine.state_2,
    ]

    expected = [e.name for e in BaseMachine.events]
    actual = [e.name for e in InheritedClass.events]
    assert actual == expected


def test_should_extend_states_and_transitions(BaseMachine, ExtendedClass):
    assert ExtendedClass.states == [
        BaseMachine.state_1,
        BaseMachine.state_2,
        ExtendedClass.state_3,
    ]

    base_events = [e.name for e in BaseMachine.events]
    expected = base_events + [ExtendedClass.trans_2_3.name, ExtendedClass.trans_3_3.name]
    actual = [e.name for e in ExtendedClass.events]
    assert actual == expected


def test_should_execute_transitions(ExtendedClass):
    instance = ExtendedClass()
    instance.trans_1_2()
    instance.trans_2_3()

    assert instance.state_3.is_active


@pytest.mark.xfail(reason="State overriding is not supported")
def test_dont_support_overriden_states(OverridedClass):
    # There's no support for overriding states
    with pytest.raises(exceptions.InvalidDefinition):
        OverridedClass()


@pytest.mark.xfail(reason="Transition overriding is not supported")
def test_support_override_transitions(OverridedTransitionClass):
    instance = OverridedTransitionClass()

    instance.trans_1_2()
    assert instance.state_3.is_active
