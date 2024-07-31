from __future__ import annotations

import os
import signal
import sys
import traceback as tb

from contextlib import suppress
from inspect import currentframe
from pdb import Pdb
from termios import tcdrain
from typing import TYPE_CHECKING
from typing import Callable
from typing import cast

from IPython.core.debugger import Pdb as IPdb
from madbg import client as madbg_client
from madbg.communication import Piping
from madbg.communication import send_message
from madbg.utils import use_context

from . import utils
from .debugger import RemoteDebugger


if TYPE_CHECKING:
    from types import FrameType
    from types import TracebackType

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
    debugger = _config_debugger(debugger, prompt, console, syntax_theme)
    debugger.set_trace(frame, done_callback=exit_stack.close)


def post_mortem(
    traceback: TracebackType | None = None,
    ip: str | None = None,
    port: int | None = None,
    hello_message: Callable[[str, int], str] | None = None,
    accepted_message: Callable[[str], str] | None = None,
    prompt: str | None = None,
    console: Console | None = None,
    syntax_theme: str | None = None,
) -> None:
    traceback = traceback or sys.exc_info()[2] or sys.last_traceback
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

    with RemoteDebugger.connect_and_start(
        ip,
        port,
        hello_message=hello_message,
        accepted_message=accepted_message,
    ) as debugger:
        debugger = cast(RemoteDebugger, debugger)
        debugger = _config_debugger(debugger, prompt, console, syntax_theme)
        if debugger.console:
            debugger.console.print_exception()
        else:
            debugger.message(*tb.format_exception(*sys.exc_info()))
        debugger.post_mortem(traceback)


def _config_debugger(
    debugger: RemoteDebugger,
    prompt: str | None = None,
    console: Console | None = None,
    syntax_theme: str | None = None,
) -> RemoteDebugger:
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
        if console:
            # Leave as None to auto-detect width.
            console.size = (None, None)  # type: ignore[assignment]
        debugger.console = console

    if syntax_theme:
        debugger.syntax_theme = syntax_theme

    for ban_cmd in BAN_CMDS:
        with suppress(AttributeError):
            delattr(Pdb, f"do_{ban_cmd}")

        with suppress(AttributeError):
            delattr(IPdb, f"do_{ban_cmd}")

    return debugger


def connect_to_debugger(
    ip=DEFAULT_IP,
    port=DEFAULT_PORT,
    timeout=madbg_client.DEFAULT_CONNECT_TIMEOUT,
    in_fd=madbg_client.STDIN_FILENO,
    out_fd=madbg_client.STDOUT_FILENO,
):
    with madbg_client.connect_to_server(ip, port, timeout) as socket:
        tty_handle = madbg_client.get_tty_handle()
        term_size = utils.get_terminal_size()
        term_data = {
            "term_attrs": madbg_client.tcgetattr(tty_handle),
            # prompt toolkit will receive this string, and it can be 'unknown'
            "term_type": os.environ.get("TERM", "unknown"),
            "term_size": (term_size.lines, term_size.columns),
        }
        send_message(socket, term_data)

        def send_terminal_size(signum, frame):
            utils.send_terminal_size(socket)

        signal.signal(signal.SIGWINCH, send_terminal_size)

        with madbg_client.prepare_terminal():
            socket_fd = socket.fileno()
            Piping({in_fd: {socket_fd}, socket_fd: {out_fd}}).run()
            tcdrain(out_fd)
