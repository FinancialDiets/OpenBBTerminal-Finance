"""Terminal helper"""
__docformat__ = "numpy"

# IMPORTATION STANDARD
import webbrowser
from contextlib import contextmanager
import hashlib
import logging
import os
import subprocess  # nosec
import sys
from typing import List

# IMPORTATION THIRDPARTY
import requests
import matplotlib.pyplot as plt

# IMPORTATION INTERNAL
from openbb_terminal.config_terminal import LOGGING_APP_NAME, LOGGING_COMMIT_HASH
from openbb_terminal import feature_flags as obbff
from openbb_terminal import thought_of_the_day as thought
from openbb_terminal.rich_config import console

# pylint: disable=too-many-statements,no-member,too-many-branches,C0302

try:
    __import__("git")
except ImportError:
    WITH_GIT = False
else:
    WITH_GIT = True
logger = logging.getLogger(__name__)


def print_goodbye():
    """Prints a goodbye message when quitting the terminal"""
    # LEGACY GOODBYE MESSAGES - You'll live in our hearts forever.
    # "An informed ape, is a strong ape."
    # "Remember that stonks only go up."
    # "Diamond hands."
    # "Apes together strong."
    # "This is our way."
    # "Keep the spacesuit ape, we haven't reached the moon yet."
    # "I am not a cat. I'm an ape."
    # "We like the terminal."
    # "...when offered a flight to the moon, nobody asks about what seat."

    console.print(
        "[param]The OpenBB Terminal is the result of a strong community building an "
        "investment research platform for everyone, anywhere.[/param]\n"
    )

    console.print(
        "We are always eager to welcome new contributors and you can find our open jobs here:\n"
        "[cmds]https://www.openbb.co/company/careers#open-roles[/cmds]\n"
    )

    console.print(
        "Join us           : [cmds]https://openbb.co/discord[/cmds]\n"
        "Follow us         : [cmds]https://twitter.com/openbb_finance[/cmds]\n"
        "Ask support       : [cmds]https://openbb.co/support[/cmds]\n"
        "Request a feature : [cmds]https://openbb.co/request-a-feature[/cmds]\n"
    )

    console.print(
        "[bold]Fill in our 2-minute survey so we better understand how we can improve the OpenBB Terminal "
        "at [cmds]https://openbb.co/survey[/cmds][/bold]\n"
    )

    console.print(
        "[param]In the meantime access investment research from your chatting platform using the OpenBB Bot[/param]\n"
        "Try it today, for FREE: [cmds]https://openbb.co/products/bot[/cmds]\n"
    )
    logger.info("END")


def sha256sum(filename):
    h = hashlib.sha256()
    b = bytearray(128 * 1024)
    mv = memoryview(b)
    with open(filename, "rb", buffering=0) as f:
        for n in iter(lambda: f.readinto(mv), 0):
            h.update(mv[:n])
    return h.hexdigest()


def update_terminal():
    """Updates the terminal by running git pull in the directory.
    Runs poetry install if needed.
    """
    if not WITH_GIT or LOGGING_COMMIT_HASH != "REPLACE_ME":
        console.print("This feature is not available: Git dependencies not installed.")
        return 0

    poetry_hash = sha256sum("poetry.lock")

    completed_process = subprocess.run("git pull", shell=True, check=False)  # nosec
    if completed_process.returncode != 0:
        return completed_process.returncode

    new_poetry_hash = sha256sum("poetry.lock")

    if poetry_hash == new_poetry_hash:
        console.print("Great, seems like poetry hasn't been updated!")
        return completed_process.returncode
    console.print(
        "Seems like more modules have been added, grab a coke, this may take a while."
    )

    completed_process = subprocess.run(  # nosec
        "poetry install", shell=True, check=False
    )
    if completed_process.returncode != 0:
        return completed_process.returncode

    return 0


def open_openbb_documentation(
    path, url="https://openbb-finance.github.io/OpenBBTerminal/", command=None
):
    """Opens the documentation page based on your current location within the terminal. Make exceptions for menus
    that are considered 'common' by adjusting the path accordingly."""
    if "ta" in path:
        path = "terminal/common/ta/"
    elif "ba" in path:
        path = "terminal/common/ba/"
    elif "qa" in path:
        path = "terminal/common/qa/"
    elif "keys" in path:
        path = "#accessing-other-sources-of-data-via-api-keys"
        command = ""
    elif "settings" in path or "featflags" in path or "sources" in path:
        path = "#customizing-the-terminal"
        command = ""
    else:
        path = f"terminal/{path}"

    if command:
        if command in ["ta", "ba", "qa"]:
            path = "terminal/common/"
        elif "keys" == command:
            path = "#accessing-other-sources-of-data-via-api-keys"
            command = ""
        elif "exe" == command:
            path = "/terminal/scripts/"
            command = ""
        elif command in ["settings", "featflags", "sources"]:
            path = "#customizing-the-terminal"
            command = ""

        path += command

    full_url = f"{url}{path}".replace("//", "/")

    webbrowser.open(full_url)


def hide_splashscreen():
    """Hide the splashscreen on Windows bundles.

    `pyi_splash` is a PyInstaller "fake-package" that's used to communicate
    with the splashscreen on Windows.
    Sending the `close` signal to the splash screen is required.
    The splash screen remains open until this function is called or the Python
    program is terminated.
    """
    try:
        import pyi_splash  # type: ignore  # pylint: disable=import-outside-toplevel

        pyi_splash.update_text("Terminal Loaded!")
        pyi_splash.close()
    except Exception as e:
        logger.info(e)


def is_packaged_application() -> bool:
    """Tell whether or not it is a packaged version (Windows or Mac installer).


    Returns:
        bool: If the application is packaged
    """

    return LOGGING_APP_NAME == "gst_packaged"


def bootup():
    if sys.platform == "win32":
        # Enable VT100 Escape Sequence for WINDOWS 10 Ver. 1607
        os.system("")  # nosec
        # Hide splashscreen loader of the packaged app
        if is_packaged_application():
            hide_splashscreen()

    try:
        if os.name == "nt":
            # pylint: disable=E1101
            sys.stdin.reconfigure(encoding="utf-8")
            # pylint: disable=E1101
            sys.stdout.reconfigure(encoding="utf-8")
    except Exception as e:
        logger.exception("Exception: %s", str(e))
        console.print(e, "\n")


def check_for_updates() -> None:
    """Check if the latest version is running.

    Checks github for the latest release version and compares it to obbff.VERSION.
    """
    # The commit has was commented out because the terminal was crashing due to git import for multiple users
    # ({str(git.Repo('.').head.commit)[:7]})
    try:
        r = requests.get(
            "https://api.github.com/repos/openbb-finance/openbbterminal/releases/latest",
            timeout=1,
        )
    except Exception:
        r = None

    if r is not None and r.status_code == 200:
        release: str = r.json()["html_url"].split("/")[-1].replace("v", "")
        lastest_split = release.split(".")
        current = obbff.VERSION.replace("m", "").split(".")
        for i in range(3):
            if int(lastest_split[i]) > int(current[i]):
                console.print(
                    "[bold red]You are not using the latest version[/bold red]"
                )
                console.print(
                    "[yellow]Check for updates at https://openbb.co/products/terminal#get-started[/yellow]"
                )
                break
            if int(lastest_split[i]) < int(current[i]):
                console.print("[yellow]You are using an unreleased version[/yellow]")
            if release == obbff.VERSION.replace("m", ""):
                console.print("[green]You are using the latest version[/green]")
                break
    else:
        console.print(
            "[yellow]Unable to check for updates... "
            + "Check your internet connection and try again...[/yellow]"
        )
    console.print("\n")


def welcome_message():
    """Print the welcome message

    Prints first welcome message, help and a notification if updates are available.
    """
    console.print(f"\nWelcome to OpenBB Terminal v{obbff.VERSION}")

    if obbff.ENABLE_THOUGHTS_DAY:
        console.print("---------------------------------")
        try:
            thought.get_thought_of_the_day()
        except Exception as e:
            logger.exception("Exception: %s", str(e))
            console.print(e)


def reset(queue: List[str] = None):
    """Resets the terminal.  Allows for checking code or keys without quitting"""
    console.print("resetting...")
    logger.info("resetting")
    plt.close("all")

    if queue and len(queue) > 0:
        completed_process = subprocess.run(  # nosec
            f"{sys.executable} terminal.py {'/'.join(queue) if len(queue) > 0 else ''}",
            shell=True,
            check=False,
        )
    else:
        completed_process = subprocess.run(  # nosec
            f"{sys.executable} terminal.py", shell=True, check=False
        )
    if completed_process.returncode != 0:
        console.print("Unfortunately, resetting wasn't possible!\n")

    return completed_process.returncode


@contextmanager
def suppress_stdout():
    with open(os.devnull, "w") as devnull:
        old_stdout = sys.stdout
        old_stderr = sys.stderr
        sys.stdout = devnull
        sys.stderr = devnull
        try:
            yield
        finally:
            sys.stdout = old_stdout
            sys.stderr = old_stderr


def is_reset(command: str) -> bool:
    """Test whether a command is a reset command

    Parameters
    ----------
    command : str
        The command to test

    Returns
    -------
    answer : bool
        Whether the command is a reset command
    """
    if "reset" in command:
        return True
    if command == "r":
        return True
    if command == "r\n":
        return True
    return False
