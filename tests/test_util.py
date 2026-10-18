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
"""Test the class Util()."""

import importlib.util
import os
import sys
from pathlib import Path

import pytest
from prompt_toolkit.application import create_app_session
from prompt_toolkit.input import create_pipe_input
from prompt_toolkit.output import DummyOutput

from pathaction.exceptions import PathActionError
from pathaction.util import Util

HAS_COLORAMA: bool = importlib.util.find_spec("colorama") is not None


def test_util_which(monkeypatch: pytest.MonkeyPatch):
    """Test Util.which()."""
    executable = sys.executable
    exec_name = Path(executable).name
    exec_dir = str(Path(executable).parent)

    with pytest.raises(PathActionError):
        Util.which("does_not_exist_ever_123")

    assert Util.which(executable) == executable
    assert Util.which(exec_name, env_path=exec_dir) == executable

    monkeypatch.delenv("PATH", raising=False)
    with pytest.raises(PathActionError):
        Util.which("does_not_exist_ever_123")

    assert Util.which(f".{os.sep}{exec_name}", cwd=exec_dir, env_path="") == executable

    with pytest.raises(PathActionError):
        Path(Util.which(f".{os.sep}{exec_name}", cwd="/", env_path=""))

    with pytest.raises(PathActionError):
        Path(Util.which(exec_name, cwd="/", env_path="/"))

    with pytest.raises(PathActionError):
        Util.which(exec_name, cwd="/", env_path="")

    monkeypatch.chdir(exec_dir)
    assert Util.which(f".{os.sep}{exec_name}", env_path="") == executable


def test_util_color(monkeypatch: pytest.MonkeyPatch) -> None:
    """Test Util.color()."""
    monkeypatch.setattr(Util, "IS_A_TTY", True)
    expected_color_string: str = "\x1b[32mTest\x1b[0m" if HAS_COLORAMA else "Test"
    assert Util.color(color=Util.COLOR_SUCCESS, string="Test") == expected_color_string

    monkeypatch.setattr(Util, "IS_A_TTY", False)
    assert Util.color(color=Util.COLOR_SUCCESS, string="Test") == "Test"


def test_util_pcolor(monkeypatch: pytest.MonkeyPatch):
    """Test Util.pcolor()."""
    monkeypatch.setattr(Util, "IS_A_TTY", False)
    with Path(os.devnull).open("w", encoding="utf-8") as devnull:
        assert (
            Util.pcolor(
                color=Util.COLOR_SUCCESS, string="Test", prefix="PREFIX ", file=devnull
            )
            == "PREFIX Test"
        )


def test_util_file_ends_with(tmp_path: Path):
    """Test Util.file_ends_with()."""
    yaml_file = tmp_path / "prefix.yaml"
    yaml_file.write_text("test", encoding="utf-8")
    assert Util.file_ends_with(str(tmp_path / "prefix"), [".yaml", ".yml"]) == [
        str(yaml_file)
    ]


def test_util_read_shebang(tmp_path: Path):
    """Test Util.read_shebang()."""
    sh_file = tmp_path / "test.sh"

    # There is NO shebang
    sh_file.write_text("echo 'Hello'", encoding="utf-8")
    with pytest.raises(PathActionError):
        Util.read_shebang(str(sh_file))

    # There is a shebang
    sh_file.write_text("#!/usr/bin/env /bin/test\necho 'Hello'", encoding="utf-8")
    assert Util.read_shebang(str(sh_file)) == "/usr/bin/env /bin/test"


def test_util_ask_question():
    """Test Util.ask_question()."""
    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        pipe_input.send_text("y\n")
        assert (
            Util.ask_question(
                question="Question? ", answers=["y", "n"], timeout=1, empty_stdin=False
            )
            == "y"
        )

    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        pipe_input.send_text("n\n")
        assert (
            Util.ask_question(
                question="Question? ", answers=["a", "n"], empty_stdin=True
            )
            == "n"
        )


def test_util_home_to_tilde():
    """Test Util.home_to_tilde()."""
    assert Util.home_to_tilde(str(Path("~/test").expanduser())) == f"~{os.sep}test"


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
    with (
        create_pipe_input() as pipe_input,
        create_app_session(input=pipe_input, output=DummyOutput()),
    ):
        pipe_input.send_text("invalid\ny\n")
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
