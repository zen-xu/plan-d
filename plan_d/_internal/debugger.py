from __future__ import annotations

import io
import os
import subprocess
import sys
import traceback

from contextlib import contextmanager, nullcontext, redirect_stderr, redirect_stdout
from termios import tcdrain
from types import TracebackType
from typing import TYPE_CHECKING, TextIO, cast

from IPython.core.alias import Alias
from IPython.terminal.debugger import TerminalPdb
from IPython.terminal.interactiveshell import TerminalInteractiveShell
from IPython.terminal.ptutils import IPythonPTLexer
from madbg.communication import Piping as _Piping
from madbg.communication import receive_message
from madbg.debugger import RemoteIPythonDebugger
from madbg.tty_utils import PTY, attach_ctty
from madbg.utils import run_thread
from prompt_toolkit.enums import DEFAULT_BUFFER
from prompt_toolkit.filters import HasFocus, IsDone
from prompt_toolkit.formatted_text import PygmentsTokens
from prompt_toolkit.input.vt100 import Vt100Input
from prompt_toolkit.layout.processors import (
    ConditionalProcessor,
    HighlightMatchingBracketProcessor,
)
from prompt_toolkit.output.vt100 import Vt100_Output as Vt100Output
from rich import box
from rich._inspect import Inspect as RichInspect
from rich.console import Console, ConsoleDimensions, Group, RenderableType
from rich.panel import Panel
from rich.pretty import Pretty
from rich.style import Style
from rich.syntax import Syntax
from rich.table import Table
from rich.text import Text
from rich.theme import Theme
from rich.traceback import Frame, PathHighlighter, Stack, Trace, Traceback
from rich.tree import Tree
from typing_extensions import Concatenate, ParamSpec

from . import utils


if TYPE_CHECKING:
    import socket

    from contextlib import AbstractContextManager
    from types import FrameType
    from typing import Any, Callable, Iterable


def default_hello_message(ip: str, port: int) -> str:
    return f"RemotePdb session open at {ip}:{port}, use 'plan-d debug {ip} {port}' to connect..."


def default_accepted_message(client_address: str) -> str:
    return f"RemotePdb accepted connection from {client_address}."


_ConsolePrintArgs = ParamSpec("_ConsolePrintArgs")


if TYPE_CHECKING:

    def as_console_printer_builder(
        f: Callable[Concatenate[Console, _ConsolePrintArgs], None],
    ) -> Callable[
        [Callable],
        Callable[_ConsolePrintArgs, None],
    ]: ...

    as_console_printer = as_console_printer_builder(Console.print)

else:

    def as_console_printer(f):
        return f


class RemoteDebugger(RemoteIPythonDebugger):
    def __init__(
        self,
        stdin: TextIO,
        stdout: TextIO,
        term_type: str | None,
        console: Console | None = None,
        syntax_theme: str = "ansi_dark",
        exception_max_frames: int = 100,
        disable_magic_cmd: bool = False,
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

        def stdout_write_wrapper(write):
            def wrapper(*args, **kwargs):
                while True:
                    try:
                        return write(*args, **kwargs)
                    except io.BlockingIOError:
                        import time

                        time.sleep(0.01)

            return wrapper

        stdout.write = stdout_write_wrapper(stdout.write)  # type: ignore[method-assign]

        self.console = console or Console(
            file=stdout,
            stderr=True,
            force_terminal=True,
            force_interactive=True,
            tab_size=4,
            theme=Theme(
                {"info": "dim cyan", "warning": "magenta", "danger": "bold red"}
            ),
        )
        self.syntax_theme = syntax_theme
        self.skip_print_stack_entry = False
        self.exception_max_frames = exception_max_frames
        self.disable_magic_cmd = disable_magic_cmd

    @classmethod
    @contextmanager
    def start(cls, sock: socket.socket):
        assert cls._get_current_instance() is None
        sock_fd = sock.fileno()
        term_data = receive_message(sock_fd)
        term_size: tuple[int, int]
        term_attrs, term_type, term_size = (
            term_data["term_attrs"],
            term_data["term_type"],
            term_data["term_size"],
        )
        rows, cols = term_size
        with PTY.open() as pty:
            pty.resize(rows, cols)
            pty.set_tty_attrs(term_attrs)
            sock_address, _ = sock.getpeername()
            if sock_address != "127.0.0.1":
                pty.make_ctty()
            else:
                attach_ctty(pty.slave_fd)
            piping = Piping(
                {sock_fd: {pty.master_fd}, pty.master_fd: {sock_fd}}, sock_fd, pty
            )
            with run_thread(piping.run):
                slave_reader = os.fdopen(pty.slave_fd, "r", encoding="utf-8")
                slave_writer = os.fdopen(pty.slave_fd, "w", encoding="utf-8")
                try:
                    instance = cls(slave_reader, slave_writer, term_type)
                    instance.console.size = ConsoleDimensions(cols, rows)
                    cls._set_current_instance(instance)
                    yield instance
                except Exception:
                    print(traceback.format_exc(), file=slave_writer)
                    raise
                finally:
                    cls._set_current_instance(None)
                    print("Closing connection", file=slave_writer, flush=True)
                    tcdrain(pty.slave_fd)
                    slave_writer.close()

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

    @classmethod
    @contextmanager
    def start_from_new_connection(cls, sock: socket.socket):
        # mute the madbg start_from_new_connection
        try:
            with cls.start(sock) as debugger:
                yield debugger
        finally:
            sock.close()

    # =========== commands ===========

    def do_pinfo(self, arg):
        """
        Provide detailed information about an object.

        The debugger interface to %pinfo, i.e., obj?.
        """
        self.do_inspect(
            arg,
            help=True,
            subclasses=True,
            value=False,
            methods=False,
            attrs=False,
        )

    def do_pinfo2(self, arg):
        """
        Provide extra detailed information about an object.

        The debugger interface to %pinfo2, i.e., obj??.
        """
        self.do_inspect(
            arg,
            help=True,
            subclasses=True,
            value=False,
            methods=False,
            attrs=False,
            source=True,
        )

    # These commands is referenced from https://github.com/cansarigol/pdbr/tree/master/pdbr
    def do_v(self, arg):
        """v(ars)
        List of local variables
        """
        self.message(self.get_vars_table())

    do_vars = do_v

    def do_varstree(self, arg):
        """varstree | vt
        List of local variables in Rich.Tree
        """
        self.message(self.get_vars_tree())

    do_vt = do_varstree

    def do_inspect(self, arg, **kwargs):
        """(i)nspect
        Display the data / methods / docs for any Python object.
        """
        kwargs.setdefault("all", False)
        kwargs.setdefault("methods", True)
        if isinstance(arg, str):
            arg = self._getval(arg)
        self.message(Inspect(arg, **kwargs))

    do_i = do_inspect

    def do_inspectall(self, arg):
        """inspectall | ia
        Inspect with all to see all attributes.
        """
        self.do_inspect(arg, all=True)

    do_ia = do_inspectall

    # =========== override methods ===========

    def onecmd(self, line: str) -> bool:
        """
        Invokes 'run_magic()' if the line starts with a '%'.
        The loop stops of this function returns True.
        (unless an overridden 'postcmd()' behaves differently)
        """
        try:
            with self.redirect_std_stream_to_console():
                line = line.strip()
                if line.startswith("%") and not self.disable_magic_cmd:
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

    @as_console_printer
    def error(self, msg, *args, **kwargs) -> None:
        self.console.print(msg, *args, **kwargs)

    @as_console_printer
    def message(self, msg, *args, **kwargs) -> None:
        self.console.print(msg, *args, **kwargs)

    def setup(self, f: FrameType | None, tb: TracebackType | None) -> None:
        if tb:
            import decorator

            import plan_d

            self.console.print_exception(
                word_wrap=True,
                suppress=[plan_d, decorator],
                max_frames=self.exception_max_frames,
            )
            self.skip_print_stack_entry = True

        return super().setup(f, tb)

    def print_stack_trace(self, context=None):
        tb = Traceback(
            Trace(
                stacks=[
                    Stack(
                        is_cause=False,
                        exc_type="",
                        exc_value="",
                        frames=[
                            Frame(
                                frame.f_code.co_filename,
                                lineno=lineno,
                                name=frame.f_code.co_name,
                            )
                            for frame, lineno in self.stack
                            if frame.f_locals.get("__tracebackhide__") is not True
                        ],
                    )
                ]
            )
        )
        self.message(tb, soft_wrap=False)

    def print_stack_entry(
        self,
        frame_lineno: tuple[FrameType, int],
        prompt_prefix="\n-> ",
        context=None,
    ):
        if self.skip_print_stack_entry:
            self.skip_print_stack_entry = False
            return

        frame, lineno = frame_lineno
        traceback = TracebackType(
            tb_next=None, tb_frame=frame, tb_lasti=frame.f_lasti, tb_lineno=lineno
        )
        # use ValueError as a dummy exception
        tb = Traceback.from_exception(
            ValueError, ValueError(""), traceback, word_wrap=True
        )
        for stack in tb.trace.stacks:
            stack.is_cause = False
            stack.exc_type = ""
            stack.exc_value = ""
        self.message(tb, soft_wrap=False)

    def print_list_lines(self, filename: str, first: int, last: int):
        codes = Syntax.from_path(
            filename,
            line_numbers=True,
            theme=self.syntax_theme,
            line_range=(first, last),
            highlight_lines={self.curframe.f_lineno},  # type: ignore[attr-defined]
            indent_guides=True,
        )
        self.message(codes)

    def print_topics(
        self, header: str, cmds: list[str] | None, cmdlen: int, maxcol: int
    ) -> None:
        cmds = cmds or []
        # Get the console width
        console_width = self.console.width

        # Determine the length of the longest string
        max_item_length = max(len(item) for item in cmds)

        # Calculate the maximum number of columns that fit within the console width
        # Add 2 to max_item_length for padding, and 3 for column separation (|--)
        column_width = max_item_length + 2
        num_columns = min(max(1, (console_width + 1) // (column_width + 3)), len(cmds))

        # Calculate the number of rows needed
        num_rows = -(-len(cmds) // num_columns)  # Equivalent to math.ceil

        # Create a Table object
        table = Table(
            title=header,
            show_header=False,
            expand=True,
            box=box.SIMPLE_HEAD,
            title_style=Style(color="cyan", bold=True, italic=True),
        )

        # Add columns to the table
        for col_index in range(num_columns):
            table.add_column(
                str(col_index), justify="center", style=Style(color="yellow")
            )

        # Fill the table with the items
        for row_index in range(num_rows):
            row_data = []
            for col_index in range(num_columns):
                # Calculate the index in the string_list
                item_index = row_index + col_index * num_rows
                # Append the item if the index is within the list's length
                if item_index < len(cmds):
                    row_data.append(cmds[item_index])
                else:
                    row_data.append("")  # Fill with empty string if out of range
            table.add_row(*row_data)

        # Print the table to the console
        self.message(table)

    # =========== methods ===========

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
                if stdout:
                    self.message(Text.from_ansi(stdout).plain)
                if stderr:
                    self.error(Text.from_ansi(stderr).plain)
                    return ""
            else:
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
        if result is not None:
            self.message("")
            self.message(result)
        return result

    @contextmanager
    def redirect_std_stream_to_console(self):
        class StdoutWrapper(io.StringIO):
            def __init__(self, debugger: RemoteDebugger):
                self.debugger = debugger

            def write(self, data):
                self.debugger.message(Text.from_ansi(data).plain, end="")

            def flush(self): ...

        class StderrWrapper(io.StringIO):
            def __init__(self, debugger: RemoteDebugger):
                self.debugger = debugger

            def write(self, data):
                self.debugger.error(Text.from_ansi(data), end="")

            def flush(self): ...

        with redirect_stdout(StdoutWrapper(self)), redirect_stderr(StderrWrapper(self)):
            yield

    def get_variables(self) -> list[tuple[str, str, str]]:
        curframe = self.curframe
        if curframe is None:
            return []

        return [
            (k, str(v), str(type(v)))
            for k, v in curframe.f_locals.items()
            if not k.startswith("__")
        ]

    def get_vars_table(self):
        variables = self.get_variables()
        if not variables:
            return
        table = Table(title="List of local variables", box=box.MINIMAL)

        table.add_column("Variable", style="cyan")
        table.add_column("Value", style="magenta")
        table.add_column("Type", style="green")
        [table.add_row(variable, value, _type) for variable, value, _type in variables]
        return table

    def get_vars_tree(self) -> Tree | None:
        variables = self.get_variables()
        if not variables:
            return None
        tree_key = ""
        type_tree = None
        tree = Tree("Variables")

        for variable, value, _type in sorted(
            variables, key=lambda item: (item[2], item[0])
        ):
            if tree_key != _type:
                if tree_key != "" and type_tree:
                    tree.add(type_tree, style="bold green")
                type_tree = Tree(_type)
                tree_key = _type
            if type_tree:
                type_tree.add(f"{variable}: {value}", style="magenta")
        if type_tree:
            tree.add(type_tree, style="bold green")
        return tree


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


class Piping(_Piping):
    def __init__(self, pipe_dict: dict[int, set[int]], client_fd: int, pty: PTY):
        super().__init__(pipe_dict)
        self.client_fd = client_fd
        self.pty = pty

    def _read(self, src_fd, dest_fds):
        try:
            data = os.read(src_fd, 1024)
            if src_fd == self.client_fd and (
                term_size := utils.try_deserialize_terminal_size(data)
            ):
                if debugger := RemoteDebugger._get_current_instance():
                    rows, cols = term_size
                    debugger = cast(RemoteDebugger, debugger)
                    debugger.console.size = ConsoleDimensions(cols, rows)
                self.pty.resize(*term_size)
                return
        except OSError:
            data = ""
        if data:
            for dest_fd in dest_fds:
                self.buffers[dest_fd] += data
        else:
            self._remove_reader(src_fd)
            if src_fd in self.writers_to_readers:
                self._remove_writer(src_fd)
            if not self.readers_to_writers:
                self.loop.stop()


class Inspect(RichInspect):
    def __init__(
        self,
        obj: Any,
        *,
        title: str | Text | None = None,
        help: bool = False,
        methods: bool = False,
        docs: bool = True,
        private: bool = False,
        dunder: bool = False,
        sort: bool = True,
        all: bool = True,
        value: bool = True,
        source: bool = False,
        subclasses: bool = False,
        attrs: bool = True,
    ) -> None:
        super().__init__(
            obj,
            title=title,
            help=help,
            methods=methods,
            docs=docs,
            private=private,
            dunder=dunder,
            sort=sort,
            all=all,
            value=value,
        )
        self.subclasses = subclasses
        self.source = source
        self.attrs = attrs

    def _render(self) -> Iterable[RenderableType]:
        renders = list(super()._render())
        if self.attrs:
            yield from renders
        else:
            yield from [obj for obj in renders if not isinstance(obj, Table)]

        if self.subclasses and (
            subclasses := getattr(self.obj, "__subclasses__", None)
        ):
            yield ""
            yield Panel(
                Group(
                    *[
                        Pretty(subclass, highlighter=self.highlighter)
                        for subclass in subclasses()
                    ]
                ),
                title="subclasses",
                border_style="scope.border",
            )

        if self.source and (file_path := getattr(self.obj, "__file__", None)):
            yield ""
            yield Panel(
                Syntax.from_path(
                    file_path,
                    lexer="python",
                    line_numbers=True,
                ),
                box=box.SIMPLE,
                title=PathHighlighter()(file_path),
                border_style="scope.border",
            )
