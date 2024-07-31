from __future__ import annotations

import os

from typing import TYPE_CHECKING

from madbg import client as madbg_client


if TYPE_CHECKING:
    from socket import SocketType


def send_terminal_size(socket: SocketType):
    term_size = get_terminal_size()
    socket.sendall(serialize_terminal_size(term_size))


def serialize_terminal_size(size: os.terminal_size) -> bytes:
    return f"terminal_size:{size.lines},{size.columns}".encode()


def try_deserialize_terminal_size(data: bytes) -> tuple[int, int] | None:
    if not data.startswith(b"terminal_size:"):
        return None
    data_str = data.decode()

    data_str = data_str[len("terminal_size:") :]

    lines, columns = map(int, data_str.split(","))
    return lines, columns


def get_terminal_size():
    tty_handle = madbg_client.get_tty_handle()
    return os.get_terminal_size(tty_handle)
