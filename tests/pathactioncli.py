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
    with patch.object(sys, "argv", argv):
        # Test success
        with pytest.raises(SystemExit) as exitinfo:
            PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == EXIT_CODE_SH

        # Test Failure
        # pathactioncli = PathActionCli(limit_loop=1,
        #                               limit_load_cfg=1,
        #                               exit=False)
        # assert pathactioncli. == 64


def test_pathactioncli_error_between_2_success(allowed_dirs: AllowedPaths):
    """Test CLI exit code when a command fails between two successful commands."""
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.nh"))]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exitinfo:
            # Test success
            PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == EXIT_CODE_NH


def test_pathactioncli_error_between_2_successful_files(allowed_dirs: AllowedPaths):
    """Test CLI exit code when processing multiple files with an error."""
    argv = [
        sys.argv[0],
        str(QA_BASEDIR.joinpath("case1", "file.nh")),
        str(QA_BASEDIR.joinpath("case1", "file2.nh")),
    ]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exitinfo:
            # Test success
            PathActionCli(limit_loop=1, limit_load_cfg=1, allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == EXIT_CODE_NH
