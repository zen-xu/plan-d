from __future__ import annotations

import os

from inspect import currentframe
from typing import TYPE_CHECKING
from typing import Callable


if TYPE_CHECKING:
    from types import FrameType


ENV_VAR_IP = "PLAND_IP"
ENV_VAR_PORT = "PLAND_PORT"
ENV_VAR_AUTO_SELECT_PORT = "PLAND_AUTO_SELECT_PORT"

DEFAULT_IP = "localhost"
DEFAULT_PORT = 3513
DEFAULT_PROMPT = "plan-d> "


def set_trace(
    frame: FrameType | None = None,
    ip: str | None = None,
    port: int | None = None,
    hello_message: Callable[[str, int], str] | None = None,
    accepted_message: Callable[[str], str] | None = None,
    prompt: str | None = None,
) -> None:
    from madbg.utils import use_context

    from .debugger import RemoteDebugger

    frame = frame or currentframe().f_back  # type: ignore[union-attr]
    assert frame

    ip = ip or str(os.getenv(ENV_VAR_IP, DEFAULT_IP))
    if os.getenv(ENV_VAR_AUTO_SELECT_PORT, "no").lower() in [
        "1",
        "yes",
        "true",
    ]:
        default_port = 0
    else:
        default_port = DEFAULT_PORT
    port = port or int(os.getenv(ENV_VAR_PORT, default_port))

    debugger: RemoteDebugger
    debugger, exit_stack = use_context(
        RemoteDebugger.connect_and_start(
            ip,
            port,
            hello_message=hello_message,
            accepted_message=accepted_message,
        )
    )
    prompt = prompt or DEFAULT_PROMPT
    if not prompt.endswith(" "):
        prompt += " "
    debugger.prompt = prompt
    debugger.set_trace(frame, done_callback=exit_stack.close)
