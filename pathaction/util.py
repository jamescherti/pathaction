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

import os
import select
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Any

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
        cwd_str = os.path.abspath(cwd) if cwd else str(Path.cwd())  # noqa: PTH100

        if not Path(cwd_str).exists():
            raise PathActionError(f"'{cwd_str}' does not exist")

        if not Path(cwd_str).is_dir():
            raise PathActionError(f"'{cwd_str}' is not a directory")

        cmd_path = cmd
        relative = False

        # Check if the command has a directory component to avoid
        # string-matching bugs
        if cmd != Path(cmd).name:
            cmd_path = os.path.normpath(str(Path(cwd_str) / cmd))
            relative = True

        if (
            Path(cmd_path).is_file()
            and (relative or Path(cmd_path).is_absolute())
            and os.access(cmd_path, os.X_OK)
        ):
            return cmd_path

        try:
            paths = os.environ["PATH"] if env_path is None else env_path
            paths_split = [p for p in paths.split(os.pathsep) if p]
        except KeyError:
            paths = ""
            paths_split = []

        if not relative and not Path(cmd_path).is_absolute():
            for path in paths_split:
                candidate_path = str(Path(path) / cmd)
                if Path(candidate_path).is_file() and os.access(
                    candidate_path, os.X_OK
                ):
                    return candidate_path

        raise PathActionError(
            f"the command '{cmd}' wasn't found in $PATH \"{paths}\" or in '{cwd_str}'."
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
        prefix = Util.color(Util.COLOR_HIGHLIGHT, prefix)
        result = f"{prefix}{colored_text}"
        print(result, file=file, **kwargs)
        return result

    @staticmethod
    def ask_question(
        question: str,
        answers: list,
        timeout: int = 0,
        hook_invalid_entry: Callable = lambda _: None,
        empty_stdin: bool = True,
    ) -> str:
        """Prompt a question and wait for specific answers."""
        # Empty stdin
        if empty_stdin:
            while (
                sys.stdin
                in select.select(
                    [sys.stdin],  # pragma: no cover
                    [],  # pragma: no cover
                    [],  # pragma: no cover
                    0,
                )[0]
            ):  # pragma: no cover
                line = sys.stdin.readline()  # pragma: no cover
                if not line:  # pragma: no cover
                    break  # pragma: no cover

        if timeout > 0:

            def alarm_handler(*args: Any) -> None:
                """Handle the SIGALRM signal."""
                raise TimeoutError  # pragma: no cover

            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(timeout)

        try:
            while True:
                try:
                    Util.pcolor(
                        Util.COLOR_QUESTION,
                        "\n" + question,
                        end="",
                        file=sys.stdout,
                        flush=True,
                    )
                    answer = input()  # nosec: B322
                except (EOFError, KeyboardInterrupt):  # pragma: no cover
                    # Ignore EOF (CTRL-D) and SIGINT (CTRL-C)
                    answer = ""  # pragma: no cover

                answer = answer.strip()

                if answer in answers:
                    return answer

                answer = ""  # pragma: no cover
                hook_invalid_entry(answer)
        finally:
            if timeout > 0:
                signal.alarm(0)  # cancel the alarm

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
        if Path(path).is_file():
            with Path(path).open("rb") as fhandler:
                line = fhandler.readline().lstrip()
                if line[0:2] == b"#!":
                    return line[2:].rstrip().decode(errors="ignore")

        raise PathActionError(f"there is no shebang in the file '{path}'")

    @staticmethod
    def home_to_tilde(path: str) -> str:
        """Convert paths starting with user home directory into '~/path'."""
        home = str(Path("~").expanduser())
        if home.endswith(os.sep):
            home = home[:-1]

        if path == home:
            return "~"
        if path.startswith(home + os.sep):
            return f"~{os.sep}{path[len(home) + len(os.sep) :]}"
        return path
