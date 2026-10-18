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

import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pathaction.allowed_paths import AllowedPaths
from pathaction.pathactioncli import PathActionCli

QA_BASEDIR = Path("./tests/pathactioncfg_cases")
EXIT_CODE_SH = 64
EXIT_CODE_NH = 111


@pytest.fixture()
def allowed_dirs():
    """Return an AllowedPaths instance with QA_BASEDIR temporarily allowed."""
    allow_dirs = AllowedPaths()
    allow_dirs.add(QA_BASEDIR, permanent=False)
    return allow_dirs


def test_pathactioncli_dir_not_allowed():
    """Test CLI exit code when the target directory is not allowed."""
    allowed_dirs = AllowedPaths()
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.sh"))]
    with patch.object(sys, "argv", argv):
        # Test success
        with pytest.raises(SystemExit) as exitinfo:
            PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == 1


def test_pathactioncli(allowed_dirs: AllowedPaths):
    """Test CLI execution on a single allowed file."""
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.sh"))]
    with (
        patch.object(sys, "argv", argv),
        patch(
            "pathaction.pathactioncfg.ActionCommand.run",
            return_value=(["mock"], EXIT_CODE_SH),
        ),
    ):
        with pytest.raises(SystemExit) as exitinfo:
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
    ):
        with pytest.raises(SystemExit) as exitinfo:
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
    ):
        with pytest.raises(SystemExit) as exitinfo:
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
