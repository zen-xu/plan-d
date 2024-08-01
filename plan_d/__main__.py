from __future__ import annotations

import click

from . import __version__, connect_to_debugger


@click.version_option(__version__, "-v", "--version")
@click.group
def cli(): ...


@cli.command
@click.argument("ip")
@click.argument("port", type=int)
@click.option(
    "-t",
    "--timeout",
    type=float,
    default=10,
    show_default=True,
    help="Connection timeout in seconds",
)
def debug(ip: str, port: int, timeout: float) -> None:
    """
    Connect the debugger to a remote server.
    """
    try:
        connect_to_debugger(ip, port, timeout=timeout)
    except (ConnectionRefusedError, TimeoutError):
        raise click.ClickException("Connection refused - did you use the right port?")  # noqa: B904


if __name__ == "__main__":
    cli()
