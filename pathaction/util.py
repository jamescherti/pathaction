#!/usr/bin/env python
#
# Copyright (C) 2021-2024 James Cherti
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
"""Useful methods that PathAction uses."""

import os
import select
import signal
import sys
from collections.abc import Callable
from pathlib import Path
from typing import Union

from colorama import Fore, Style

from .exceptions import PathActionError


class Util:
    """Useful methods."""

    IS_A_TTY = ((hasattr(sys.stdout, 'isatty') and sys.stdout.isatty()) and
                (("TERM" not in os.environ) or
                 ("TERM" in os.environ and os.environ["TERM"] != "dumb")))
    COLOR_TEXT = Fore.WHITE
    COLOR_HIGHLIGHT = Fore.GREEN
    COLOR_ERROR = Fore.RED
    COLOR_SUCCESS = Fore.GREEN
    COLOR_QUESTION = Fore.YELLOW

    @staticmethod
    def which(cmd: str,
              cwd: Union[str, Path, None] = None,
              env_path: Union[str, None] = None) -> Path:
        """Return the path which conforms to the given mode on the PATH."""
        if cwd:
            cwd = Path(cwd).absolute()
        else:
            cwd = Path.cwd()

        if not cwd.exists():
            raise PathActionError(f"'{cwd}' does not exist")

        if not cwd.is_dir():
            raise PathActionError(f"'{cwd}' is not a directory")

        cmd_path = Path(cmd)
        relative = False
        if cmd.startswith(f"..{os.path.sep}") \
                or cmd.startswith(f".{os.path.sep}"):
            cmd_path = cwd.joinpath(cmd_path)
            relative = True

        if cmd_path.is_file() and (relative or cmd_path.is_absolute()) \
                and os.access(cmd_path, os.X_OK):
            return cmd_path

        try:
            paths = env_path if env_path else os.environ["PATH"]
            paths_split = paths.split(os.pathsep)
        except KeyError:
            paths = ""
            paths_split = []

        for path in paths_split:
            cmd_path = Path(path).joinpath(cmd)
            if os.path.isfile(cmd_path) and os.access(cmd_path, os.X_OK):
                return cmd_path

        raise PathActionError(f"the command '{cmd}' wasn't found "
                              f"in $PATH \"{paths}\" "
                              f"or in '{cwd}'.")

    @staticmethod
    def color(color: str, string: str = "") -> str:
        """Return a colored text."""
        color_reset: Union[int, str] = Style.RESET_ALL
        if not Util.IS_A_TTY:
            color = ""
            color_reset = ""
        return f"{color}{string}{color_reset}"

    @staticmethod
    def pcolor(color: str, string: str = "", prefix: str = "",
               file=sys.stderr, **kwargs) -> str:
        """Print a colored text."""
        colored_text = Util.color(color, string)
        prefix = Util.color(Util.COLOR_HIGHLIGHT, prefix)
        result = f"{prefix}{colored_text}"
        print(result, file=file, **kwargs)
        return result

    @staticmethod
    def ask_question(question: str,
                     answers: list,
                     timeout: int = 0,
                     hook_invalid_entry: Callable = lambda _: None,
                     empty_stdin: bool = True) -> str:
        """Ask a question."""
        # Empty stdin
        if empty_stdin:
            while sys.stdin in select.select([sys.stdin],  # pragma: no cover
                                             [],  # pragma: no cover
                                             [],  # pragma: no cover
                                             0)[0]:  # pragma: no cover
                line = sys.stdin.readline()  # pragma: no cover
                if not line:  # pragma: no cover
                    break  # pragma: no cover

        if timeout > 0:
            def alarm_handler(*args):
                """SIGALRM handler."""
                raise TimeoutError  # pragma: no cover

            signal.signal(signal.SIGALRM, alarm_handler)
            signal.alarm(timeout)

        try:
            while True:
                try:
                    Util.pcolor(Util.COLOR_QUESTION,
                                "\n" + question,
                                end="", file=sys.stdout, flush=True)
                    answer = input()    # nosec: B322
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
    def file_ends_with(path_prefix: str, path_suffixes: list) -> list:
        """Return paths that that exist and end with path_suffixes.

        :path_prefix: path to the file.
        :path_suffixes: list of suffixes (e.g. extensions).

        """
        result: list = []
        for cur_path_suffix in path_suffixes:
            cur_file = f"{path_prefix}{cur_path_suffix}"
            if os.path.isfile(cur_file) and cur_file not in result:
                result.append(cur_file)
        return result

    @staticmethod
    def read_shebang(path: str) -> str:
        """Return the shebang of the source code.

        None is returned if the shebang cannot be found.
        """
        if os.path.isfile(path):
            with open(path, "rb") as fhandler:
                line = fhandler.readline().lstrip()
                if line[0:2] == b"#!":
                    return line[2:].rstrip().decode(errors="ignore")

        raise PathActionError(f"there is no shebang in the file '{path}'")

    @staticmethod
    def home_to_tilde(path: str) -> str:
        """Convert paths that start with '/home/*' to '~/*'."""
        home = os.path.expanduser(f"~{os.sep}")
        if f"{path}{os.sep}".startswith(home):
            path = f"~{os.sep}{path[len(home):]}"
        return path
