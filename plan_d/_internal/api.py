from __future__ import annotations

import os

from contextlib import suppress
from inspect import currentframe
from pdb import Pdb
from typing import TYPE_CHECKING
from typing import Callable

from IPython.core.debugger import Pdb as IPdb


if TYPE_CHECKING:
    from types import FrameType

    from rich.console import Console

ENV_VAR_IP = "PLAND_IP"
ENV_VAR_PORT = "PLAND_PORT"
ENV_VAR_AUTO_SELECT_PORT = "PLAND_AUTO_SELECT_PORT"
ENV_VAR_DISABLE_RICH = "PLAND_DISABLE_RICH"


DEFAULT_IP = "localhost"
DEFAULT_PORT = 3513
DEFAULT_PROMPT = "plan-d> "

BAN_CMDS = {"list"}


def set_trace(
    frame: FrameType | None = None,
    ip: str | None = None,
    port: int | None = None,
    hello_message: Callable[[str, int], str] | None = None,
    accepted_message: Callable[[str], str] | None = None,
    prompt: str | None = None,
    console: Console | None = None,
    syntax_theme: str | None = None,
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

    if not console:
        with suppress(ImportError):
            from rich.console import Console
            from rich.theme import Theme

            console = Console(
                file=debugger.stdout,
                height=debugger.height,
                width=debugger.width,
                stderr=True,
                force_terminal=True,
                force_interactive=True,
                tab_size=4,
                theme=Theme(
                    {"info": "dim cyan", "warning": "magenta", "danger": "bold red"}
                ),
            )

    if os.getenv(ENV_VAR_DISABLE_RICH, "no").lower() in ["1", "true", "yes"]:
        debugger.console = None
    else:
        debugger.console = console

    if syntax_theme:
        debugger.syntax_theme = syntax_theme

    for ban_cmd in BAN_CMDS:
        with suppress(AttributeError):
            delattr(Pdb, f"do_{ban_cmd}")

        with suppress(AttributeError):
            delattr(IPdb, f"do_{ban_cmd}")

    debugger.set_trace(frame, done_callback=exit_stack.close)
