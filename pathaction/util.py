#!/usr/bin/env python3
#
# Copyright (C) 2021-2026 James Cherti
# URL: https://github.com/jamescherti/pathaction
#
# This program is free software: you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation, either version 3 of the License, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE. See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program. If not, see <https://www.gnu.org/licenses/>.
#
"""Provide useful methods that PathAction uses."""

from __future__ import annotations

import asyncio
import os
import shutil
import sys
import time
from collections.abc import Callable
from pathlib import Path
from typing import Any

from prompt_toolkit import PromptSession
from prompt_toolkit.formatted_text import ANSI
from prompt_toolkit.input.base import PipeInput
from prompt_toolkit.input.typeahead import clear_typeahead

try:
    from colorama import Fore, Style
except ImportError:

    class Fore:  # type: ignore
        """Provide fallback text colors."""

        WHITE: str = ""
        GREEN: str = ""
        RED: str = ""
        YELLOW: str = ""

    class Style:  # type: ignore
        """Provide fallback text styles."""

        RESET_ALL: str = ""


from .exceptions import PathActionError


class Util:
    """Provide helper methods for CLI formatting and execution."""

    IS_A_TTY = (hasattr(sys.stdout, "isatty") and sys.stdout.isatty()) and (
        ("TERM" not in os.environ)
        or ("TERM" in os.environ and os.environ["TERM"] != "dumb")
    )
    COLOR_TEXT = Fore.WHITE
    COLOR_HIGHLIGHT = Fore.GREEN
    COLOR_ERROR = Fore.RED
    COLOR_SUCCESS = Fore.GREEN
    COLOR_QUESTION = Fore.YELLOW

    @staticmethod
    def error(message: str) -> None:
        """Print an error message directly to sys.stderr."""
        print(Path(sys.argv[0]).name + ": Error: " + message, file=sys.stderr)

    @staticmethod
    def which(cmd: str, cwd: str | None = None, env_path: str | None = None) -> str:
        """Return the path which conforms to the given mode on the PATH."""
        cwd_path = Path(cwd).absolute() if cwd else Path.cwd()

        if not cwd_path.exists():
            raise PathActionError(f"'{cwd_path}' does not exist")

        if not cwd_path.is_dir():
            raise PathActionError(f"'{cwd_path}' is not a directory")

        cmd_path = Path(cmd)
        relative = cmd != cmd_path.name

        resolved: str | None = None

        if relative or cmd_path.is_absolute():
            target = cmd_path if cmd_path.is_absolute() else cwd_path / cmd
            resolved = shutil.which(str(target))
        else:
            paths = os.environ.get("PATH", "") if env_path is None else env_path
            resolved = shutil.which(cmd, path=paths)

        if resolved:
            return resolved

        paths_str = os.environ.get("PATH", "") if env_path is None else env_path
        raise PathActionError(
            f"the command '{cmd}' wasn't found in $PATH \"{paths_str}\" "
            f"or in '{cwd_path}'."
        )

    @staticmethod
    def color(color: str, string: str = "") -> str:
        """Return text formatted with colorama styles."""
        color_reset: int | str = Style.RESET_ALL
        if not Util.IS_A_TTY:
            color = ""
            color_reset = ""
        return f"{color}{string}{color_reset}"

    @staticmethod
    def pcolor(
        color: str,
        string: str = "",
        prefix: str = "",
        file: Any = sys.stderr,
        **kwargs: Any,
    ) -> str:
        """Print a colored string with an optional prefix."""
        colored_text = Util.color(color, string)
        prefix_str = Util.color(Util.COLOR_HIGHLIGHT, prefix)
        result = f"{prefix_str}{colored_text}"
        print(result, file=file, **kwargs)
        return result

    @staticmethod
    def ask_question(
        question: str,
        answers: list[str],
        timeout: int = 0,
        hook_invalid_entry: Callable[[str], None] = lambda _: None,
        empty_stdin: bool = True,
    ) -> str:
        """Prompt a question and wait for specific answers."""
        session: PromptSession[str] = PromptSession()
        should_empty_stdin = empty_stdin
        deadline = time.monotonic() + timeout if timeout > 0 else 0.0
        timer_handle: asyncio.TimerHandle | None = None

        def alarm_handler() -> None:
            """Handle the timeout signal."""
            if session.app.is_running:  # pragma: no cover
                session.app.exit(exception=TimeoutError())  # pragma: no cover

        def pre_run() -> None:
            nonlocal should_empty_stdin, timer_handle
            # Empty stdin
            if should_empty_stdin:
                should_empty_stdin = False
                if not isinstance(session.app.input, PipeInput):  # pragma: no cover
                    while session.app.input.read_keys():  # pragma: no cover
                        pass  # pragma: no cover
                    session.app.input.flush_keys()  # pragma: no cover
                clear_typeahead(session.app.input)

            if timeout > 0:
                remaining = max(0.0, deadline - time.monotonic())
                loop = asyncio.get_running_loop()
                timer_handle = loop.call_later(remaining, alarm_handler)

        while True:
            try:
                if timeout > 0 and time.monotonic() >= deadline:
                    raise TimeoutError  # pragma: no cover

                prompt_message = ANSI(Util.color(Util.COLOR_QUESTION, "\n" + question))
                answer = session.prompt(prompt_message, pre_run=pre_run)
            except (EOFError, KeyboardInterrupt):  # pragma: no cover
                # Ignore EOF (CTRL-D) and SIGINT (CTRL-C)
                answer = ""  # pragma: no cover
            finally:
                if timer_handle is not None:
                    timer_handle.cancel()  # cancel the alarm
                    timer_handle = None

            answer = answer.strip()

            if answer in answers:
                return answer

            answer = ""  # pragma: no cover
            hook_invalid_entry(answer)

    @staticmethod
    def file_ends_with(path_prefix: str, path_suffixes: list[str]) -> list[str]:
        """Return valid system paths that end with given suffixes.

        Args:
            path_prefix: Base path prefix.
            path_suffixes: List of file suffixes to attempt appending.
        """
        result: list[str] = []
        for cur_path_suffix in path_suffixes:
            cur_file = f"{path_prefix}{cur_path_suffix}"
            if Path(cur_file).is_file() and cur_file not in result:
                result.append(cur_file)
        return result

    @staticmethod
    def read_shebang(path: str) -> str:
        """Return the shebang string of the parsed source code.

        Raises PathActionError if the shebang cannot be found.
        """
        file_path = Path(path)
        if file_path.is_file():
            with file_path.open("rb") as fhandler:
                line = fhandler.readline().lstrip()
                if line[0:2] == b"#!":
                    return line[2:].rstrip().decode(errors="ignore")

        raise PathActionError(f"there is no shebang in the file '{path}'")

    @staticmethod
    def home_to_tilde(path: str) -> str:
        """Convert paths starting with user home directory into '~/path'."""
        target_path = Path(path)
        home_path = Path.home()
        if target_path == home_path:
            return "~"
        if target_path.is_relative_to(home_path):
            return f"~{os.sep}{target_path.relative_to(home_path)}"
        return path
