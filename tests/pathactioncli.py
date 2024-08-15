#!/usr/bin/env python
"""Test the class PathActionCfg()"""

import os
import sys
from pathlib import Path
from unittest.mock import patch

import pytest
from pathaction.allowed_paths import AllowedPaths
from pathaction.pathactioncli import PathActionCli

QA_BASEDIR = Path("./tests/pathactioncfg_cases")


@pytest.fixture()
def allowed_dirs():
    allow_dirs = AllowedPaths()
    allow_dirs.add(QA_BASEDIR, permanent=False)
    return allow_dirs


def test_pathactioncli_dir_not_allowed():
    allowed_dirs = AllowedPaths()
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.sh"))]
    with patch.object(sys, "argv", argv):
        # Test success
        with pytest.raises(SystemExit) as exitinfo:
            pathactioncli = PathActionCli(limit_loop=1,
                                            limit_load_cfg=1,
                                            allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == 1


def test_pathactioncli(allowed_dirs: AllowedPaths):
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.sh"))]
    with patch.object(sys, "argv", argv):
        # Test success
        with pytest.raises(SystemExit) as exitinfo:
            pathactioncli = PathActionCli(limit_loop=1,
                                            limit_load_cfg=1,
                                            allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == 64

        # Test Failure
        # pathactioncli = PathActionCli(limit_loop=1,
        #                                 limit_load_cfg=1,
        #                                 exit=False)
        # assert pathactioncli. == 64


def test_pathactioncli_error_between_2_success(allowed_dirs: AllowedPaths):
    argv = [sys.argv[0], str(QA_BASEDIR.joinpath("case1", "file.nh"))]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exitinfo:
            # Test success
            pathactioncli = PathActionCli(limit_loop=1,
                                            limit_load_cfg=1,
                                            allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == 111


def test_pathactioncli_error_between_2_successful_files(
        allowed_dirs: AllowedPaths):
    argv = [sys.argv[0],
            str(QA_BASEDIR.joinpath("case1", "file.nh")),
            str(QA_BASEDIR.joinpath("case1", "file2.nh"))]
    with patch.object(sys, "argv", argv):
        with pytest.raises(SystemExit) as exitinfo:
            # Test success
            pathactioncli = PathActionCli(limit_loop=1,
                                            limit_load_cfg=1,
                                            allowed_dirs=allowed_dirs)

        assert exitinfo.value.code == 111
