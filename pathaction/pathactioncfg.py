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
"""Load a PathAction configuration file."""

from __future__ import annotations

import contextlib
import fnmatch
import mimetypes
import os
import re
import shlex
import shutil
import subprocess  # nosec B404
import sys
from collections import UserDict
from copy import copy, deepcopy
from pathlib import Path
from typing import Any, ClassVar

if sys.platform != "win32":
    import pwd


import jinja2
import schema
import yaml  # type: ignore

from .exceptions import PathActionError
from .util import Util


def get_default_shell() -> str:
    """Return default shell path for the current platform."""
    if sys.platform == "win32":
        return os.environ.get("COMSPEC", "cmd.exe")

    # pylint: disable=possibly-used-before-assignment
    return pwd.getpwuid(os.getuid()).pw_shell


def platform_quote(text: str) -> str:
    """Return a shell-escaped version of the string for the current platform."""
    if sys.platform == "win32":
        return subprocess.list2cmdline([text])

    return shlex.quote(text)


class MatchMethods:
    """Match methods that are used by ActionCommand."""

    @staticmethod
    def mimetype_regex(path: str, string: str) -> bool:
        """Match a mime type with a regular expression."""
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return False

        return bool(re.match(string, file_mime, re.IGNORECASE))

    @staticmethod
    def mimetype(path: str, string: str) -> bool:
        """Check if file mimetype strictly matches the string."""
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return False

        return file_mime == string

    @staticmethod
    def mimetype_match(path: str, string: str) -> bool:
        """Check if file mimetype matches using fnmatch."""
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return False

        return bool(fnmatch.fnmatch(file_mime, string))


class ActionCommand(UserDict):
    """Represent a command in an action."""

    match_methods: ClassVar[list[tuple[str, Any, bool]]] = [
        (
            match_name if match_is_include else f"{match_name}_exclude",
            match_method,
            match_is_include,
        )
        for match_is_include in (False, True)
        for match_name, match_method in (
            ("path_match", fnmatch.fnmatch),
            ("path_match_case", fnmatch.fnmatchcase),
            ("mimetype_regex", MatchMethods.mimetype_regex),
            ("mimetype_match", MatchMethods.mimetype_match),
            ("mimetype", MatchMethods.mimetype),
            ("path_regex", lambda path, string: re.search(string, path, re.IGNORECASE)),
            ("path_regex_case", lambda path, string: re.search(string, path)),
        )
    ]

    schema_qa_options: ClassVar[dict[Any, Any]] = {
        schema.Optional("shell_path"): str,
        schema.Optional("timeout"): int,
        schema.Optional("verbose"): bool,
        schema.Optional("debug"): bool,
        schema.Optional("confirm_after_timeout"): int,
        schema.Optional("last"): bool,
    }

    schema_action_command: ClassVar[dict[Any, Any]] = {
        schema.Optional("tags"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("mimetype_match"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("mimetype_match_exclude"): schema.Or(
            str,
            [str],  # type: ignore
        ),
        schema.Optional("mimetype_regex"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("mimetype_regex_exclude"): schema.Or(
            str,
            [str],  # type: ignore
        ),
        schema.Optional("mimetype"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("mimetype_exclude"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_regex"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_regex_exclude"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_regex_case"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_regex_case_exclude"): schema.Or(
            str,
            [str],  # type: ignore
        ),
        schema.Optional("path_match"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_match_exclude"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_match_case"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("path_match_case_exclude"): schema.Or(
            str,
            [str],  # type: ignore
        ),
        schema.Optional("comment"): str,
        schema.Optional("timeout"): int,
        schema.Optional("shell"): bool,
        schema.Optional("list_commands"): [
            schema.Or(str, [str])  # type: ignore
        ],
        schema.Optional("command"): schema.Or(str, [str]),  # type: ignore
        schema.Optional("cwd"): str,
        schema.Optional("stdout"): str,
        schema.Optional("stderr"): str,
        schema.Optional("options"): schema_qa_options,
    }

    default_values: ClassVar[dict[str, Any]] = {
        "comment": "",
        "shell": False,
        "tags": "main",
    }

    def __init__(self, path_cfg: str, action_dict: dict) -> None:
        """Initialize the ActionCommand class."""
        super().__init__()

        schema_data = schema.Schema(ActionCommand.schema_action_command)
        schema_data.validate(action_dict)

        self.clear()
        for item in (self.default_values, action_dict):
            self.update(deepcopy(item))

        parent = Path(path_cfg).parent
        self.default_cwd = "" if parent == Path() else str(parent)
        self["path_cfg"] = str(path_cfg)
        if "cwd" not in self:
            self["cwd"] = self.default_cwd

        # Also validate the *_exclude regex keys for invalid regular expressions.
        for regex_key in (
            "path_regex_case",
            "path_regex_case_exclude",
            "path_regex",
            "path_regex_exclude",
            "mimetype_regex",
            "mimetype_regex_exclude",
        ):
            if regex_key in self:
                if isinstance(self[regex_key], str):
                    list_regex = [self[regex_key]]
                else:
                    list_regex = self[regex_key]

                for regex in list_regex:
                    try:
                        re.compile(regex)  # type: ignore
                    except re.error as err:
                        err_str = (
                            f"the regular expression '{regex}' "
                            f"is invalid (loaded from "
                            f"'{self['path_cfg']}')"
                        )
                        raise PathActionError(err_str) from err

        # The keys "command" and "list_commands" are mutually exclusive
        if "command" in self and "list_commands" in self:
            err_str = (
                "The keys 'command' and 'list_commands' cannot be "
                "both defined in " + str(self)
            )
            raise PathActionError(err_str)

    def __getattr__(self, key: str) -> Any:
        """Retrieve attribute."""
        # Raise AttributeError instead of KeyError to comply with Python's data model
        # (fixes hasattr, getattr with default, and copy).
        try:
            return self[key]
        except KeyError as err:
            raise AttributeError(key) from err

    def run(
        self, shell_path: str, timeout: float = 0, debug: bool = False
    ) -> tuple[str | list, int]:
        """Execute a command.

        Returns:
            Tuple containing the command and errno.
        """
        first_cmd = True
        if "command" in self:
            list_commands = [self.command]
        elif "list_commands" in self:
            list_commands = self.list_commands
        else:
            raise PathActionError("No command has been defined")

        # Initialize cmd and errno to prevent UnboundLocalError if
        # list_commands is an empty list.
        cmd: str | list = ""
        errno: int = 0

        for cmd in list_commands:
            if first_cmd:
                first_cmd = False
            else:
                Util.pcolor(Util.COLOR_TEXT, "")

            cmd_str = (
                subprocess.list2cmdline(cmd) if isinstance(cmd, list) else str(cmd)
            )

            timeout = self.get("timeout", timeout)

            if timeout > 0:
                Util.pcolor(Util.COLOR_TEXT, f"{timeout} seconds", prefix="[TIMEOUT] ")
            elif debug:
                Util.pcolor(Util.COLOR_TEXT, "No timeout.", prefix="[TIMEOUT] ")

            Util.pcolor(Util.COLOR_TEXT, cmd_str.replace("\n", r"\n"), prefix="[RUN] ")

            shell = self["shell"]
            if not isinstance(cmd, list) and not isinstance(cmd, str):
                raise ValueError("'cmd' has to be a list or a string")

            cwd = self["cwd"]
            if shell:
                if isinstance(cmd, list):
                    cmd = subprocess.list2cmdline(cmd)
            else:
                cmd = (
                    shlex.split(cmd, posix=(sys.platform != "win32"))
                    if isinstance(cmd, str)
                    else deepcopy(cmd)
                )
                if not cmd:
                    raise PathActionError("the command is empty.")

                cmd_path = Util.which(cmd[0], cwd=cwd)
                cmd[0] = str(cmd_path)

            kwargs: dict[str, Any] = {}
            kwargs["cwd"] = cwd
            if timeout > 0.0:
                kwargs["timeout"] = timeout  # type: ignore

            with contextlib.ExitStack() as stack:
                stdout_path: str | None = None
                stderr_path: str | None = None

                if self.get("stdout"):
                    stdout_path = self["stdout"]

                if self.get("stderr"):
                    stderr_path = self["stderr"]

                # Check that BOTH stdout_path and stderr_path exist before
                # calling .samefile(), otherwise .samefile() raises FileNotFoundError
                # when stdout_path exists but stderr_path does not.
                if (
                    stdout_path
                    and stderr_path
                    and (
                        (
                            Path(stdout_path).exists()
                            and Path(stderr_path).exists()
                            and Path(stdout_path).samefile(stderr_path)
                        )
                        or (Path(stdout_path).resolve() == Path(stderr_path).resolve())
                    )
                ):
                    kwargs["stdout"] = stack.enter_context(
                        Path(self["stdout"]).open("wb")
                    )
                    kwargs["stderr"] = kwargs["stdout"]
                    stdout_path = None
                    stderr_path = None

                if stdout_path:
                    kwargs["stdout"] = stack.enter_context(
                        Path(self["stdout"]).open("wb")
                    )

                if stderr_path:
                    kwargs["stderr"] = stack.enter_context(
                        Path(self["stderr"]).open("wb")
                    )

                if shell:
                    errno = subprocess.call(
                        cmd,
                        shell=True,  # nosec: B602
                        executable=shell_path,
                        **kwargs,  # type: ignore
                    )
                else:
                    errno = subprocess.call(cmd, **kwargs)  # type: ignore

            if errno != 0:
                break

        return (cmd, errno)


class PathActionCfg:
    """Load rules and options from '.pathaction.yaml'."""

    yaml_ext: ClassVar[list[str]] = [".yaml", ".yml"]

    default_options: ClassVar[dict[str, Any]] = {
        "shell_path": get_default_shell(),
        "confirm_after_timeout": 0,
        "debug": False,
        "verbose": False,
        "last": False,
    }

    schema_pathaction_cfg: ClassVar[dict[Any, Any]] = {
        schema.Optional("vars"): {
            schema.Optional(str): schema.Or(
                schema.Optional(str),
                schema.Optional(list),
                schema.Optional(dict),
                schema.Optional(int),
                schema.Optional(bool),
                schema.Optional(float),
            )
        },
        schema.Optional("options"): ActionCommand.schema_qa_options,
        "actions": [ActionCommand.schema_action_command],
    }

    def __init__(self, source_code: str) -> None:
        """Initialize the class PathActionCfg."""
        self.schema: schema.Schema = schema.Schema(PathActionCfg.schema_pathaction_cfg)

        # Init vars
        self.source_code: Path = Path(source_code)

        # The data
        self.env: dict = {}
        self.loaded_yaml_path: list[str] = []
        self.cfg: dict = {}

        # reset and load all ".pathaction.yaml" files
        self.reset()

    def reset(self) -> None:
        """Reset the configuration variables."""
        self.env = deepcopy(dict(os.environ))
        self.loaded_yaml_path = []
        self.cfg = {
            "options": deepcopy(PathActionCfg.default_options),
            "vars": {},
            "actions": [],
        }

    def get_action_cmd_cwd(self, action_cmd: ActionCommand) -> str:
        """Determine the working directory of an ActionCommand."""
        cwd = action_cmd["cwd"]
        cwd_rendered = Path(
            str(self._jinja2_render(cwd, cwd=str(action_cmd.default_cwd)))
        )

        if cwd_rendered.is_absolute():
            # os.path.normpath is needed here to squash any '..' segments
            # that might exist in the absolute path.
            return os.path.normpath(cwd_rendered)

        pathaction_path = Path(action_cmd.path_cfg).parent

        # Use os.path.abspath() instead of Path.absolute() so relative '..'
        # segments in cwd are normalized while still preserving symlinks.
        return os.path.abspath(pathaction_path / cwd_rendered)  # noqa: PTH100

    def find_command(self, action_name: str) -> ActionCommand | None:
        """Find command that matches the absolute path to the source code."""
        abs_source_code = str(self.source_code.absolute())

        is_match_found = False
        action_cmd: ActionCommand | None = None
        action_found = False
        for cur_action_cmd in self.cfg["actions"]:
            cur_action_cmd = copy(cur_action_cmd)

            tags = cur_action_cmd["tags"]
            if isinstance(tags, str):
                tags = [tags]

            if action_name not in tags:
                continue

            action_found = True

            # Evaluate cur_action_cmd["cwd"] once per action before iterating
            # over patterns so it is not repeatedly re-rendered on each pattern.
            cur_action_cmd["cwd"] = self.get_action_cmd_cwd(cur_action_cmd)

            # Track exclusion separately from inclusion. Previously, matching
            # an *_exclude rule set is_match_found = True and broke out of the outer
            # loop, preventing subsequent actions from being checked.
            is_excluded = False
            for (
                match_name,
                match_method,
                match_is_include,
            ) in ActionCommand.match_methods:
                if match_name not in cur_action_cmd:
                    continue

                list_patterns = (
                    [cur_action_cmd[match_name]]
                    if isinstance(cur_action_cmd[match_name], str)
                    else cur_action_cmd[match_name]
                )

                for pattern in list_patterns:
                    pattern = self._jinja2_render(pattern, cwd=cur_action_cmd.cwd)

                    if match_method(abs_source_code, str(pattern)):
                        if match_is_include:
                            is_match_found = True
                            action_cmd = cur_action_cmd.copy()
                        else:
                            is_excluded = True
                        break

                if is_excluded or is_match_found:
                    break

            if is_match_found:
                break

        if not action_found:
            raise PathActionError(
                f"There is no action tagged '{action_name}' for "
                f"the path {abs_source_code}"
            )

        if not action_cmd:
            return None

        #
        # Render Jinja2 all strings and list of strings that are in action_cmd
        #
        # This step has to be done after the match (because some Jinja2
        # filters are specific to the match, like 'shebang' for
        # example)
        #
        for key in action_cmd:
            # Skip internal "path_cfg" in addition to "cwd" so file paths
            # containing Jinja-like characters are not evaluated as templates.
            if key in ("cwd", "path_cfg"):
                continue

            action_cmd[key] = self._jinja2_render(action_cmd[key], cwd=action_cmd.cwd)

        return action_cmd

    def load_cfg(self, yaml_path: str) -> bool:
        """Merge data from the Yaml file."""
        # Resolve: Prevent the parser from loading the same configuration file multiple
        # times.
        abs_yaml_path = str(Path(yaml_path).resolve())
        if abs_yaml_path in self.loaded_yaml_path:
            # already loaded
            return False

        try:
            with Path(abs_yaml_path).open(encoding="utf-8") as fhandler:
                raw_cfg = yaml.full_load(fhandler)
        except yaml.YAMLError as err:
            err_msg = f"cannot load the YAML file '{abs_yaml_path}'. {err}"
            raise PathActionError(err_msg) from err

        try:
            self.schema.validate(raw_cfg)
        except schema.SchemaError as err:
            raise schema.SchemaError(f"'{abs_yaml_path}': {err}") from err

        # Merge default values
        for key in ("vars", "options"):
            if key in raw_cfg:
                self.cfg[key].update(raw_cfg[key])

                if key == "options":
                    self.cfg["options"] = self._jinja2_render(
                        self.cfg["options"],
                        cwd=str(Path(abs_yaml_path).parent),
                    )

        if "actions" in raw_cfg:
            new_actions = []
            path_cfg = abs_yaml_path
            for action_cmd in raw_cfg["actions"]:
                action_cmd = ActionCommand(path_cfg, action_cmd)
                new_actions.append(action_cmd)

            self.cfg["actions"] = new_actions

        # Checks
        shell_target = (
            shutil.which(self.cfg["options"]["shell_path"])
            or self.cfg["options"]["shell_path"]
        )
        if not os.access(shell_target, os.X_OK):
            err_msg = (
                f"the shell '{self.cfg['options']['shell_path']}' "
                "does not exist or is not an executable."
            )
            raise PathActionError(err_msg)

        self.loaded_yaml_path.append(abs_yaml_path)
        return True

    def load_all_cfg(self, limit: int) -> list[str]:
        """Find and load all 'pathaction.yaml' files."""
        self.reset()
        list_cfg_files: list[str] = []

        #
        # Find cfg files
        #
        # Load pathaction.yaml from the current directory and parent
        # directories
        #
        dirname = self.source_code.resolve()
        if not dirname.is_dir():
            dirname = dirname.parent

        while True:
            if limit == 0:
                break

            list_pathaction_files = Util.file_ends_with(
                str(dirname / ".pathaction"), PathActionCfg.yaml_ext
            )

            if len(list_pathaction_files) > 1:
                err_str = (
                    "more than one file that ends with "
                    + ", ".join(PathActionCfg.yaml_ext)
                    + " was found: "
                    + ", ".join(list_pathaction_files)
                )
                raise PathActionError(err_str)

            if list_pathaction_files and list_pathaction_files[0] not in list_cfg_files:
                list_cfg_files.insert(0, list_pathaction_files[0])

            if dirname == dirname.parent:
                break

            dirname = dirname.parent
            limit -= 1

        #
        # Load cfg files
        #
        loaded_cfg_files = []
        schema_error = None
        for yaml_path in list_cfg_files:
            try:
                if self.load_cfg(yaml_path):
                    loaded_cfg_files.append(yaml_path)

                if self.cfg["options"]["last"]:
                    # reload
                    self.reset()
                    loaded_cfg_files = []
                    if self.load_cfg(yaml_path):
                        loaded_cfg_files.append(yaml_path)
            except schema.SchemaError as err:
                if schema_error is None:
                    schema_error = str(err)

        if schema_error:
            raise PathActionError(schema_error)

        return loaded_cfg_files

    def _jinja2_render_string(self, string: str, cwd: str) -> str:
        """Render a Jinja2 string."""
        source_code_str = str(self.source_code.absolute())
        env = jinja2.Environment(  # nosec B701
            loader=jinja2.BaseLoader,  # type: ignore
            undefined=jinja2.StrictUndefined,
            autoescape=False,
        )

        # pylint: disable=unnecessary-lambda
        env.filters["shebang"] = lambda arg: Util.read_shebang(arg)  # noqa: PLW0108
        env.filters["shebang_list"] = lambda arg: shlex.split(
            Util.read_shebang(arg), posix=(sys.platform != "win32")
        )
        env.filters["shebang_quote"] = lambda arg: " ".join(
            platform_quote(item)
            for item in shlex.split(
                Util.read_shebang(arg), posix=(sys.platform != "win32")
            )
        )

        def env_filters_quote(arg):
            if isinstance(arg, list):
                return [
                    (
                        platform_quote(str(item))
                        if isinstance(item, (str, int, float))
                        and not isinstance(item, bool)
                        else item
                    )
                    for item in arg
                ]

            # Use isinstance() (excluding bool) instead of type(arg) in [...]
            # so string subclasses are supported and booleans are rejected.
            if isinstance(arg, (str, int, float)) and not isinstance(arg, bool):
                return platform_quote(str(arg))

            raise ValueError(f"quote: invalid type: {arg}")

        def env_filters_which(cmd_str):
            if isinstance(cmd_str, str):
                path_command = shutil.which(cmd_str)
                if not path_command:
                    err_str = f"which: command not found: {cmd_str}"
                    raise FileNotFoundError(err_str)

                return path_command

            raise ValueError(f"which: invalid type: {cmd_str}")

        env.filters["which"] = env_filters_which
        env.filters["quote"] = env_filters_quote
        env.filters["startswith"] = lambda string, prefix: string.startswith(prefix)
        env.filters["endswith"] = lambda string, suffix: string.endswith(suffix)
        env.filters["basename"] = lambda arg: Path(arg).name
        env.filters["dirname"] = lambda arg: str(Path(arg).parent)
        env.filters["file_only_dirname"] = lambda file_path: (
            str(Path(file_path).parent) if Path(file_path).is_file() else str(file_path)
        )
        env.filters["realpath"] = lambda arg: str(Path(arg).resolve())
        env.filters["abspath"] = lambda arg: str(Path(arg).absolute())
        env.filters["joinpath"] = lambda lst: str(Path(*lst))
        env.filters["joincmd"] = lambda lst: subprocess.list2cmdline(lst)  # noqa: PLW0108
        env.filters["splitcmd"] = lambda arg: shlex.split(
            arg, posix=(sys.platform != "win32")
        )
        env.filters["expanduser"] = lambda arg: str(Path(arg).expanduser())
        env.filters["relpath"] = lambda *arg: os.path.relpath(*arg)  # noqa: PLW0108
        env.filters["expandvars"] = lambda arg: os.path.expandvars(arg)  # noqa: PLW0108

        j2_template = env.from_string(string)

        j2_vars: dict[str, Any] = {}
        j2_vars.update(self.cfg["vars"])

        j2_vars.update(
            {"file": source_code_str, "env": self.env, "cwd": cwd, "pathsep": os.sep}
        )

        return j2_template.render(**j2_vars)

    def _jinja2_render(
        self, arg: str | list | dict | int | float | bool, cwd: str
    ) -> str | list | dict | int | float | bool:
        """Find and replace jinja2 variables like {{ file }}.

        Parameters:
            :arg: string or list of strings

        Returns: string or list of strings

        """
        if isinstance(arg, str):
            return self._jinja2_render_string(string=arg, cwd=cwd)

        if isinstance(arg, dict):
            result_dict = {}
            for key, value in arg.items():
                if isinstance(value, list):
                    value = self._jinja2_render(arg=value, cwd=cwd)

                if isinstance(value, str):
                    value = self._jinja2_render_string(string=value, cwd=cwd)

                result_dict[key] = value

            return result_dict

        if isinstance(arg, list):
            result_list = []
            for item in arg:
                if isinstance(item, list):
                    item = self._jinja2_render(arg=item, cwd=cwd)

                if isinstance(item, str):
                    item = self._jinja2_render_string(string=item, cwd=cwd)

                result_list.append(item)

            return result_list

        return arg

    @property
    def debug(self) -> bool:
        """Return True if debug is enabled."""
        return bool(self.cfg["options"]["debug"])

    @property
    def verbose(self) -> bool:
        """Return True if verbose or debug is enabled."""
        return bool(self.debug or self.cfg["options"]["verbose"])
