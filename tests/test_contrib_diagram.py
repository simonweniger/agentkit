from contextlib import contextmanager
from unittest import mock

import pytest

from workflow.contrib.diagram import DotGraphMachine
from workflow.contrib.diagram import main
from workflow.contrib.diagram import quickchart_write_svg


@pytest.fixture(
    params=[
        (
            "_repr_svg_",
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE svg',
        ),
        (
            "_repr_html_",
            '<div class="workflow"><?xml version="1.0" encoding="UTF-8" standalone=',
        ),
    ]
)
def expected_reprs(request):
    return request.param


@pytest.mark.parametrize(
    "machine_name",
    [
        "AllActionsMachine",
        "OrderControl",
    ],
)
def test_machine_repr_custom_(request, machine_name, expected_reprs):
    machine_cls = request.getfixturevalue(machine_name)
    flow = machine_cls()

    magic_method, expected_repr = expected_reprs
    repr = getattr(flow, magic_method)()
    assert repr.startswith(expected_repr)


def test_machine_dot(OrderControl):
    flow = OrderControl()

    graph = DotGraphMachine(flow)
    dot = graph()

    dot_str = dot.to_string()  # or dot.to_string()
    assert dot_str.startswith("digraph list {")


class TestDiagramCmdLine:
    def test_generate_image(self, tmp_path):
        out = tmp_path / "workflow.svg"

        main(["tests.examples.traffic_light_machine.TrafficLightMachine", str(out)])

        assert out.read_text().startswith(
            '<?xml version="1.0" encoding="UTF-8" standalone="no"?>\n<!DOCTYPE svg'
        )

    def test_generate_complain_about_bad_sm_path(self, capsys, tmp_path):
        out = tmp_path / "workflow.svg"

        expected_error = "TrafficLightMachineXXX is not a subclass of Workflow"
        with pytest.raises(ValueError, match=expected_error):
            main(
                [
                    "tests.examples.traffic_light_machine.TrafficLightMachineXXX",
                    str(out),
                ]
            )


class TestQuickChart:
    @contextmanager
    def mock_quickchart(self, origin_img_path):
        with open(origin_img_path) as f:
            expected_image = f.read()

        with mock.patch("workflow.contrib.diagram.urlopen", spec=True) as p:
            p().read.side_effect = lambda: expected_image.encode()
            yield p

    def test_should_call_write_svg(self, OrderControl):
        workflow = OrderControl()
        with self.mock_quickchart("docs/images/_oc_machine_processing.svg"):
            quickchart_write_svg(workflow, "docs/images/oc_machine_processing.svg")
