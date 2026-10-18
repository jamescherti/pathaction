#!/usr/bin/env python
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
"""Test the class ActionCommand()."""

from collections import UserDict

import pytest

from pathaction.exceptions import PathActionError
from pathaction.pathactioncfg import ActionCommand
from pathaction.util import Util


def test_actioncommand_exclusive_command():
    """Test mutually exclusive command options in ActionCommand."""
    path_cfg = ".pathaction.yaml"
    action_dict = {"list_commands": ["true"], "command": "true"}
    with pytest.raises(PathActionError):
        ActionCommand(path_cfg=path_cfg, action_dict=action_dict)


def test_actioncommand_schema():
    """Test the ActionCommand schema and default values."""
    path_cfg = ".pathaction.yaml"
    action_dict = {"list_commands": ["true"]}
    actioncommand = ActionCommand(path_cfg=path_cfg, action_dict=action_dict)

    default_values = ActionCommand.default_values.copy()
    default_values["path_cfg"] = path_cfg
    assert actioncommand["path_cfg"] == path_cfg
    assert actioncommand["comment"] == ""
    assert actioncommand["shell"] is False
    assert actioncommand["cwd"] == ""
    assert isinstance(ActionCommand, UserDict) is False


def test_actioncommand_run_list_commands():
    """Test running ActionCommand with list_commands."""
    action_dict = {
        "list_commands": [["true"]],
        "comment": "",
        "cwd": "/",
        "tags": "main",
        "shell": False,
    }
    action_command = ActionCommand(path_cfg="", action_dict=action_dict)
    action_dict["path_cfg"] = ""
    assert action_command == action_dict
    assert action_command.run(shell_path=Util.which("sh"), timeout=0) == (
        [str(Util.which("true"))],
        0,
    )


def test_actioncommand_run_commands():
    """Test running ActionCommand with a single command."""
    action_dict = {
        "command": "true",
        "comment": "",
        "cwd": "/",
        "tags": "main",
        "shell": False,
    }
    action_command = ActionCommand(path_cfg="", action_dict=action_dict)
    action_dict["path_cfg"] = ""
    assert action_command == action_dict
    assert action_command.run(shell_path=Util.which("sh"), timeout=0) == (
        [str(Util.which("true"))],
        0,
    )


def test_actioncommand_getattr():
    """Test attribute lookup and AttributeError on ActionCommand."""
    action_command = ActionCommand(
        path_cfg=".pathaction.yaml", action_dict={"command": "true"}
    )
    assert action_command.command == "true"
    with pytest.raises(AttributeError):
        _ = action_command.non_existent_attribute


def test_actioncommand_invalid_regex_list():
    """Test ActionCommand initialization with an invalid regex in a list."""
    with pytest.raises(PathActionError):
        ActionCommand(
            path_cfg=".pathaction.yaml",
            action_dict={"command": "true", "path_regex_exclude": ["[invalid"]},
        )


def test_actioncommand_run_errors():
    """Test error conditions in ActionCommand.run()."""
    action_command = ActionCommand(path_cfg="", action_dict={})
    with pytest.raises(PathActionError):
        action_command.run(shell_path=Util.which("sh"))

    empty_cmd = ActionCommand(path_cfg="", action_dict={"command": ""})
    with pytest.raises(PathActionError):
        empty_cmd.run(shell_path=Util.which("sh"))

    invalid_type_cmd = ActionCommand(path_cfg="", action_dict={"command": "true"})
    invalid_type_cmd["command"] = 123  # type: ignore[assignment]
    with pytest.raises(ValueError, match="'cmd' has to be a list or a string"):
        invalid_type_cmd.run(shell_path=Util.which("sh"))


def test_actioncommand_run_shell_list_and_timeout():
    """Test running multiple commands with shell=True, timeout, and debug."""
    action_dict = {
        "list_commands": [["true"], ["true"]],
        "cwd": "/",
        "shell": True,
        "timeout": 5,
    }
    action_command = ActionCommand(path_cfg="", action_dict=action_dict)
    assert action_command.run(shell_path=Util.which("sh"), debug=True) == (
        "true",
        0,
    )

    del action_command["timeout"]
    assert action_command.run(shell_path=Util.which("sh"), timeout=0, debug=True) == (
        "true",
        0,
    )
