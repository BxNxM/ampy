import shutil
import sys
from functools import update_wrapper
from pathlib import Path
from typing import Optional, List

import click
import dotenv
import serial
from bullet import Bullet, Check
from halo import Halo

from ampy.core import board_finder, firmware_builder
from ampy.core.settings import DEV_MODULE
from ampy.core.util import clean_mpy_repo, update_mpy_repo

ESP32_FAIL_MSG = """\
\tNote: If you're using an ESP32, you may need to hold down the 'BOOT' button on your device while runing this command.
\t      Read more @ https://randomnerdtutorials.com/solved-failed-to-connect-to-esp32-timed-out-waiting-for-packet-header/\
"""

# Load AMPY_PORT et al from ~/.ampy file
# Performed here because we need to beat click's decorators.
config = dotenv.find_dotenv(filename=".ampy", usecwd=True)
if config:
    dotenv.load_dotenv(dotenv_path=config)


@click.group()
@click.option(
    "--port",
    "-p",
    envvar="AMPY_PORT",
    required=False,
    help="Name of serial port for connected board.\n\n"
    "Can be optionally specified with 'AMPY_PORT' environment variable.",
)
@click.option(
    "--baud",
    "-b",
    envvar="AMPY_BAUD",
    default=115200,
    help="Baud rate for the serial connection (default 115200).\n\n"
    "Can be optionally specified with 'AMPY_BAUD' environment variable.",
)
@click.pass_context
def cli(ctx: click.Context, port: Optional[str], baud: int):
    ctx.obj = {"port": port, "baud": baud}


def find_boards() -> List[board_finder.MpyBoard]:
    obj = click.get_current_context().obj
    port = obj["port"]
    baud = obj["baud"]

    with Halo(
        text="Finding boards connected to your computer", spinner="dots"
    ) as spinner:
        if port is not None:
            boards = [board_finder.detect_board(port, baud)]
        else:
            boards = list(board_finder.main(baud))

        if not boards:
            spinner.fail(click.style("No boards detected!", fg="red"))
            print(ESP32_FAIL_MSG)
            exit()
        spinner.succeed()

    return boards


def pass_many_boards(f):
    def new_func(*args, **kwargs):
        boards = find_boards()

        if len(boards) > 1:
            choices = {str(it): it for it in boards}
            boards = [
                choices[it]
                for it in Check(
                    prompt="Please choose any number of boards you want",
                    choices=list(choices.keys()),
                ).launch()
            ]

        f(boards, *args, **kwargs)

    return update_wrapper(new_func, f)


def pass_single_board(f):
    def new_func(*args, **kwargs):
        boards = find_boards()

        if len(boards) > 1:
            choices = {str(it): it for it in boards}
            board = choices[
                Bullet(
                    prompt="Please choose a single board", choices=list(choices.keys())
                ).launch()
            ]
        else:
            board = boards[0]

        f(board, *args, **kwargs)

    return update_wrapper(new_func, f)


@cli.add_command
@click.command(
    help="List all micropython boards attached via USB serial port.\n\n"
    "Will soft-reset all devices when run."
)
def devices():
    for board in find_boards():
        print(repr(board))


@cli.add_command
@click.command(help="Stream logs from device.")
@pass_single_board
def logs(board: board_finder.MpyBoard):
    print(f"Streaming output for: {board}.\n" f"You may need to reset the device once.")
    with serial.Serial(board.port, baudrate=board.baud) as ser:
        ser.flush()
        while True:
            sys.stdout.buffer.write(ser.read(1))
            sys.stdout.buffer.flush()


@cli.add_command
@click.command(help="Flash micropython firmware.")
@click.argument("firmware", type=click.Path(exists=True, resolve_path=True))
@pass_many_boards
def flash(boards: List[board_finder.MpyBoard], firmware):
    for board in boards:
        print(f"Flashing firmware to board: {board}")
        board.flash(Path(firmware))


@cli.add_command
@click.command(help="Build micropython firmware.")
@click.option(
    "--clean", "-c", is_flag=True, help="Clean local build cache.", is_eager=True
)
@click.option("--mpy-version", "-v", help="Micropython repo's git tag or branch.")
@click.option(
    "--dev",
    "-d",
    is_flag=True,
    help="Build the ampy development firmware.",
    is_eager=True,
)
@click.option(
    "--module",
    "-m",
    type=click.Path(exists=True, resolve_path=True),
    multiple=True,
    help="Path to python module / python script. Can be used multiple times.",
)
@click.option(
    "--entrypoint",
    "-e",
    multiple=True,
    help="Module or function to be executed on boot. Can be used multiple times.",
)
@click.option("--yes", "-y", is_flag=True)
@click.option("--output-path", "-o")
@pass_many_boards
def build(
    boards: List[board_finder.MpyBoard],
    clean: bool,
    module: List[str],
    entrypoint: List[str],
    yes: bool,
    dev: bool,
    output_path: str,
        mpy_version: str
):
    if clean:
        clean_mpy_repo()
        return

    if output_path and len(boards) > 1:
        print(
            click.style(
                "The '--output-path' option is ambiguous with multiple boards attached.",
                fg="red",
            )
        )

    if dev:
        if module or entrypoint:
            print(
                click.style(
                    "The '--dev' switch is not compatible with '--module' or '--entrypoint'",
                    fg="red",
                )
            )
        module = [DEV_MODULE]
        entrypoint = []

    update_mpy_repo(mpy_version)

    for board in boards:
        print("Building firmware for:", board)
        firmware = firmware_builder.main(board, entrypoint, [Path(i) for i in module])

        if output_path is not None:
            shutil.copy(firmware, output_path)
            firmware = output_path

        print("Built firmware:", firmware)

        if not yes and not click.confirm(
            "Do you want to flash this firmware right now? You can flash it later using:"
            f"\n\t$ ampy flash {firmware}\n"
        ):
            continue

        board.flash(Path(firmware))


if __name__ == "__main__":
    cli()
