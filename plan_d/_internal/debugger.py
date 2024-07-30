from __future__ import annotations

import io
import subprocess
import sys

from contextlib import nullcontext
from contextlib import redirect_stdout
from typing import TYPE_CHECKING
from typing import TextIO

from IPython.core.alias import Alias
from IPython.terminal.debugger import TerminalPdb
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.terminal.ptutils import IPythonPTLexer
from madbg.debugger import RemoteIPythonDebugger
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import HasFocus
from prompt_toolkit.filters import IsDone
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.input.vt100 import Vt100Input
from prompt_toolkit.layout.processors import ConditionalProcessor
from prompt_toolkit.layout.processors import HighlightMatchingBracketProcessor
from prompt_toolkit.output.vt100 import Vt100_Output as Vt100Output


if TYPE_CHECKING:
    from contextlib import AbstractContextManager
    from typing import Callable


def default_hello_message(ip: str, port: int) -> str:
    return f"RemotePdb session open at {ip}:{port}, use 'plan-d debug {ip} {port}' to connect..."


def default_accepted_message(client_address: str) -> str:
    return f"RemotePdb accepted connection from {client_address}."


DEFAULT_PROMPT = "plan-d> "


class RemoteDebugger(RemoteIPythonDebugger):
    def __init__(
        self,
        stdin: TextIO,
        stdout: TextIO,
        term_type: str | None,
        **extra_pt_session_options,
    ) -> None:
        # fix annoying `Warning: Input is not a terminal (fd=0)`
        Vt100Input._fds_not_a_terminal.add(0)
        # A patch until https://github.com/ipython/ipython/issues/11745 is solved
        TerminalInteractiveShell.simple_prompt = False  # type: ignore[assignment]
        term_input = Vt100Input(stdin)
        term_output = Vt100Output.from_pty(stdout, term_type)

        TerminalPdb.__init__(
            self,
            pt_session_options={
                "input": term_input,
                "output": term_output,
                "lexer": IPythonPTLexer(),
                "prompt_continuation": (
                    lambda width, lineno, is_soft_wrap: PygmentsTokens(
                        self.shell.prompts.continuation_prompt_tokens(width)  # type: ignore[attr-defined]
                    )
                ),
                "multiline": True,
                "input_processors": [
                    # Highlight matching brackets, but only when this setting is
                    # enabled, and only when the DEFAULT_BUFFER has the focus.
                    ConditionalProcessor(
                        processor=HighlightMatchingBracketProcessor(chars="[](){}"),
                        filter=HasFocus(DEFAULT_BUFFER) & ~IsDone(),
                    )
                ],
                **extra_pt_session_options,
            },
            stdin=stdin,
            stdout=stdout,
        )

        self.use_rawinput = True
        self.done_callback = None

    @classmethod
    def connect_and_start(
        cls,
        ip: str,
        port: int,
        hello_message: Callable[[str, int], str] | None = None,
        accepted_message: Callable[[str], str] | None = None,
    ) -> AbstractContextManager[RemoteIPythonDebugger]:
        current_instance = cls._get_current_instance()
        if current_instance is not None:
            return nullcontext(current_instance)

        hello_message = hello_message or default_hello_message
        accepted_message = accepted_message or default_accepted_message

        with cls.get_server_socket(ip, port) as server_socket:
            server_socket.listen(1)
            print(
                hello_message(ip, server_socket.getsockname()[1]),
                file=sys.__stderr__,
                flush=True,
            )
            sock, address = server_socket.accept()
            print(
                accepted_message(address),
                file=sys.__stderr__,
                flush=True,
            )
        return cls.start_from_new_connection(sock)

    def onecmd(self, line: str) -> bool:
        """
        Invokes 'run_magic()' if the line starts with a '%'.
        The loop stops of this function returns True.
        (unless an overridden 'postcmd()' behaves differently)
        """
        try:
            line = line.strip()
            if line.startswith("%"):
                if line.startswith("%%"):
                    self.error(
                        "Cell magics (multiline) are not yet supported. "
                        "Use a single '%' instead."
                    )
                    return False
                self.run_magic(line[1:])
                return False
            return super().onecmd(line)

        except Exception as e:
            self.error(f"{type(e).__qualname__} in onecmd({line!r}): {e}")
            return False

    def run_magic(self, line) -> str:
        magic_name, arg, line = self.parseline(line)
        result = stdout = ""
        if hasattr(self, f"do_{magic_name}"):
            # We want to use do_{magic_name} methods if defined.
            # This is indeed the case with do_pdef, do_pdoc etc,
            # which are defined by our base class (IPython.core.debugger.Pdb).
            result = getattr(self, f"do_{magic_name}")(arg)
        else:
            assert self.shell
            magic_fn = self.shell.find_line_magic(magic_name)
            if not magic_fn:
                self.error(f"Line Magic %{magic_name} not found")
                return ""

            if isinstance(magic_fn, Alias):
                stdout, stderr = call_magic_fn(magic_fn, arg)
                if stderr:
                    self.error(stderr)
                    return ""
            else:
                std_buffer = io.StringIO()
                with redirect_stdout(std_buffer):
                    if magic_name in ("time", "timeit"):
                        f_globals = self.curframe.f_globals if self.curframe else {}
                        result = magic_fn(
                            arg,
                            local_ns={
                                **self.curframe_locals,
                                **f_globals,
                            },
                        )
                    else:
                        result = magic_fn(arg)
                stdout = std_buffer.getvalue()
        if stdout:
            self._print(stdout)
        if result is not None:
            self._print(result)
        return result

    def _print(self, message: str):
        self.stdout.write(message)


def call_magic_fn(alias: Alias, rest):
    cmd = alias.cmd
    nargs = alias.nargs
    # Expand the %l special to be the user's input line
    if cmd.find("%l") >= 0:
        cmd = cmd.replace("%l", rest)
        rest = ""

    if nargs == 0:
        if cmd.find("%%s") >= 1:
            cmd = cmd.replace("%%s", "%s")
        # Simple, argument-less aliases
        cmd = f"{cmd} {rest}"
    else:
        # Handle aliases with positional arguments
        args = rest.split(None, nargs)
        if len(args) < nargs:
            raise RuntimeError(
                f"Alias <{alias.name}> requires {nargs} arguments, {len(args)} given."
            )
        cmd = "{} {}".format(cmd % tuple(args[:nargs]), " ".join(args[nargs:]))
    return subprocess.Popen(
        cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.PIPE, text=True
    ).communicate()
