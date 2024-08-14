import warnings
from typing import Dict
from typing import Type

from agentkit.utils.workflow import qualname

try:
    from django.utils.module_loading import autodiscover_modules
except ImportError:  # pragma: no cover
    # Not a django project
    def autodiscover_modules(module_name: str):
        pass


_initialized: bool = False
_REGISTRY: Dict[str, Type[object]] = {}


def register(cls):
    _REGISTRY[qualname(cls)] = cls
    _REGISTRY[cls.__name__] = cls
    return cls


def get_machine_cls(name):
    init_registry()
    if "." not in name:
        warnings.warn(
            """Use fully qualified names (<module>.<class>) for state flow mixins.""",
            DeprecationWarning,
            stacklevel=2,
        )
    return _REGISTRY[name]


def init_registry():
    global _initialized
    if not _initialized:
        load_modules(["workflow", "statemachines"])
        _initialized = True


def load_modules(modules=None):
    if modules is None:
        warnings.warn(
            """Modules cannot be None""",
            DeprecationWarning,
            stacklevel=2,
        )
    else:
        for module in modules:
            autodiscover_modules(module)
