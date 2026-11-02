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
"""Test the class PathActionCfg()."""

import argparse
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pathaction import command_line_interface
from pathaction.allowed_paths import AllowedPaths
from pathaction.exceptions import PathActionError
from pathaction.pathactioncfg import ActionCommand, PathActionCfg
from pathaction.pathactioncli import PathActionCli

QA_BASEDIR = Path(__file__).resolve().parent / "pathactioncfg_cases"
EXIT_CODE_SH = 64
EXIT_CODE_NH = 111


@pytest.fixture()
def allowed_dirs():
    """Return an AllowedPaths instance with QA_BASEDIR temporarily allowed."""
    allow_dirs = AllowedPaths()
    allow_dirs.add(QA_BASEDIR, permanent=False)
    return allow_dirs


def test_init_command_line_interface():
    """Test the module entry point."""
    with patch("pathaction.PathActionCli") as mock_cli:
        command_line_interface()
        mock_cli.assert_called_once()


@patch("builtins.input", return_value="")
def test_ask_user_press_enter(mock_input, allowed_dirs):
    """Test ask_user_press_enter handles the prompt and halts successfully."""
    argv = [sys.argv[0], "mock.py", "-a"]
    with (
        patch.object(sys, "argv", argv),
        pytest.raises(SystemExit) as exitinfo,
        patch("pathaction.pathactioncfg.ActionCommand.run", return_value=(["mock"], 1)),
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 1
    mock_input.assert_called_once()


def test_handle_dir_permissions_disallow_error(capfd, allowed_dirs):
    """Test disallowed directory errors correctly."""
    argv = [sys.argv[0], "--disallow-dir", "/not/allowed/dir"]
    with (
        patch.object(sys, "argv", argv),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 1

    out, err = capfd.readouterr()
    assert "cannot be disallowed for this reason" in out + err


@patch("pathaction.pathactioncli.PathActionCli.load_cfg_files")
def test_main_exceptions(mock_load, allowed_dirs):
    """Test main exception blocks catching gracefully."""
    cli = PathActionCli.__new__(PathActionCli)
    cli.args = argparse.Namespace(confirm_after=False)
    cli.limit_loop = 1

    mock_load.side_effect = KeyboardInterrupt()
    assert cli.main(PathActionCfg("")) == 1

    cli.limit_loop = 1
    mock_load.side_effect = Exception("General error")
    assert cli.main(PathActionCfg("")) == 1

    cli.limit_loop = 1
    mock_load.side_effect = subprocess.TimeoutExpired("cmd", 10)
    assert cli.main(PathActionCfg("")) == 1

    cli.limit_loop = 1
    mock_load.side_effect = PathActionError("Path error")
    assert cli.main(PathActionCfg("")) == 1


@patch("pathaction.util.Util.ask_question")
def test_ask_execute_again_options(mock_ask):
    """Test prompting options and timeouts for re-executing."""
    cli = PathActionCli.__new__(PathActionCli)
    cli.args = argparse.Namespace(confirm_after=True)

    cfg = PathActionCfg("")
    cfg.cfg["options"]["confirm_after_timeout"] = 5

    # Test timeout option "t" then "a"
    mock_ask.side_effect = ["t", "a"]
    assert cli.ask_execute_again(cfg) is True

    # Test TimeoutError
    mock_ask.side_effect = TimeoutError()
    assert cli.ask_execute_again(cfg) is False


def test_printing_methods():
    """Test debug, verbose output and CLI result printing logic by hooking print."""
    cli = PathActionCli.__new__(PathActionCli)
    cli.args = argparse.Namespace(tag="main", confirm_before=False, confirm_after=False)

    cfg = PathActionCfg("")
    cfg.cfg["options"]["debug"] = True
    cfg.cfg["options"]["verbose"] = True
    cfg.cfg["options"]["shell_path"] = "/bin/sh"
    cfg.loaded_yaml_path = ["/mock/.pathaction.yaml"]

    action = ActionCommand(
        "/mock/.pathaction.yaml",
        {
            "command": ["echo", "test"],
            "comment": "A comment",
            "cwd": "/mock",
            "shell": True,
        },
    )

    with patch("builtins.print") as mock_print:
        cli.show_action_infos(cfg, action)

        # Verify the chunks printed via Util.pcolor() reached print()
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "A comment" in printed_output
        assert "[COMMAND]" in printed_output
        assert "[SHELL]" in printed_output

        mock_print.reset_mock()
        cli._print_run_debug(cfg, action)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "Run command arguments:" in printed_output

        mock_print.reset_mock()
        cli._print_execution_result(cfg, action, ["echo", "test"], 0)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "All commands were successful:" in printed_output

        mock_print.reset_mock()
        cli._print_execution_result(cfg, action, ["echo", "test"], 1)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "[FAILURE]" in printed_output

    # Test list_commands scenario
    action2 = ActionCommand(
        "/mock/.pathaction.yaml",
        {
            "list_commands": [["echo", "test2"]],
            "cwd": "/mock",
        },
    )
    with patch("builtins.print") as mock_print:
        cli.show_action_infos(cfg, action2)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "echo test2" in printed_output

        mock_print.reset_mock()
        cli._print_run_debug(cfg, action2)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "list commands" in printed_output

        mock_print.reset_mock()
        cli._print_execution_result(cfg, action2, ["echo", "test2"], 0)
        printed_output = "\n".join(
            call[0][0] for call in mock_print.call_args_list if call[0]
        )
        assert "echo test2" in printed_output


@patch("pathaction.util.Util.ask_question")
def test_confirm_execution(mock_ask):
    """Test prompting before execution handling."""
    cli = PathActionCli.__new__(PathActionCli)
    cli.args = argparse.Namespace(confirm_before=True)
    cli.confirm_before_disabled = False

    mock_ask.return_value = "n"
    assert cli._confirm_execution() is False

    mock_ask.return_value = "y"
    assert cli._confirm_execution() is True
    assert cli.confirm_before_disabled is True


@patch("pathaction.util.Util.error")
def test_pathactioncli_dir_not_allowed(mock_error):
    """Test CLI exit code when the target file's directory is not allowed."""
    allowed_dirs = AllowedPaths()  # Do not use fixture; ensure it stays unauthorized
    target_file = QA_BASEDIR.joinpath("case1", "file.sh")
    argv = [sys.argv[0], str(target_file)]
    with (
        patch.object(sys, "argv", argv),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

    assert exitinfo.value.code == 1

    mock_error.assert_called_once()
    assert f"not allowed: '{target_file.parent}'" in mock_error.call_args[0][0]


@patch("pathaction.util.Util.error")
def test_pathactioncli_dir_not_allowed_directory(mock_error):
    """Test CLI exit code when a directory is passed and it is not allowed."""
    allowed_dirs = AllowedPaths()  # Do not use fixture; ensure it stays unauthorized
    target_dir = QA_BASEDIR.joinpath("case1")
    argv = [sys.argv[0], str(target_dir)]
    with (
        patch.object(sys, "argv", argv),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 1

    mock_error.assert_called_once()
    # Verify it prints the target directory itself, not its parent
    assert f"not allowed: '{target_dir}'" in mock_error.call_args[0][0]


def test_pathactioncli(allowed_dirs: AllowedPaths):
    """Test CLI execution on a single allowed file."""
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.sh"))]
    with (
        patch.object(sys, "argv", argv),
        patch(
            "pathaction.pathactioncfg.ActionCommand.run",
            return_value=(["mock"], EXIT_CODE_SH),
        ),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

    assert exitinfo.value.code == EXIT_CODE_SH


def test_pathactioncli_error_between_2_success(allowed_dirs: AllowedPaths):
    """Test CLI exit code when a command fails between two successful commands."""
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.nh"))]
    with (
        patch.object(sys, "argv", argv),
        patch(
            "pathaction.pathactioncfg.ActionCommand.run",
            return_value=(["mock"], EXIT_CODE_NH),
        ),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

    assert exitinfo.value.code == EXIT_CODE_NH


def test_pathactioncli_error_between_2_successful_files(allowed_dirs: AllowedPaths):
    """Test CLI exit code when processing multiple files with an error."""
    argv = [
        sys.argv[0],
        str(QA_BASEDIR.joinpath("case1", "file.nh")),
        str(QA_BASEDIR.joinpath("case1", "file2.nh")),
    ]
    with (
        patch.object(sys, "argv", argv),
        patch(
            "pathaction.pathactioncfg.ActionCommand.run",
            return_value=(["mock"], EXIT_CODE_NH),
        ),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

    assert exitinfo.value.code == EXIT_CODE_NH


def test_pathactioncli_no_filenames(allowed_dirs: AllowedPaths):
    """Test CLI exit code when no filenames are passed."""
    with (
        patch.object(sys, "argv", [sys.argv[0]]),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 1


def test_pathactioncli_require_tty(allowed_dirs: AllowedPaths):
    """Test CLI exit code when require_tty is True and stdin is not a TTY."""
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.py"))]
    with (
        patch.object(sys, "argv", argv),
        patch.object(sys.stdin, "isatty", return_value=False),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(
            require_tty=True,
            limit_loop=1,
            limit_load_cfg=1,
            allowed_dirs=allowed_dirs,
        )
    assert exitinfo.value.code == 1


def test_pathactioncli_dir_permission_flags(tmp_path: Path):
    """Test --allow-dir, --list-allowed-dirs, --disallow-dir, and --list flags."""
    cfg_file = tmp_path / "permissions.yml"
    allowed_dirs = AllowedPaths()
    target_dir = QA_BASEDIR / "case1"
    target_file = target_dir / "file.py"

    with patch("pathaction.pathactioncli.CFG_ALLOWED_DIRS", Path(cfg_file)):
        # --allow-dir on a file (should fail with exit code 1)
        with (
            patch.object(sys, "argv", [sys.argv[0], "--allow-dir", str(target_file)]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 1

        # --allow-dir on a valid directory (should succeed with exit code 0)
        with (
            patch.object(sys, "argv", [sys.argv[0], "--allow-dir", str(target_dir)]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 0
        assert allowed_dirs.is_allowed(target_dir)

        # Multiple --allow-dir paths (should continue processing and succeed with 0)
        with (
            patch.object(
                sys,
                "argv",
                [sys.argv[0], "--allow-dir", str(target_dir), str(target_dir.parent)],
            ),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 0
        assert allowed_dirs.is_allowed(target_dir.parent)

        # --list-allowed-dirs (should succeed with exit code 0)
        with (
            patch.object(sys, "argv", [sys.argv[0], "--list-allowed-dirs"]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 0

        # --list configuration files
        with (
            patch.object(sys, "argv", [sys.argv[0], "--list", str(target_file)]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(limit_load_cfg=1, allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 0

        # --disallow-dir on an allowed directory (should succeed with exit code 0)
        with (
            patch.object(sys, "argv", [sys.argv[0], "--disallow-dir", str(target_dir)]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 0

        # --disallow-dir on a directory not in allowed_dirs (should fail with 1)
        with (
            patch.object(sys, "argv", [sys.argv[0], "--disallow-dir", str(target_dir)]),
            pytest.raises(SystemExit) as exitinfo,
        ):
            PathActionCli(allowed_dirs=allowed_dirs)
        assert exitinfo.value.code == 1


def test_pathactioncli_confirm_before_and_after(allowed_dirs: AllowedPaths):
    """Test --confirm-before and --confirm-after interactive flows."""
    target_file = str(QA_BASEDIR.joinpath("case1", "file.py"))

    # --confirm-before declined ("n")
    with (
        patch.object(sys, "argv", [sys.argv[0], "-b", target_file]),
        patch("pathaction.util.Util.ask_question", return_value="n"),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 1

    # --confirm-before accepted ("y") and --confirm-after ("t" then "n")
    with (
        patch.object(sys, "argv", [sys.argv[0], "-b", "-a", target_file]),
        patch("pathaction.pathactioncfg.ActionCommand.run", return_value=(["mock"], 0)),
        patch(
            "pathaction.util.Util.ask_question",
            side_effect=["y", "t", "n"],
        ),
        pytest.raises(SystemExit) as exitinfo,
    ):
        PathActionCli(limit_loop=2, limit_load_cfg=1, allowed_dirs=allowed_dirs)
    assert exitinfo.value.code == 0
