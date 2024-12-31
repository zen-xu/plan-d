from __future__ import annotations

import os
import signal
import socket
import sys

from contextlib import suppress
from inspect import currentframe
from pdb import Pdb
from termios import tcdrain
from typing import TYPE_CHECKING, Callable, Generator, TypeVar, cast

from decorator import contextmanager
from IPython.core.debugger import Pdb as IPdb
from madbg import client as madbg_client
from madbg.communication import Piping, send_message
from madbg.utils import use_context
from typing_extensions import Concatenate, ParamSpec

from . import utils
from .debugger import RemoteDebugger


if TYPE_CHECKING:
    from types import FrameType, TracebackType

    from rich.console import Console


ENV_VAR_IP = "PLAND_IP"
ENV_VAR_PORT = "PLAND_PORT"

DEFAULT_IP = socket.gethostbyname(socket.gethostname())
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
    disable_magic_cmd: bool | None = None,
) -> None:
    frame = frame or currentframe().f_back  # type: ignore[union-attr]
    assert frame

    ip = ip or str(os.getenv(ENV_VAR_IP, DEFAULT_IP))
    if port is None:
        port = int(os.getenv(ENV_VAR_PORT, 0))
    debugger: RemoteDebugger
    debugger, exit_stack = use_context(
        RemoteDebugger.connect_and_start(
            ip,
            port,
            hello_message=hello_message,
            accepted_message=accepted_message,
        )
    )
    debugger = _config_debugger(
        debugger, prompt, console, syntax_theme, disable_magic_cmd
    )
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
    disable_magic_cmd: bool | None = None,
    exception_max_frames: int = 100,
) -> None:
    traceback = traceback or sys.exc_info()[2] or sys.last_traceback
    ip = ip or str(os.getenv(ENV_VAR_IP, DEFAULT_IP))
    if port is None:
        port = int(os.getenv(ENV_VAR_PORT, 0))

    with RemoteDebugger.connect_and_start(
        ip,
        port,
        hello_message=hello_message,
        accepted_message=accepted_message,
    ) as debugger:
        debugger = cast(RemoteDebugger, debugger)
        debugger = _config_debugger(
            debugger, prompt, console, syntax_theme, disable_magic_cmd
        )
        debugger.exception_max_frames = exception_max_frames
        debugger.post_mortem(traceback)


def _config_debugger(
    debugger: RemoteDebugger,
    prompt: str | None = None,
    console: Console | None = None,
    syntax_theme: str | None = None,
    disable_magic_cmd: bool | None = None,
) -> RemoteDebugger:
    prompt = prompt or DEFAULT_PROMPT
    if not prompt.endswith(" "):
        prompt += " "
    debugger.prompt = prompt

    if console:
        debugger.console = console

    if syntax_theme:
        debugger.syntax_theme = syntax_theme

    if disable_magic_cmd is not None:
        debugger.disable_magic_cmd = disable_magic_cmd

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
) -> None:
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


_P = ParamSpec("_P")
_T = TypeVar("_T")

if TYPE_CHECKING:
    from types import TracebackType

    def like_post_mortem_args_builder(
        _: Callable[Concatenate[TracebackType | None, _P], None],
    ) -> Callable[[Callable[..., _T]], Callable[_P, _T]]: ...

    like_post_mortem_args = like_post_mortem_args_builder(post_mortem)
else:

    def like_post_mortem_args(f):
        return f


@contextmanager
@like_post_mortem_args
def launch_pland_on_exception(*args, **kwargs) -> Generator[None, None, None]:
    """
    Automatically launch plan-d debugger when an exception is raised.

    `launch_pland_on_exception` can be used as a context manager or a decorator.

    .. code-block:: python
        import plan_d


        def func1():
            with plan_d.launch_pland_on_exception():
                value1 = 1
                value2 = 2
                result = value1 + value2 / 0
                return result


        @plan_d.launch_pland_on_exception()
        def func2():
            value1 = 1
            value2 = 2
            result = value1 + value2 / 0
            return result
    """

    __tracebackhide__ = True
    try:
        yield
    except Exception:
        _, m, tb = sys.exc_info()
        print(m.__repr__(), file=sys.stderr)
        post_mortem(tb, *args, **kwargs)
        raise
    finally:
        pass
