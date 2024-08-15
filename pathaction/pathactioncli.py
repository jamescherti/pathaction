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
"""The command-line interface of pathaction."""

import argparse
import os
import subprocess  # nosec B404
import sys
import traceback
from pathlib import Path
from pprint import pprint
from typing import Any

import colorama
import jinja2
import schema
from setproctitle import setproctitle

from .allowed_paths import AllowedPaths
from .exceptions import PathActionError
from .pathactioncfg import ActionCommand, PathActionCfg
from .util import Util

CFG_ALLOWED_DIRS = Path("~/.config/pathaction/permissions.yml") \
    .expanduser()


class PathActionCli:
    """Command line interface."""

    def ask_user_press_enter(self):
        if self.args.confirm_after:
            print()
            input("Press enter...")
            sys.exit(1)

    def __init__(self,
                 require_tty=False,
                 limit_loop: int = -1,
                 limit_load_cfg: int = -1,
                 allowed_dirs=None):
        """Parse the arguments and init the command line interface."""
        # Variables
        self.confirm_before_disabled = False
        self.tag = None
        self.args: Any = None
        self.errno = 0
        self.limit_loop = limit_loop
        self.limit_load_cfg = limit_load_cfg

        # Init
        colorama.init()
        setproctitle(Path(sys.argv[0]).name)  # type: ignore

        # Load PathAction cfg
        self.parse_args()

        # Checks
        if require_tty and not sys.stdin.isatty():
            print("Error: stdin is not a tty.", file=sys.stderr)
            self.errno = 1
            self.ask_user_press_enter()
            sys.exit(1)

        # Allow directory
        if not allowed_dirs:
            allowed_dirs = AllowedPaths()
            try:
                allowed_dirs.load_from_yaml(CFG_ALLOWED_DIRS)
            except FileNotFoundError:
                pass

        # Prepare
        list_pathaction_cfg = []
        first = False
        for filename in self.args.list_filenames:
            try:
                pathaction_cfg = PathActionCfg(filename)

                source_code = Path(pathaction_cfg.source_code).resolve()

                if self.args.allow_dir:
                    CFG_ALLOWED_DIRS.parent.mkdir(parents=True, exist_ok=True)
                    if not source_code.is_dir():
                        print(f"Error: The path you provided is not a "
                              f"directory: {source_code}", file=sys.stderr)
                        self.errno = 1
                        self.ask_user_press_enter()
                        sys.exit(1)

                    allowed_dirs.add(source_code, permanent=True)
                    allowed_dirs.save_to_yaml(CFG_ALLOWED_DIRS)
                    print(
                        "The directory has been permanently added to the "
                        f"allow list: {source_code}"
                    )
                    sys.exit(0)

                if not allowed_dirs.is_allowed(source_code):
                    print("Error: The following directory is not "
                          f"allowed: '{source_code.parent}'", file=sys.stderr)
                    print("You can allow the directory or one of its "
                          "parent directories with the command-line "
                          "option '--allow-dir'.", file=sys.stderr)
                    self.errno = 1
                    self.ask_user_press_enter()
                    sys.exit(1)
            except PathActionError as err:
                print(f"Error: {err}.", file=sys.stderr)
                self.errno = 1
                self.ask_user_press_enter()
                sys.exit(1)

            try:
                pathaction_cfg.load_all_cfg(limit=limit_load_cfg)
            except (PathActionError,
                    schema.SchemaError,
                    jinja2.exceptions.TemplateSyntaxError,
                    jinja2.exceptions.UndefinedError) as err:
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

        # Execute
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

    def main(self):
        """Main loop."""
        limit_loop = self.limit_loop

        ask_execute_again = False
        while True:
            errno = 0
            if limit_loop == 0:
                break

            limit_loop -= 1

            try:
                if ask_execute_again:
                    if not self.ask_execute_again():
                        break

                self.load_cfg_files()
                errno = self.run_from_yaml()
            except (PathActionError,
                    schema.SchemaError,
                    jinja2.exceptions.TemplateSyntaxError,
                    jinja2.exceptions.UndefinedError,
                    subprocess.TimeoutExpired) as err:
                Util.pcolor(Util.COLOR_ERROR)
                Util.pcolor(Util.COLOR_ERROR, f"Error: {err}")
                errno = 1
            except KeyboardInterrupt:
                if self.pathaction_cfg.verbose:
                    Util.pcolor(Util.COLOR_ERROR)
                    Util.pcolor(
                        Util.COLOR_ERROR,
                        f"'{sys.argv[0]}' terminated because of a SIGINT."
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

    def parse_args(self):
        """Parse the command line arguments."""
        default_action = "main"

        description = os.path.basename(sys.argv[0])
        parser = argparse.ArgumentParser(description=description,
                                         usage="%(prog)s [--option] filename")
        parser.add_argument(
            "list_filenames",
            type=str,
            metavar="N",
            nargs="+",
            help="Path to the files."
        )

        parser.add_argument(
            "-t",
            "--tag",
            default=default_action,
            type=str,
            help=("Execute the action associated with this tag "
                  f"(default: {default_action}).")
        )

        parser.add_argument(
            "-b",
            "--confirm-before",
            action="store_true",
            default=False,
            help="Confirm before executing the action."
        )

        parser.add_argument(
            "-a",
            "--confirm-after",
            action="store_true",
            default=False,
            help="Ask the user to run the action again."
        )

        parser.add_argument(
            "-l",
            "--list",
            action="store_true",
            default=False,
            help="List the configuration files that have been found."
        )

        parser.add_argument(
            "-d",
            "--allow-dir",
            action="store_true",
            default=False,
            help="Allow pathaction to be executed in the provided "
            "directory and its subdirectories permanently."
        )

        self.args = parser.parse_args(sys.argv[1:])

    def load_cfg_files(self):
        """Load all cfg files."""
        limit_load_cfg = self.limit_load_cfg
        self.pathaction_cfg.load_all_cfg(limit=limit_load_cfg)

        source_code = Util.home_to_tilde(
            os.path.abspath(self.pathaction_cfg.source_code)
        )

        if self.pathaction_cfg.verbose:
            Util.pcolor(Util.COLOR_TEXT,
                        f"source code: {source_code}",
                        prefix="[INFO] ")

        if self.pathaction_cfg.debug:
            Util.pcolor(Util.COLOR_TEXT,
                        "Rule set files that were loaded:",
                        prefix="[INFO] ")

        for yaml_path in self.pathaction_cfg.loaded_yaml_path:
            if self.pathaction_cfg.debug:
                print(f"  - {yaml_path}")

        if not self.pathaction_cfg.loaded_yaml_path:
            list_qa_files = ", ".join(['.pathaction.yaml',
                                       '.pathaction.yml'])
            err_msg = ("none of the pathaction YAML files were found, "
                       f"neither the relative ones {list_qa_files} "
                       "(located at the parent "
                       f"directories of the source code: {source_code})")
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
        """Ask the user if he wants to execute the command again."""
        if not self.pathaction_cfg:
            return False

        if not self.args.confirm_after:
            return False

        ca_timeout = \
            self.pathaction_cfg.cfg["options"]["confirm_after_timeout"]
        ca_timeout = max(ca_timeout, 0)

        def hook_invalid_entry(_):
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
                    hook_invalid_entry=hook_invalid_entry
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

    def show_action_infos(self, action: ActionCommand):
        """Show action infos."""
        if self.pathaction_cfg.debug:
            Util.pcolor(Util.COLOR_TEXT,
                        "Merged configurations from Yaml config files:",
                        prefix="[INFO] ")
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
                item = Util.home_to_tilde(item)
                Util.pcolor(Util.COLOR_TEXT, f"  {item}")

            # Shell
            if action.shell:
                Util.pcolor(Util.COLOR_TEXT,
                            self.pathaction_cfg.cfg["options"]["shell_path"],
                            prefix="[SHELL] ")

        Util.pcolor(Util.COLOR_TEXT,
                    Util.home_to_tilde(action.cwd),
                    prefix="[WORKING DIR] ")

        if "command" in action:
            Util.pcolor(Util.COLOR_TEXT,
                        subprocess.list2cmdline(action.command)
                        if isinstance(action.command, list)
                        else str(action.command),
                        prefix="[COMMAND] ")
        elif "list_commands" in action:
            Util.pcolor(Util.COLOR_TEXT, "List of commands:",
                        prefix="[COMMANDS] ")
            for cmd in action.list_commands:
                Util.pcolor(
                    Util.COLOR_TEXT,
                    "  " + (subprocess.list2cmdline(cmd)
                            if isinstance(cmd, list) else str(cmd))
                )

        if action.comment:
            Util.pcolor(Util.COLOR_TEXT, action.comment, prefix="[COMMENT] ")

    def run_from_yaml(self) -> int:
        """Run the command from a Yaml."""
        # Run the command
        question = "Do you want to execute the command? [y,n] "
        if self.args.confirm_before and not self.confirm_before_disabled:
            answer = Util.ask_question(question=question, answers=["y", "n"])
            if answer == "y":
                self.confirm_before_disabled = True
            else:
                return 1
        else:
            Util.pcolor(Util.COLOR_TEXT, "")

        if self.pathaction_cfg.debug:
            Util.pcolor(Util.COLOR_TEXT, "Run command arguments:",
                        prefix="[RUN COMMAND] ")

            if "command" in self.tag:  # type: ignore
                Util.pcolor(Util.COLOR_TEXT, "  - command: " +
                            str(self.tag["command"]))  # type: ignore
            if "list_commands" in self.tag:  # type: ignore
                Util.pcolor(Util.COLOR_TEXT, "  - list commands: " +
                            str(self.tag["list_commands"]))  # type: ignore
            Util.pcolor(Util.COLOR_TEXT, "  - shell: " +
                        str(self.tag.shell))  # type: ignore
            Util.pcolor(Util.COLOR_TEXT, "  - cwd: " +
                        str(self.tag.cwd))  # type: ignore

        # Global timeout
        timeout = -1
        try:
            timeout = self.pathaction_cfg.cfg["options"]["timeout"]
        except KeyError:
            pass

        # String command: use the shell
        (cmd, errno) = self.tag.run(  # type: ignore
            shell_path=self.pathaction_cfg.cfg["options"]["shell_path"],
            timeout=timeout,
            debug=self.pathaction_cfg.debug,
        )

        # Show the result
        if errno != 0:
            status = "[FAILURE] "
            status_color = Util.COLOR_ERROR
            if cmd:
                message = (status +
                           (subprocess.list2cmdline(cmd)
                            if isinstance(cmd, list)
                            else cmd))
                Util.pcolor(status_color, message)

            Util.pcolor(status_color,
                        f"[EXIT-CODE] command returned {errno}")

        if errno == 0:
            status_color = Util.COLOR_SUCCESS
            Util.pcolor(status_color, "")
            if not self.pathaction_cfg.debug:
                Util.pcolor(status_color, "All commands were successful.",
                            prefix="[SUCCESS] ")
            else:
                Util.pcolor(status_color, "All commands were successful:",
                            prefix="[SUCCESS] ")

                if self.tag and "command" in self.tag:
                    string = subprocess.list2cmdline(self.tag.command) \
                        if isinstance(self.tag.command, list) \
                        else str(self.tag.command)
                    Util.pcolor(status_color, f"  {string}")

                if self.tag and "list_commands" in self.tag:
                    for cmd in self.tag.list_commands:
                        Util.pcolor(
                            status_color,
                            "  " + (subprocess.list2cmdline(cmd)
                                    if isinstance(cmd, list) else str(cmd))
                        )

        return errno  # type: ignore
