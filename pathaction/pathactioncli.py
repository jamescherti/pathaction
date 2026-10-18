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
"""Represent the command-line interface of pathaction."""

from __future__ import annotations

import argparse
import contextlib
import os
import subprocess  # nosec B404
import sys
import traceback
from pathlib import Path
from pprint import pprint
from typing import Any

try:
    import colorama

    HAS_COLORAMA = True
except ImportError:
    HAS_COLORAMA = False

try:
    from setproctitle import setproctitle

    SETPROCTITLE = True
except ImportError:
    SETPROCTITLE = False

import jinja2
import schema

from .allowed_paths import AllowedPaths
from .exceptions import PathActionError
from .pathactioncfg import ActionCommand, PathActionCfg
from .util import Util

CFG_ALLOWED_DIRS = str(Path("~/.config/pathaction/permissions.yml").expanduser())


class PathActionCli:
    """Provide the Command line interface logic."""

    def ask_user_press_enter(self) -> None:
        """Ask the user to press enter to exit."""
        if self.args.confirm_after:
            print()
            input("Press enter...")
            sys.exit(1)

    def __init__(
        self,
        require_tty: bool = False,
        limit_loop: int = -1,
        limit_load_cfg: int = -1,
        allowed_dirs: Any = None,
    ) -> None:
        """Parse the arguments and initialize the CLI."""
        # Variables
        self.confirm_before_disabled = False
        self.tag: Any = None
        self.errno = 0
        self.limit_loop = limit_loop
        self.limit_load_cfg = limit_load_cfg
        self.pathaction_cfg: Any = None

        # Init
        if HAS_COLORAMA:
            colorama.init()

        # Optional: setproctitle
        if SETPROCTITLE:
            setproctitle(Path(sys.argv[0]).name)

        # Load PathAction cfg
        self.args: argparse.Namespace = self.parse_args()

        # Checks
        if require_tty and not sys.stdin.isatty():
            Util.error("stdin is not a tty.")
            self.errno = 1
            self.ask_user_press_enter()
            sys.exit(1)

        # Allow directory
        allowed_dirs = self._init_allowed_dirs(allowed_dirs)
        self._handle_dir_permissions(allowed_dirs)

        if not self.args.list_filenames:
            Util.error("the following arguments are required: N")
            self.errno = 1
            sys.exit(1)

        # Prepare
        list_pathaction_cfg = self._prepare_pathaction_cfgs(allowed_dirs)

        # Execute
        first = True
        for pathaction_cfg in list_pathaction_cfg:
            self.pathaction_cfg = pathaction_cfg

            self.errno = self.main()
            if self.errno != 0:
                break

            if first:
                first = False
            else:
                print()

        if self.errno:
            self.ask_user_press_enter()
        sys.exit(self.errno)  # pragma: no cover

    def _init_allowed_dirs(self, allowed_dirs: Any) -> Any:
        """Initialize the allowed directories configuration."""
        if not allowed_dirs:
            allowed_dirs = AllowedPaths()
            with contextlib.suppress(FileNotFoundError):
                allowed_dirs.load_from_yaml(CFG_ALLOWED_DIRS)
        return allowed_dirs

    def _handle_dir_permissions(self, allowed_dirs: Any) -> None:
        """Process directory permission arguments."""
        if self.args.list_allowed_dirs:
            for allowed_dir in allowed_dirs:
                print(allowed_dir)
            sys.exit(0)

        if self.args.disallow_dir:
            target_dir = Path(self.args.disallow_dir).resolve()
            if target_dir not in allowed_dirs.get_all():
                print(
                    f"Error: The directory '{target_dir}' is not part "
                    "of the allowed ones and cannot be disallowed for this "
                    "reason."
                )
                sys.exit(1)
            allowed_dirs.remove(target_dir)
            allowed_dirs.save_to_yaml(CFG_ALLOWED_DIRS)
            print(f"Removed from allowed directories: {target_dir}")
            sys.exit(0)

    def _prepare_pathaction_cfgs(self, allowed_dirs: Any) -> list[Any]:
        """Parse configuration files and validate directories."""
        list_pathaction_cfg = []
        for filename in self.args.list_filenames:
            try:
                pathaction_cfg = PathActionCfg(filename)
                source_code = os.path.abspath(pathaction_cfg.source_code)  # noqa: PTH100
                resolved_source_code = Path(source_code).resolve()

                if self.args.allow_dir:
                    Path(CFG_ALLOWED_DIRS).parent.mkdir(parents=True, exist_ok=True)
                    if not Path(source_code).is_dir():
                        Util.error(
                            f"The path you provided is not a directory: {source_code}"
                        )
                        self.errno = 1
                        self.ask_user_press_enter()
                        sys.exit(1)

                    allowed_dirs.add(resolved_source_code, permanent=True)
                    allowed_dirs.save_to_yaml(CFG_ALLOWED_DIRS)
                    print(
                        "The directory has been permanently added to the "
                        f"allow list: {resolved_source_code}"
                    )
                    sys.exit(0)

                if not allowed_dirs.is_allowed(resolved_source_code):
                    Util.error(
                        "The following directory is not "
                        f"allowed: '{Path(resolved_source_code).parent}'\n"
                        "You can allow the directory or one of its "
                        "parent directories with the command-line "
                        "option '--allow-dir'."
                    )
                    self.errno = 1
                    self.ask_user_press_enter()
                    sys.exit(1)
            except PathActionError as err:
                Util.error(f"{err}.")
                self.errno = 1
                self.ask_user_press_enter()
                sys.exit(1)

            try:
                pathaction_cfg.load_all_cfg(limit=self.limit_load_cfg)
            except (
                PathActionError,
                schema.SchemaError,
                jinja2.exceptions.TemplateSyntaxError,
                jinja2.exceptions.UndefinedError,
            ) as err:
                Util.pcolor(Util.COLOR_ERROR)
                Util.pcolor(Util.COLOR_ERROR, f"Error: {err}")
                self.errno = 1
                self.ask_user_press_enter()
                sys.exit(1)

            if self.args.list:
                for item in reversed(pathaction_cfg.loaded_yaml_path):
                    print(item)
                continue

            list_pathaction_cfg.append(pathaction_cfg)

        return list_pathaction_cfg

    def main(self) -> int:
        """Run the main CLI execution loop."""
        limit_loop = self.limit_loop
        ask_execute_again = False
        while True:
            errno = 0
            if limit_loop == 0:
                break

            limit_loop -= 1

            try:
                if ask_execute_again and not self.ask_execute_again():
                    break

                self.load_cfg_files()
                errno = self.run_from_yaml()
            except (
                PathActionError,
                schema.SchemaError,
                jinja2.exceptions.TemplateSyntaxError,
                jinja2.exceptions.UndefinedError,
                subprocess.TimeoutExpired,
            ) as err:
                Util.pcolor(Util.COLOR_ERROR)
                Util.pcolor(Util.COLOR_ERROR, f"Error: {err}")
                errno = 1
            except KeyboardInterrupt:
                if self.pathaction_cfg.verbose:
                    Util.pcolor(Util.COLOR_ERROR)
                    Util.pcolor(
                        Util.COLOR_ERROR,
                        f"'{sys.argv[0]}' terminated because of a SIGINT.",
                    )
                errno = 1
            except Exception:  # pylint: disable=broad-except
                Util.pcolor(Util.COLOR_ERROR)
                Util.pcolor(Util.COLOR_ERROR, traceback.format_exc())
                errno = 1

            ask_execute_again = True
            if not self.pathaction_cfg:
                break

            if not self.args.confirm_after:
                break

        return errno

    def parse_args(self) -> argparse.Namespace:
        """Parse the command line arguments."""
        default_action = "main"

        description = Path(sys.argv[0]).name
        parser = argparse.ArgumentParser(
            description=description, usage="%(prog)s [--option] filename"
        )

        parser.add_argument(
            "list_filenames",
            type=str,
            metavar="N",
            nargs="*",
            help="Path to the files.",
        )

        parser.add_argument(
            "-t",
            "--tag",
            default=default_action,
            type=str,
            help=(
                "Execute the action associated with this tag "
                f"(default: {default_action})."
            ),
        )

        parser.add_argument(
            "-b",
            "--confirm-before",
            action="store_true",
            default=False,
            help="Confirm before executing the action.",
        )

        parser.add_argument(
            "-a",
            "--confirm-after",
            action="store_true",
            default=False,
            help="Ask the user to run the action again.",
        )

        parser.add_argument(
            "-l",
            "--list",
            action="store_true",
            default=False,
            help="List the configuration files that have been found.",
        )

        parser.add_argument(
            "-d",
            "--allow-dir",
            action="store_true",
            default=False,
            help="Allow pathaction to be executed in the provided "
            "directory and its subdirectories permanently.",
        )

        parser.add_argument(
            "--disallow-dir",
            type=str,
            metavar="DIR",
            help="Disallow pathaction from being executed in the provided directory.",
        )

        parser.add_argument(
            "--list-allowed-dirs",
            action="store_true",
            default=False,
            help="List permanently allowed directories.",
        )

        return parser.parse_args(sys.argv[1:])

    def load_cfg_files(self) -> None:
        """Load all valid configuration files."""
        limit_load_cfg = self.limit_load_cfg
        self.pathaction_cfg.load_all_cfg(limit=limit_load_cfg)

        source_code = Util.home_to_tilde(
            os.path.abspath(self.pathaction_cfg.source_code)  # noqa: PTH100
        )

        if self.pathaction_cfg.verbose:
            Util.pcolor(
                Util.COLOR_TEXT, f"source code: {source_code}", prefix="[INFO] "
            )

        if self.pathaction_cfg.debug:
            Util.pcolor(
                Util.COLOR_TEXT, "Rule set files that were loaded:", prefix="[INFO] "
            )

        for yaml_path in self.pathaction_cfg.loaded_yaml_path:
            if self.pathaction_cfg.debug:
                print(f"  - {yaml_path}")

        if not self.pathaction_cfg.loaded_yaml_path:
            list_qa_files = ", ".join([".pathaction.yaml", ".pathaction.yml"])
            err_msg = (
                "none of the pathaction YAML files were found, "
                f"neither the relative ones {list_qa_files} "
                "(located at the parent "
                f"directories of the source code: {source_code})"
            )
            raise PathActionError(err_msg)

        # Return action
        action = self.pathaction_cfg.find_command(self.args.tag)
        if not action:
            list_qa_files = ", ".join(self.pathaction_cfg.loaded_yaml_path)
            err_msg = (
                f"the file '{source_code}' does not match any pattern that "
                f"is defined in one of the rule set files {list_qa_files}."
            )
            raise PathActionError(str(err_msg))

        self.show_action_infos(action)
        self.tag = action

    def ask_execute_again(self) -> bool:
        """Ask the user if they want to execute the command again."""
        if not self.pathaction_cfg:
            return False

        if not self.args.confirm_after:
            return False

        ca_timeout = self.pathaction_cfg.cfg["options"]["confirm_after_timeout"]
        ca_timeout = max(ca_timeout, 0)

        def hook_invalid_entry(_: Any) -> None:
            self.load_cfg_files()

        while True:
            question = "Run again?"
            if ca_timeout > 0:
                question += f" (timeout: {ca_timeout} sec)"
                question += " [a=again, n=no, t=no_timeout] "
                answers = ["a", "n", "t"]
            else:
                question += " [a=again, n=no] "
                answers = ["a", "n"]

            try:
                answer = Util.ask_question(
                    question=question,
                    answers=answers,
                    timeout=ca_timeout,
                    hook_invalid_entry=hook_invalid_entry,
                )
                if answer == "a":
                    return True

                if answer == "t":
                    Util.pcolor(Util.COLOR_TEXT, "Timeout disabled.")
                    ca_timeout = 0
                    continue

                break
            except TimeoutError:
                Util.pcolor(Util.COLOR_TEXT, "Timeout.")
                return False  # exit

        return False  # exit

    def show_action_infos(self, action: ActionCommand) -> None:
        """Print and format the loaded action information."""
        if self.pathaction_cfg.debug:
            Util.pcolor(
                Util.COLOR_TEXT,
                "Merged configurations from Yaml config files:",
                prefix="[INFO] ",
            )
            pprint(self.pathaction_cfg.cfg)

            if action:
                Util.pcolor(Util.COLOR_TEXT, "Command:", prefix="[ACTION] ")
                pprint(action)

        if self.pathaction_cfg.verbose:
            Util.pcolor(
                Util.COLOR_TEXT,
                f"'{self.args.tag}' loaded from:",
                prefix="[INFO] ",
            )
            for item in self.pathaction_cfg.loaded_yaml_path:
                tilde_item = Util.home_to_tilde(item)
                Util.pcolor(Util.COLOR_TEXT, f"  {tilde_item}")

            # Shell
            if action.shell:
                Util.pcolor(
                    Util.COLOR_TEXT,
                    self.pathaction_cfg.cfg["options"]["shell_path"],
                    prefix="[SHELL] ",
                )

        Util.pcolor(
            Util.COLOR_TEXT, Util.home_to_tilde(action.cwd), prefix="[WORKING DIR] "
        )

        if "command" in action:
            Util.pcolor(
                Util.COLOR_TEXT,
                subprocess.list2cmdline(action.command)
                if isinstance(action.command, list)
                else str(action.command),
                prefix="[COMMAND] ",
            )
        elif "list_commands" in action:
            Util.pcolor(Util.COLOR_TEXT, "List of commands:", prefix="[COMMANDS] ")
            for cmd in action.list_commands:
                Util.pcolor(
                    Util.COLOR_TEXT,
                    "  "
                    + (
                        subprocess.list2cmdline(cmd)
                        if isinstance(cmd, list)
                        else str(cmd)
                    ),
                )

        if action.comment:
            Util.pcolor(Util.COLOR_TEXT, action.comment, prefix="[COMMENT] ")

    def run_from_yaml(self) -> int:
        """Run the parsed command configuration."""
        if not self._confirm_execution():
            return 1

        self._print_run_debug()

        timeout = -1
        with contextlib.suppress(KeyError):
            timeout = self.pathaction_cfg.cfg["options"]["timeout"]

        # String command: use the shell
        (cmd, errno) = self.tag.run(  # type: ignore
            shell_path=self.pathaction_cfg.cfg["options"]["shell_path"],
            timeout=timeout,
            debug=self.pathaction_cfg.debug,
        )

        self._print_execution_result(cmd, errno)
        return errno  # type: ignore

    def _confirm_execution(self) -> bool:
        """Ask the user to confirm execution if required."""
        if self.args.confirm_before and not self.confirm_before_disabled:
            question = "Do you want to execute the command? [y,n] "
            answer = Util.ask_question(question=question, answers=["y", "n"])
            if answer == "y":
                self.confirm_before_disabled = True
                return True
            return False
        Util.pcolor(Util.COLOR_TEXT, "")
        return True

    def _print_run_debug(self) -> None:
        """Print debug information for the run command."""
        if not self.pathaction_cfg.debug:
            return

        Util.pcolor(Util.COLOR_TEXT, "Run command arguments:", prefix="[RUN COMMAND] ")

        if "command" in self.tag:  # type: ignore
            Util.pcolor(Util.COLOR_TEXT, "  - command: " + str(self.tag["command"]))  # type: ignore
        if "list_commands" in self.tag:  # type: ignore
            Util.pcolor(
                Util.COLOR_TEXT,
                "  - list commands: " + str(self.tag["list_commands"]),
            )  # type: ignore
        Util.pcolor(Util.COLOR_TEXT, "  - shell: " + str(self.tag.shell))  # type: ignore
        Util.pcolor(Util.COLOR_TEXT, "  - cwd: " + str(self.tag.cwd))  # type: ignore

    def _print_execution_result(self, cmd: Any, errno: int) -> None:
        """Print the result of the executed command."""
        if errno != 0:
            status = "[FAILURE] "
            status_color = Util.COLOR_ERROR
            if cmd:
                message = status + (
                    subprocess.list2cmdline(cmd) if isinstance(cmd, list) else cmd
                )
                Util.pcolor(status_color, message)
            Util.pcolor(status_color, f"[EXIT-CODE] command returned {errno}")
            return

        status_color = Util.COLOR_SUCCESS
        Util.pcolor(status_color, "")
        if not self.pathaction_cfg.debug:
            Util.pcolor(
                status_color, "All commands were successful.", prefix="[SUCCESS] "
            )
        else:
            Util.pcolor(
                status_color, "All commands were successful:", prefix="[SUCCESS] "
            )

            if self.tag and "command" in self.tag:
                string = (
                    subprocess.list2cmdline(self.tag.command)
                    if isinstance(self.tag.command, list)
                    else str(self.tag.command)
                )
                Util.pcolor(status_color, f"  {string}")

            if self.tag and "list_commands" in self.tag:
                for tag_cmd in self.tag.list_commands:
                    Util.pcolor(
                        status_color,
                        "  "
                        + (
                            subprocess.list2cmdline(tag_cmd)
                            if isinstance(tag_cmd, list)
                            else str(tag_cmd)
                        ),
                    )
