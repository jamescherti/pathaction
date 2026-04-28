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
    path_cfg = ".pathaction.yaml"
    action_dict = {"list_commands": ["true"],
                   "command": "true"}
    with pytest.raises(PathActionError):
        actioncommand = ActionCommand(path_cfg=path_cfg,
                                      action_dict=action_dict)


def test_actioncommand_schema():
    path_cfg = ".pathaction.yaml"
    action_dict = {"list_commands": ["true"]}
    actioncommand = ActionCommand(path_cfg=path_cfg,
                                  action_dict=action_dict)

    default_values = ActionCommand.default_values.copy()
    default_values["path_cfg"] = path_cfg
    assert actioncommand["path_cfg"] == path_cfg
    assert actioncommand["comment"] == ""
    assert actioncommand["shell"] is False
    assert actioncommand["cwd"] == ""
    assert isinstance(ActionCommand, UserDict) is False


def test_actioncommand_run_list_commands():
    action_dict = {"list_commands": [["true"]],
                   "comment": "",
                   "cwd": "/",
                   "tags": "main",
                   "shell": False}
    action_command = ActionCommand(path_cfg='', action_dict=action_dict)
    action_dict['path_cfg'] = ''
    assert action_command == action_dict
    assert action_command.run(shell_path=Util.which("sh"), timeout=0) == \
        ([str(Util.which("true"))], 0)


def test_actioncommand_run_commands():
    action_dict = {"command": "true",
                   "comment": "",
                   "cwd": "/",
                   "tags": "main",
                   "shell": False}
    action_command = ActionCommand(path_cfg='', action_dict=action_dict)
    action_dict['path_cfg'] = ''
    assert action_command == action_dict
    assert action_command.run(shell_path=Util.which("sh"), timeout=0) == \
        ([str(Util.which("true"))], 0)
