#!/usr/bin/env python
"""Test the class Util()."""

import pwd
import os
from pathlib import Path
import tempfile
import unittest.mock

import pytest
from pathaction.exceptions import PathActionError
from pathaction.util import Util


def test_util_which():
    with pytest.raises(PathActionError):
        Util.which("does_not_exist")

    assert Util.which("/bin/sh") == Path("/bin/sh")

    assert Util.which("sh", env_path="/bin") == Path("/bin/sh")

    with pytest.raises(PathActionError):
        del os.environ["PATH"]
        Util.which("sh")

    assert Util.which("./sh", cwd="/bin", env_path="") == Path("/bin/sh")

    with pytest.raises(PathActionError):
        Path(Util.which("./bin", cwd="/", env_path=""))

    with pytest.raises(PathActionError):
        Path(Util.which("bin", cwd="/", env_path="/"))

    with pytest.raises(PathActionError):
        Util.which("sh", cwd="/bin", env_path="")

    cwd = os.getcwd()
    os.chdir("/bin")
    new_cwd = os.getcwd()
    assert Util.which("./sh", env_path="") == Path(new_cwd).joinpath("sh")
    os.chdir(cwd)


def test_util_color():
    Util.IS_A_TTY = True
    assert Util.color(color=Util.COLOR_SUCCESS,
                      string="Test") == '\x1b[32mTest\x1b[0m'

    Util.IS_A_TTY = False
    assert Util.color(color=Util.COLOR_SUCCESS, string="Test") == "Test"


def test_util_pcolor():
    Util.IS_A_TTY = False
    with open(os.devnull, "w", encoding="utf-8") as devnull:
        assert Util.pcolor(color=Util.COLOR_SUCCESS,
                           string="Test",
                           prefix="PREFIX ",
                           file=devnull) == "PREFIX Test"


def test_util_file_ends_with():
    tmp_path = None
    try:
        _, tmp_path = tempfile.mkstemp(prefix="prefix", suffix=".yaml")
        tmpdir = Path(tmp_path).parent
        tmpname = Path(tmp_path).name[0:-5]
        assert Util.file_ends_with(path_prefix=tmpdir.joinpath(tmpname),
                                   path_suffixes=[".yaml", ".yml"]) \
            == [str(tmpdir.joinpath(tmpname + ".yaml"))]
    finally:
        if tmp_path:
            os.remove(tmp_path)


def test_util_read_shebang():
    tmp_path = None
    try:
        _, tmp_path = tempfile.mkstemp(prefix="test_read_shebang",
                                       suffix=".sh")
        # There is NO shebang
        with open(tmp_path, "w", encoding="utf-8") as fhandler:
            fhandler.write("echo 'Hello world'")
        with pytest.raises(PathActionError):
            Util.read_shebang(tmp_path)

        # There is a shebang
        with open(tmp_path, "w", encoding="utf-8") as fhandler:
            fhandler.write("#!/usr/bin/env /bin/test" + os.linesep)
            fhandler.write("echo 'Hello world'")
        assert Util.read_shebang(tmp_path) == "/usr/bin/env /bin/test"
    finally:
        if tmp_path:
            os.remove(tmp_path)


def test_util_ask_question():
    with unittest.mock.patch('builtins.input', return_value='y'):
        assert Util.ask_question(question="Question? ",
                                 answers=["y", "n"],
                                 timeout=1,
                                 empty_stdin=False) == "y"

    with unittest.mock.patch('builtins.input', return_value='n'):
        assert Util.ask_question(question="Question? ",
                                 answers=["a", "n"],
                                 empty_stdin=False) == "n"


def test_util_home_to_tilde():
    assert Util.home_to_tilde(os.path.expanduser("~/test")) == "~/test"
