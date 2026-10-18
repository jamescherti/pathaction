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
"""Test the class Util()."""

import importlib.util
import os
import tempfile
import unittest.mock
from pathlib import Path

import pytest

from pathaction.exceptions import PathActionError
from pathaction.util import Util

HAS_COLORAMA: bool = importlib.util.find_spec("colorama") is not None


def test_util_which():
    """Test Util.which()."""
    with pytest.raises(PathActionError):
        Util.which("does_not_exist")

    assert Util.which("/bin/sh") == "/bin/sh"

    assert Util.which("sh", env_path="/bin") == "/bin/sh"

    with pytest.raises(PathActionError):
        del os.environ["PATH"]
        Util.which("sh")

    assert Util.which("./sh", cwd="/bin", env_path="") == "/bin/sh"

    with pytest.raises(PathActionError):
        Path(Util.which("./bin", cwd="/", env_path=""))

    with pytest.raises(PathActionError):
        Path(Util.which("bin", cwd="/", env_path="/"))

    with pytest.raises(PathActionError):
        Util.which("sh", cwd="/bin", env_path="")

    cwd = Path.cwd()
    os.chdir("/bin")
    new_cwd = Path.cwd()
    assert Util.which("./sh", env_path="") == str(new_cwd / "sh")
    os.chdir(cwd)


def test_util_color() -> None:
    """Test Util.color()."""
    Util.IS_A_TTY = True

    expected_color_string: str = "\x1b[32mTest\x1b[0m" if HAS_COLORAMA else "Test"
    assert Util.color(color=Util.COLOR_SUCCESS, string="Test") == expected_color_string

    Util.IS_A_TTY = False
    assert Util.color(color=Util.COLOR_SUCCESS, string="Test") == "Test"


def test_util_pcolor():
    """Test Util.pcolor()."""
    Util.IS_A_TTY = False
    with Path(os.devnull).open("w", encoding="utf-8") as devnull:
        assert (
            Util.pcolor(
                color=Util.COLOR_SUCCESS, string="Test", prefix="PREFIX ", file=devnull
            )
            == "PREFIX Test"
        )


def test_util_file_ends_with():
    """Test Util.file_ends_with()."""
    tmp_path = None
    try:
        _, tmp_path = tempfile.mkstemp(prefix="prefix", suffix=".yaml")
        tmpdir = Path(tmp_path).parent
        tmpname = Path(tmp_path).name[0:-5]
        assert Util.file_ends_with(
            path_prefix=tmpdir.joinpath(tmpname), path_suffixes=[".yaml", ".yml"]
        ) == [str(tmpdir.joinpath(tmpname + ".yaml"))]
    finally:
        if tmp_path:
            Path(tmp_path).unlink()


def test_util_read_shebang():
    """Test Util.read_shebang()."""
    tmp_path = None
    try:
        _, tmp_path = tempfile.mkstemp(prefix="test_read_shebang", suffix=".sh")
        # There is NO shebang
        with Path(tmp_path).open("w", encoding="utf-8") as fhandler:
            fhandler.write("echo 'Hello world'")
        with pytest.raises(PathActionError):
            Util.read_shebang(tmp_path)

        # There is a shebang
        with Path(tmp_path).open("w", encoding="utf-8") as fhandler:
            fhandler.write("#!/usr/bin/env /bin/test" + os.linesep)
            fhandler.write("echo 'Hello world'")
        assert Util.read_shebang(tmp_path) == "/usr/bin/env /bin/test"
    finally:
        if tmp_path:
            Path(tmp_path).unlink()


def test_util_ask_question():
    """Test Util.ask_question()."""
    with unittest.mock.patch("builtins.input", return_value="y"):
        assert (
            Util.ask_question(
                question="Question? ", answers=["y", "n"], timeout=1, empty_stdin=False
            )
            == "y"
        )

    with unittest.mock.patch("builtins.input", return_value="n"):
        assert (
            Util.ask_question(
                question="Question? ", answers=["a", "n"], empty_stdin=False
            )
            == "n"
        )


def test_util_home_to_tilde():
    """Test Util.home_to_tilde()."""
    assert Util.home_to_tilde(str(Path("~/test").expanduser())) == "~/test"


def test_util_which_invalid_cwd(tmp_path: Path):
    """Test Util.which() when cwd does not exist or is not a directory."""
    with pytest.raises(PathActionError):
        Util.which("sh", cwd=str(tmp_path / "non_existent_dir"))

    file_path = tmp_path / "some_file"
    file_path.write_text("", encoding="utf-8")
    with pytest.raises(PathActionError):
        Util.which("sh", cwd=str(file_path))


def test_util_read_shebang_missing_file(tmp_path: Path):
    """Test Util.read_shebang() when the file does not exist."""
    with pytest.raises(PathActionError):
        Util.read_shebang(str(tmp_path / "does_not_exist.sh"))


def test_util_ask_question_invalid_entry_hook():
    """Test Util.ask_question() invoking hook_invalid_entry on invalid input."""
    hook_calls = []
    with unittest.mock.patch("builtins.input", side_effect=["invalid", "y"]):
        answer = Util.ask_question(
            question="Question? ",
            answers=["y", "n"],
            hook_invalid_entry=hook_calls.append,
            empty_stdin=False,
        )
    assert answer == "y"
    assert len(hook_calls) == 1


def test_util_home_to_tilde_edge_cases():
    """Test Util.home_to_tilde() with exact home path and non-home path."""
    assert Util.home_to_tilde(str(Path("~").expanduser())) == "~"
    assert Util.home_to_tilde("/tmp/other_path") == "/tmp/other_path"
