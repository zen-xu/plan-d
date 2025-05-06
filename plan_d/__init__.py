from __future__ import annotations


__version__ = "0.2.4"
__authors__ = [
    "ZhengYu, Xu <zen-xu@outlook.com>",
]

from ._internal.api import connect_to_debugger as connect_to_debugger
from ._internal.api import launch_pland_on_exception as launch_pland_on_exception
from ._internal.api import post_mortem as post_mortem
from ._internal.api import set_trace as set_trace


# lpe is an alias for launch_pland_on_exception
lpe = launch_pland_on_exception
