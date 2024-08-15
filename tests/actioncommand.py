#!/usr/bin/env python
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
