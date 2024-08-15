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
"""Load a PathAction configuration file."""

import mimetypes
import os
import pwd
import re
import shlex
import shutil
import subprocess  # nosec B404
from collections import UserDict
from copy import copy, deepcopy
from glob import fnmatch  # type: ignore
from pathlib import Path
from typing import Any, List, Tuple, Union

import jinja2
import schema
import yaml  # type: ignore
from markupsafe import escape as jinja2_escape

from .exceptions import PathActionError
from .util import Util


class MatchMethods:
    """Match methods that are used by ActionCommand."""

    @staticmethod
    def mimetype_regex(path: str, string: str):
        """Match a mime type with a regular expression."""
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return False

        return bool(re.match(string, file_mime, re.IGNORECASE))

    @staticmethod
    # pylint: disable=missing-function-docstring
    def mimetype(path: str, string: str):
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return False

        return file_mime == string

    @staticmethod
    # pylint: disable=missing-function-docstring
    def mimetype_match(path: str, string: str):
        file_mime = mimetypes.guess_type(path)[0]
        if not file_mime:
            return None

        return fnmatch.fnmatch(file_mime, string)


class ActionCommand(UserDict):
    """A command in an action."""

    match_methods = [
        (match_name if match_is_include else f"{match_name}_exclude",
         match_method,
         match_is_include)
        for match_is_include in (False, True)
        for match_name, match_method in (
            ("path_match", fnmatch.fnmatch),
            ("path_match_case", fnmatch.fnmatchcase),
            ("mimetype_regex", MatchMethods.mimetype_regex),
            ("mimetype_match", MatchMethods.mimetype_match),
            ("mimetype", MatchMethods.mimetype),
            ("path_regex",
             lambda path, string:
             re.search(string, path, re.IGNORECASE)),
            ("path_regex_case",
             lambda path, string:
             re.search(string, path)),
        )
    ]

    schema_qa_options = {
        schema.Optional("shell_path"): str,
        schema.Optional("timeout"): int,
        schema.Optional("verbose"): bool,
        schema.Optional("debug"): bool,
        schema.Optional("confirm_after_timeout"): int,
        schema.Optional("last"): bool,
    }

    schema_action_command = {
        schema.Optional("tags"): schema.Or(str, [str]),
        schema.Optional("mimetype_match"): schema.Or(str, [str]),
        schema.Optional("mimetype_match_exclude"): schema.Or(str, [str]),
        schema.Optional("mimetype_regex"): schema.Or(str, [str]),
        schema.Optional("mimetype_regex_exclude"): schema.Or(str, [str]),
        schema.Optional("mimetype"): schema.Or(str, [str]),
        schema.Optional("mimetype_exclude"): schema.Or(str, [str]),
        schema.Optional("path_regex"): schema.Or(str, [str]),
        schema.Optional("path_regex_exclude"): schema.Or(str, [str]),
        schema.Optional("path_match"): schema.Or(str, [str]),
        schema.Optional("path_match_exclude"): schema.Or(str, [str]),
        schema.Optional("comment"): str,
        schema.Optional("timeout"): int,
        schema.Optional("shell"): bool,
        schema.Optional("list_commands"): [schema.Or(str, [str])],
        schema.Optional("command"): schema.Or(str, [str]),
        schema.Optional("cwd"): str,
        schema.Optional("stdout"): str,
        schema.Optional("stderr"): str,
        schema.Optional("options"): schema_qa_options,
    }

    default_values = {
        "comment": "",
        "shell": False,
        "tags": "main",
    }

    def __init__(self, path_cfg: str, action_dict: dict):
        """Init the class ActionCommand()."""
        super().__init__()

        schema_data = schema.Schema(ActionCommand.schema_action_command)
        schema_data.validate(action_dict)

        self.clear()
        for item in (self.default_values, action_dict):
            self.update(deepcopy(item))

        self.default_cwd = os.path.dirname(path_cfg)
        self["path_cfg"] = str(jinja2_escape(path_cfg))
        if "cwd" not in self:
            # self["cwd"] = jinja2_escape(os.path.dirname(self.path_cfg))
            self["cwd"] = self.default_cwd

        # Check the validity of the regex
        for regex_key in ("path_regex_case", "path_regex", "mimetype_regex"):
            if regex_key in self:
                if isinstance(self[regex_key], str):
                    list_regex = [self[regex_key]]
                else:
                    list_regex = self[regex_key]

                for regex in list_regex:
                    try:
                        re.compile(regex)  # type: ignore
                    except re.error as err:
                        err_str = (f"the regular expression '{regex}' "
                                   f"is invalid (loaded from "
                                   f"'{self['path_cfg']}')")
                        raise PathActionError(err_str) from err

        # The keys "command" and "list_commands" are mutually exclusive
        if "command" in self and "list_commands" in self:
            err_str = ("The keys 'command' and 'list_commands' cannot be "
                       "both defined in in " + str(self))
            raise PathActionError(err_str)

    def __getattr__(self, key: str) -> Any:
        """Get attribute."""
        return self[key]

    def run(self, shell_path: str,
            timeout: float = 0,
            debug: bool = False) -> Tuple[Union[str, list], int]:
        """Execute a command.

        Return (command, errno)

        """
        first_cmd = True
        if "command" in self:
            list_commands = [self.command]
        elif "list_commands" in self:
            list_commands = self.list_commands
        else:
            raise PathActionError("No command has been defined")

        for cmd in list_commands:
            if first_cmd:
                first_cmd = False
            else:
                Util.pcolor(Util.COLOR_TEXT, "")

            cmd_str = (subprocess.list2cmdline(cmd)
                       if isinstance(cmd, list)
                       else str(cmd))

            try:
                # local timeout
                timeout = self["timeout"]
            except KeyError:
                pass

            if timeout > 0:
                Util.pcolor(Util.COLOR_TEXT,
                            f"{timeout} seconds",
                            prefix="[TIMEOUT] ")
            elif debug:
                Util.pcolor(Util.COLOR_TEXT, "No timeout.",
                            prefix="[TIMEOUT] ")

            Util.pcolor(Util.COLOR_TEXT,
                        cmd_str.replace("\n", r"\n"),
                        prefix="[RUN] ")

            shell = self["shell"]
            cwd = self["cwd"]

            if not isinstance(cmd, list) and not isinstance(cmd, str):
                raise ValueError("'cmd' has to be a list of a string")

            if shell:
                if isinstance(cmd, list):
                    cmd = subprocess.list2cmdline(cmd)
            else:
                cmd = shlex.split(cmd) \
                    if isinstance(cmd, str) else deepcopy(cmd)
                if not cmd:
                    raise PathActionError("the command is empty.")

                cmd_path = Util.which(cmd[0], cwd=cwd)
                cmd[0] = str(cmd_path)

            kwargs = {}
            kwargs["cwd"] = cwd
            if timeout > 0.0:
                kwargs["timeout"] = timeout  # type: ignore

            try:
                stdout = None
                stderr = None
                if "stdout" in self and self["stdout"]:
                    stdout = Path(self["stdout"])

                if "stderr" in self and self["stderr"]:
                    stderr = Path(self["stderr"])

                if (stdout and stderr and
                        ((stdout.exists() and stdout.samefile(stderr)) or
                         (stdout.resolve() == stderr.resolve()))):
                    kwargs["stdout"] = open(self["stdout"], "wb")
                    kwargs["stderr"] = kwargs["stdout"]
                    stdout = None
                    stderr = None

                if stdout:
                    kwargs["stdout"] = open(self["stdout"], "wb")

                if stderr:
                    kwargs["stderr"] = open(self["stderr"], "wb")

                if shell:
                    errno = subprocess.call(
                        cmd,
                        shell=True,  # nosec: B602
                        executable=shell_path,
                        **kwargs  # type: ignore
                    )
                else:
                    errno = subprocess.call(cmd, **kwargs)  # type: ignore
            finally:
                if "stdout" in kwargs:
                    kwargs["stdout"].close()

                if "stderr" in kwargs:
                    kwargs["stderr"].close()

            if errno != 0:
                break

        return (cmd, errno)


class PathActionCfg:
    """Load rules and options from '.pathaction.yaml'."""

    yaml_ext = [".yaml", ".yml"]

    default_options = {
        "shell_path": pwd.getpwuid(os.getuid()).pw_shell,
        "confirm_after_timeout": 0,
        "debug": False,
        "verbose": False,
        "last": False
    }

    schema_pathaction_cfg = {
        schema.Optional('vars'): {
            schema.Optional(str):
            schema.Or(
                schema.Optional(str),
                schema.Optional(list),
                schema.Optional(dict),
                schema.Optional(int),
                schema.Optional(bool),
                schema.Optional(float)
            )
        },

        schema.Optional("options"): ActionCommand.schema_qa_options,

        'actions': [ActionCommand.schema_action_command],
    }

    def __init__(self, source_code: str):
        """Init the class PathAction()."""
        self.schema: schema.Schema = schema.Schema(
            PathActionCfg.schema_pathaction_cfg
        )

        # if not os.path.exists(source_code):
        #     err_str = f"'{source_code}' does not exist."
        #     raise PathActionError(err_str)

        # Init vars
        self.source_code: str = os.path.normpath(source_code)

        # The data
        self.env: dict = {}
        self.loaded_yaml_path: list = []
        self.cfg: dict = {}

        # reset and load all ".pathaction.yaml" files
        self.reset()

    def reset(self):
        """Reset the configuration."""
        self.env: dict = deepcopy(os.environ)
        self.loaded_yaml_path = []
        self.cfg = {
            "options": deepcopy(PathActionCfg.default_options),
            "vars": {},
            "actions": {}
        }

    def get_action_cmd_cwd(self, action_cmd: ActionCommand) -> str:
        """The cwd of an ActionCommand."""
        cwd = action_cmd["cwd"]
        cwd = self._jinja2_render(cwd, cwd=action_cmd.default_cwd)

        if os.path.isabs(cwd):
            return str(cwd)

        pathaction_path = os.path.dirname(action_cmd.path_cfg)
        return str(os.path.abspath(
            os.path.join(pathaction_path, action_cmd["cwd"])
        ))

    def find_command(self, action_name: str) -> Union[ActionCommand, None]:
        """Find command that matches the absolute path to the source code."""
        abs_source_code = os.path.abspath(self.source_code)
        # if action_name not in self.cfg["actions"]:
        #     raise PathActionError("the ActionCommand wasn't found")

        is_match_found = False
        action_cmd: Union[ActionCommand, None] = None
        action_found = False
        for cur_action_cmd in self.cfg["actions"]:
            cur_action_cmd = copy(cur_action_cmd)

            tags = cur_action_cmd["tags"]
            if isinstance(tags, str):
                tags = [tags]

            if action_name not in tags:
                continue

            action_found = True
            for (match_name, match_method,
                 match_is_include) in ActionCommand.match_methods:
                if match_name not in cur_action_cmd:
                    continue

                list_patterns = (
                    [cur_action_cmd[match_name]]
                    if isinstance(cur_action_cmd[match_name], str)
                    else cur_action_cmd[match_name]
                )

                for pattern in list_patterns:
                    #
                    # Fix cwd after Jinja2 is rendered.
                    #
                    # This part has to be interpreter after Jinja2 render
                    # (check above)
                    #
                    # if "cwd" in action_cmd:
                    cur_action_cmd["cwd"] = \
                        self.get_action_cmd_cwd(cur_action_cmd)

                    pattern = self._jinja2_render(pattern,
                                                  cwd=cur_action_cmd.cwd)

                    if match_method(abs_source_code, pattern):
                        is_match_found = True
                        if match_is_include:
                            action_cmd = cur_action_cmd.copy()
                        break

                if is_match_found:
                    break

            if is_match_found:
                break

        if not action_found:
            raise PathActionError(
                f"There is no action tagged '{action_name}' for "
                f"the path {os.path.abspath(self.source_code)}"
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
        for key in action_cmd.keys():
            if key == "cwd":
                continue

            action_cmd[key] = self._jinja2_render(
                action_cmd[key],
                cwd=action_cmd.cwd
            )

        return action_cmd

    def load_cfg(self, yaml_path: str) -> bool:
        """Merge data from the Yaml file."""
        yaml_path = os.path.abspath(yaml_path)
        if yaml_path in self.loaded_yaml_path:
            # already loaded
            return False

        try:
            with open(yaml_path, 'r', encoding="utf-8") as fhandler:
                raw_cfg = yaml.full_load(fhandler)
        except yaml.YAMLError as err:
            err_msg = f"cannot load the YAML file '{yaml_path}'. {err}"
            raise PathActionError(err_msg) from err

        try:
            self.schema.validate(raw_cfg)
        except schema.SchemaError as err:
            raise schema.SchemaError(f"'{yaml_path}': {err}") \
                from err

        # Merge default values
        for key in ("vars", "options"):
            if key in raw_cfg:
                self.cfg[key].update(raw_cfg[key])

                if key == "options":
                    self.cfg["options"] = self._jinja2_render(
                        self.cfg["options"],
                        cwd=os.path.dirname(yaml_path),
                    )

        if "actions" in raw_cfg:
            new_actions = []
            path_cfg = os.path.abspath(yaml_path)
            for action_cmd in raw_cfg["actions"]:
                action_cmd = ActionCommand(path_cfg, action_cmd)
                new_actions.append(action_cmd)

            self.cfg["actions"] = new_actions

        # Checks
        if not os.access(self.cfg["options"]["shell_path"], os.X_OK):
            err_msg = (f"the shell '{self.cfg['options']['shell_path']}' "
                       "does not exist or is not an executable.")
            raise PathActionError(err_msg)

        self.loaded_yaml_path.append(yaml_path)
        return True

    def load_all_cfg(self, limit: int) -> List[str]:
        """Find and load all 'pathaction.yaml' files."""
        self.reset()

        list_cfg_files: list = []

        #
        # Find cfg files
        #
        # Load pathaction.yaml from the current directory and parent
        # directories
        #
        filename = ""
        dirname = os.path.realpath(self.source_code)
        first = True
        while True:
            if first:
                if not os.path.isdir(dirname):
                    dirname, filename = os.path.split(dirname)

                first = False
            else:
                dirname, filename = os.path.split(dirname)

                if not filename:
                    break

            if limit == 0:
                break

            list_pathaction_files = Util.file_ends_with(
                os.path.join(dirname, ".pathaction"),
                PathActionCfg.yaml_ext
            )

            if len(list_pathaction_files) > 1:
                err_str = ("more than one file that ends with " +
                           ", ".join(PathActionCfg.yaml_ext) +
                           " was found: " +
                           ", ".join(list_pathaction_files))
                raise PathActionError(err_str)

            if list_pathaction_files and \
                    list_pathaction_files[0] not in list_cfg_files:
                list_cfg_files.insert(0, list_pathaction_files[0])

            limit -= 1

            if not dirname:
                break

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
                    self.load_cfg(yaml_path)
            except schema.SchemaError as err:
                if schema_error is None:
                    schema_error = str(err)

        if schema_error:
            raise PathActionError(schema_error)

        return loaded_cfg_files

    def _jinja2_render_string(self, string: str,
                              cwd: str) -> str:
        """Render a Jinja2 string."""
        source_code = os.path.abspath(self.source_code)
        env = jinja2.Environment(   # nosec B701
            loader=jinja2.BaseLoader,    # type: ignore
            undefined=jinja2.StrictUndefined,
            autoescape=False
        )

        # pylint: disable=unnecessary-lambda
        env.filters['shebang'] = lambda arg: Util.read_shebang(arg)
        env.filters['shebang_list'] = \
            lambda arg: shlex.split(Util.read_shebang(arg))
        env.filters['shebang_quote'] = \
            lambda arg: \
            subprocess.list2cmdline(
                [shlex.quote(item)
                 for item in shlex.split(Util.read_shebang(arg))]
        )

        def env_filters_quote(arg):
            if isinstance(arg, list):
                return [(shlex.quote(item) if isinstance(item, str) else item)
                        for item in arg]

            if type(arg) in [str, int, float]:
                return shlex.quote(str(arg))

            raise ValueError(f"quote: invalid type: {arg}")

        def env_filters_which(cmd_str):
            if isinstance(cmd_str, str):
                path_command = shutil.which(cmd_str)
                if not path_command:
                    err_str = f"which: command not found: {cmd_str}"
                    raise FileNotFoundError(err_str)

                return path_command

            raise ValueError(f"which: invalid type: {cmd_str}")

        env.filters['which'] = env_filters_which
        env.filters['quote'] = env_filters_quote
        env.filters['startswith'] = \
            lambda string, prefix: string.startswith(prefix)
        env.filters['endswith'] = \
            lambda string, suffix: string.endswith(suffix)
        env.filters['basename'] = lambda arg: os.path.basename(arg)
        env.filters['dirname'] = lambda arg: os.path.dirname(arg)
        env.filters['file_only_dirname'] = lambda file_path: \
            os.path.dirname(file_path) \
            if os.path.isfile(file_path) else file_path
        env.filters['realpath'] = lambda arg: os.path.realpath(arg)
        env.filters['abspath'] = lambda arg: os.path.abspath(arg)
        env.filters['relpath'] = lambda *arg: os.path.relpath(*arg)
        env.filters['joinpath'] = lambda lst: os.path.join(*lst)
        env.filters['joincmd'] = lambda lst: subprocess.list2cmdline(lst)
        env.filters['splitcmd'] = lambda arg: shlex.split(arg)
        env.filters['expanduser'] = lambda arg: os.path.expanduser(arg)
        env.filters['expandvars'] = lambda arg: os.path.expandvars(arg)

        j2_template = env.from_string(string)

        j2_vars = {}
        j2_vars.update(self.cfg["vars"])
        j2_vars.update(dict(file=source_code,
                            env=self.env,
                            cwd=cwd,
                            pathsep=os.path.sep))

        return j2_template.render(**j2_vars)

    def _jinja2_render(self,
                       arg: Union[str, list, dict, int, float, bool],
                       cwd: str) -> Union[str, list, dict, int, float, bool]:
        """Find and replace jinja2 variables like {{ file }}.

        Parameters:
            :arg: string or list of strings

        Returns: string or list of strings

        """
        arg_was_not_list = False
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
                    item = self._jinja2_render_string(string=item,
                                                      cwd=cwd)

                result_list.append(item)

            return result_list[0] if arg_was_not_list else result_list

        return arg

    @property
    def debug(self) -> bool:
        """Debug."""
        return bool(self.cfg["options"]["debug"])

    @property
    def verbose(self) -> bool:
        """Verbose."""
        return bool(self.debug or self.cfg["options"]["verbose"])
