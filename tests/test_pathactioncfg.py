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

import os
import shutil
import subprocess
import sys
from pathlib import Path
from unittest.mock import patch

import pytest

from pathaction.exceptions import PathActionError
from pathaction.pathactioncfg import ActionCommand, PathActionCfg, platform_quote

QA_BASEDIR = Path(__file__).resolve().parent / "pathactioncfg_cases"


def test_pathactioncfg_cwd_in_cwd():
    """Test using the cwd variable inside the cwd option."""
    source_code = QA_BASEDIR.joinpath("case1", "file3.nh")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert Path(actioncommand["cwd"]).name == "test_cwd"
    assert Path(actioncommand["cwd"]).parent.name == "case1"


def test_pathactioncfg_jinja_render(monkeypatch: pytest.MonkeyPatch):
    """Test rendering Jinja2 templates and filters in PathActionCfg."""
    # FILE: file.py
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    anchor = str(Path.cwd().anchor)

    # var: file
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ file }}", cwd=anchor) == str(
        source_code.absolute()
    )

    # var: pathsep (type: string)
    assert pathactioncfg._jinja2_render("{{ pathsep }}", cwd=anchor) == os.path.sep

    # var: pathsep (type: list)
    assert pathactioncfg._jinja2_render(["{{ pathsep }}"], cwd=anchor) == [os.path.sep]

    # var: pathsep (type: list)
    assert pathactioncfg._jinja2_render(
        {"{{ pathsep }}": "{{ pathsep }}"}, cwd=anchor
    ) == {"{{ pathsep }}": os.path.sep}

    # var: cwd
    assert pathactioncfg._jinja2_render("{{ cwd }}", cwd=anchor) == anchor

    # var: cwd (2)
    assert pathactioncfg._jinja2_render(["{{ cwd }}"], cwd=anchor) == [anchor]

    # method: shebang
    assert (
        pathactioncfg._jinja2_render("{{ file | shebang }}", cwd=anchor)
        == "/usr/bin/env python"
    )

    # method: quote (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render(
        '{{ "te\'st" | quote }}', cwd=anchor
    ) == platform_quote(string)

    # method: quote (int)
    assert pathactioncfg._jinja2_render(
        "{{ 1024 | quote }}", cwd=anchor
    ) == platform_quote(str(1024))

    # method: quote (float)
    assert pathactioncfg._jinja2_render(
        "{{ 1024.123 | quote }}", cwd=anchor
    ) == platform_quote(str(1024.123))

    # method: quote list (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[0] }}""", cwd=anchor
    ) == platform_quote(string)

    # method: quote list (number)
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[1] }}""", cwd=anchor
    ) == platform_quote(str(255))

    # method: basename
    assert (
        pathactioncfg._jinja2_render("{{ '/path/to/file.txt' | basename }}", cwd=anchor)
        == Path(r"/path/to/file.txt").name
    )

    # startswith(string)
    assert (
        pathactioncfg._jinja2_render(
            "{{ 'true' if ('/path/to/file.txt' | startswith('/path')) else 'false' }}",
            cwd=anchor,
        )
        == "true"
    )

    # endsswith(string)
    assert (
        pathactioncfg._jinja2_render(
            "{{ 'true' if ('/path/to/file.txt' | endswith('/file.txt')) "
            "else 'false' }}",
            cwd=anchor,
        )
        == "true"
    )

    # method: dirname
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | dirname }}", cwd=anchor
    ) == str(Path(r"/path/to/file.txt").parent)

    assert pathactioncfg._jinja2_render(
        "{{ file | relpath }}", cwd=anchor
    ) == os.path.relpath(source_code)

    # method: abspath
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | abspath }}", cwd=anchor
    ) == str(Path(r"/path/to/file.txt").resolve())

    # method: joinpath
    assert pathactioncfg._jinja2_render(
        "{{ ['/path', 'to', 'file.txt'] | joinpath }}", cwd=anchor
    ) == str(Path("/path") / "to" / "file.txt")

    # method: joincmd
    assert pathactioncfg._jinja2_render(
        "{{ ['cp', '/file', '/file2'] | joincmd }}", cwd=anchor
    ) == subprocess.list2cmdline(["cp", "/file", "/file2"])

    # method: expanduser
    assert pathactioncfg._jinja2_render(
        "{{ '~/file' | expanduser }}", cwd=anchor
    ) == str(Path("~/file").expanduser())

    # method: expandvars
    if "TEST" not in os.environ:
        monkeypatch.setenv("TEST", "TEST RESULT")
    assert pathactioncfg._jinja2_render(
        "{{ '$TEST' | expandvars }}", cwd=anchor
    ) == os.path.expandvars("$TEST")

    # method: file_dirname
    assert (
        Path(
            str(
                pathactioncfg._jinja2_render(
                    "{{ file | file_only_dirname }}",
                    cwd=anchor,
                )
            )
        ).name
        == "case1"
    )

    # method: file_dirname
    assert (
        Path(
            str(
                pathactioncfg._jinja2_render(
                    "{{ file | dirname | file_only_dirname }}",
                    cwd=anchor,
                )
            )
        ).name
        == "case1"
    )


def test_pathactioncfg_directory_load_all_cfg():
    """Test loading configuration files when the target is a directory."""
    source_code = QA_BASEDIR.joinpath("case1")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    assert pathactioncfg.loaded_yaml_path == [
        str(QA_BASEDIR.joinpath("case1", ".pathaction.yaml").resolve())
    ]


def test_pathactioncfg_cwd_in_path_match():
    """Test using the cwd variable in path_match."""
    source_code = QA_BASEDIR.joinpath("case1", "file4.bash")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert Path(str(actioncommand["path_match"])).parent.name == "case1"


def test_pathactioncfg_reset():
    """Test resetting PathActionCfg state."""
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.reset()
    assert pathactioncfg.env == os.environ
    assert pathactioncfg.loaded_yaml_path == []
    assert pathactioncfg.cfg == {
        "options": PathActionCfg.default_options,
        "vars": {},
        "actions": [],
    }


def test_pathactioncfg_test_case_schema_error():
    """Test handling of schema errors in configuration files."""
    source_code = QA_BASEDIR.joinpath("case2_schema_error", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_more_than_one_cfg():
    """Test error raised when multiple config files exist in the same directory."""
    source_code = QA_BASEDIR.joinpath("case3_two_cfg_files", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_shell_does_not_exist():
    """Test error raised when the configured shell does not exist."""
    source_code = QA_BASEDIR.joinpath("case4_shell", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_yaml_syntax():
    """Test error raised on invalid YAML syntax."""
    source_code = QA_BASEDIR.joinpath("case5_yaml_syntax", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_invalid_regex():
    """Test error raised on invalid regular expressions."""
    source_code = QA_BASEDIR.joinpath("case6_invalid_regex", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_mimetype():
    """Test matching actions by file mimetype."""
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ["false is good"]


def test_pathactioncfg_test_case_mimetype_regex():
    """Test matching actions by mimetype regular expression."""
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ["false is good"]


def test_pathactioncfg_test_case_mimetype_match():
    """Test matching actions by mimetype glob pattern."""
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.txt")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ["false this is a text file"]


def test_pathactioncfg_test_case_mimetype_empty_file():
    """Test matching actions when the target file has no mimetype."""
    source_code = QA_BASEDIR.joinpath("case10_mimetype_empty", "empty")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ["true there is no mimetype"]


def test_pathactioncfg_test_case_conflict_command_list_commands():
    """Test error raised when both command and list_commands are specified."""
    source_code = QA_BASEDIR.joinpath(
        "case8_conflict_list_commands_command", "file.txt"
    )
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_path_match_cwd():
    """Test jinja2 variables in patterns."""
    source_code = QA_BASEDIR.joinpath("case9_path_match_cwd", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert actioncommand["command"] == "true"


def test_pathactioncfg_options_jinja2():
    """Test rendering Jinja2 templates in the options section."""
    source_code = QA_BASEDIR.joinpath("case11_options_jinja2", "file4.bash")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    options = pathactioncfg.cfg["options"]
    assert "sh" in options["shell_path"] or options["shell_path"]


def test_pathactioncfg_file_does_not_have_to_exist():
    """Test initializing PathActionCfg with a non-existent file."""
    source_code = QA_BASEDIR.joinpath("case1", "doesnotexist.py")
    PathActionCfg(source_code=str(source_code))


def test_pathactioncfg_test_case_matches():
    """Test matching actions against various path and regex rules."""
    source_code = QA_BASEDIR.joinpath("case1", "file.exists")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is None

    # Test: success / multiple path_match
    source_code = QA_BASEDIR.joinpath("case1", "file.htm")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    cwd = actioncommand["cwd"]
    path_cfg = actioncommand["path_cfg"]
    del actioncommand["cwd"]
    del actioncommand["path_cfg"]
    assert Path(cwd).parent.name == "case1"
    assert Path(path_cfg).parent.name == "case1"

    assert actioncommand == {
        "shell": True,
        "list_commands": ["true lynx /dev/null"],
        "path_match": ["*.html", "*.htm"],
        "tags": "main",
        "timeout": 60,
        "comment": "This is a comment",
    }

    # Test: success / regex
    source_code = QA_BASEDIR.joinpath("case1", "file.sh")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == [["/usr/bin/env", "sh", "file.sh"]]
    assert actioncommand["path_regex"] == [r".*\.sh"]

    # Test: success / path_match
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    with pytest.raises(PathActionError):
        # Find the action "not_found"
        actioncommand = pathactioncfg.find_command("not_found")

    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ["python file.py"]
    assert actioncommand["path_match"] == ["*.py"]
    assert actioncommand["path_cfg"].endswith(os.sep + ".pathaction.yaml") is True

    assert pathactioncfg.debug is True
    assert pathactioncfg.verbose is True

    assert (
        pathactioncfg.load_cfg(  # it sould be ignored
            str(QA_BASEDIR.joinpath("case1", ".pathaction.yaml"))
        )
        is False
    )


def test_pathactioncfg_stdout_stderr(tmp_path: Path):
    """Test redirecting stdout and stderr to files in ActionCommand."""
    source_code = QA_BASEDIR.joinpath("case12_stdout_stderr", "stdout_stderr")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None

    def mock_call(cmd, **kwargs):
        if kwargs.get("stdout"):
            kwargs["stdout"].write(b"stdout_test\n")
        if (kwargs.get("stderr") and kwargs["stderr"] != kwargs["stdout"]) or (
            kwargs.get("stderr") and kwargs["stderr"] == kwargs["stdout"]
        ):
            kwargs["stderr"].write(b"stderr_test\n")
        return 0

    with patch("subprocess.call", side_effect=mock_call):
        # 2 different stdout and stderr
        for use_same_file in [False, True]:
            tmp_stdout = tmp_path / f"stdout_test_{use_same_file}.txt"
            tmp_stderr = (
                tmp_path / f"stderr_test_{use_same_file}.txt"
                if not use_same_file
                else tmp_stdout
            )

            actioncommand["stdout"] = str(tmp_stdout)
            actioncommand["stderr"] = str(tmp_stderr)

            _, errno = actioncommand.run(sys.executable)
            assert errno == 0

            if not use_same_file:
                with tmp_stdout.open(encoding="utf-8") as fhandler:
                    assert fhandler.readline().strip() == "stdout_test"
                with tmp_stderr.open(encoding="utf-8") as fhandler:
                    assert fhandler.readline().strip() == "stderr_test"
            else:
                with tmp_stdout.open(encoding="utf-8") as fhandler:
                    assert fhandler.read().splitlines() == [
                        "stdout_test",
                        "stderr_test",
                    ]


def test_pathactioncfg_jinja_extra_filters():
    """Test shebang_list, shebang_quote, realpath, which, and quote errors."""
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    anchor = str(Path.cwd().anchor)

    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ file | shebang_list }}", cwd=anchor) == str(
        ["/usr/bin/env", "python"]
    )
    assert (
        pathactioncfg._jinja2_render("{{ file | shebang_quote }}", cwd=anchor)
        == "/usr/bin/env python"
    )
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | realpath }}", cwd=anchor
    ) == str(Path("/path/to/file.txt").resolve())

    executable = sys.executable.replace("\\", "\\\\")
    assert pathactioncfg._jinja2_render(
        "{{ '" + executable + "' | which }}", cwd=anchor
    ) == shutil.which(sys.executable)

    with pytest.raises(FileNotFoundError):
        pathactioncfg._jinja2_render("{{ 'non_existent_bin_xyz' | which }}", cwd=anchor)

    with pytest.raises(TypeError):
        pathactioncfg._jinja2_render("{{ 123 | which }}", cwd=anchor)

    with pytest.raises(TypeError):
        pathactioncfg._jinja2_render("{{ true | quote }}", cwd=anchor)

    assert pathactioncfg._jinja2_render("{{ [true] | quote }}", cwd=anchor) == "[True]"


def test_pathactioncfg_jinja_nested_structures():
    """Test _jinja2_render with nested lists, dicts, and non-string scalars."""
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    anchor = str(Path.cwd().anchor)

    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render(
        {"key": ["{{ cwd }}"], "num": 42}, cwd=anchor
    ) == {
        "key": [anchor],
        "num": 42,
    }
    assert pathactioncfg._jinja2_render([["{{ cwd }}"], 42], cwd=anchor) == [
        [anchor],
        42,
    ]
    assert pathactioncfg._jinja2_render(42, cwd=anchor) == 42


def test_pathactioncfg_exclude_rules():
    """Test action exclusion rules in find_command."""
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.cfg["actions"] = [
        pathactioncfg.cfg["actions"][0] if pathactioncfg.cfg["actions"] else None
    ]

    pathactioncfg.cfg["actions"] = [
        ActionCommand(
            path_cfg=str(QA_BASEDIR / "case1" / ".pathaction.yaml"),
            action_dict={
                "path_match": "*.py",
                "path_match_exclude": "*file.py",
                "command": "not_executed_mock",
                "cwd": "test_dir",
            },
        ),
        ActionCommand(
            path_cfg=str(QA_BASEDIR / "case1" / ".pathaction.yaml"),
            action_dict={
                "path_match": "*.py",
                "command": sys.executable,
                "cwd": "test_dir",
            },
        ),
    ]
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert actioncommand["command"] == sys.executable
    assert actioncommand["cwd"] == str(
        QA_BASEDIR.joinpath("case1", "test_dir").resolve()
    )


def test_pathactioncfg_option_last(tmp_path: Path):
    """Test the 'last' option discarding parent configurations."""
    parent_cfg = tmp_path / ".pathaction.yaml"
    parent_cfg.write_text(
        "vars:\n  parent_var: '1'\nactions:\n  - path_match: '*'\n    "
        "command: 'mock_cmd'\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    child_cfg = sub_dir / ".pathaction.yaml"
    child_cfg.write_text(
        "options:\n  last: true\nactions:\n  - path_match: '*'\n    "
        "command: 'mock_cmd'\n",
        encoding="utf-8",
    )

    pathactioncfg = PathActionCfg(source_code=str(sub_dir / "test.py"))
    loaded = pathactioncfg.load_all_cfg(limit=2)
    assert loaded == [str(child_cfg.resolve())]
    assert "parent_var" not in pathactioncfg.cfg["vars"]


@pytest.mark.skipif(sys.platform != "win32", reason="Requires Windows cmd.exe")
def test_windows_shell_builtin_pipe_and_redirection(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Verify variable expansion, built-ins, pipes, and shell redirection.

    :param tmp_path: Temporary test directory.
    :param monkeypatch: Environment modification fixture.
    """
    shell: str | None = shutil.which("cmd.exe")
    assert shell is not None, "cmd.exe is required for this integration test"

    monkeypatch.setenv("PATHACTION_TEST_VALUE", "PATHACTION_OK")
    output: Path = tmp_path / "shell output.txt"
    stderr: Path = tmp_path / "shell errors.txt"

    action: ActionCommand = ActionCommand(
        path_cfg=str(tmp_path / ".pathaction.yaml"),
        action_dict={
            "command": (
                "echo %PATHACTION_TEST_VALUE%"
                '|findstr PATHACTION_OK > "shell output.txt"'
            ),
            "shell": True,
            "cwd": str(tmp_path),
            "stderr": str(stderr),
        },
    )

    _, returncode = action.run(shell_path=shell, timeout=10)

    assert returncode == 0, stderr.read_bytes()
    assert output.is_file(), stderr.read_bytes()
    assert output.read_bytes().strip() == b"PATHACTION_OK"


def test_pathactioncfg_merge_parent_child_dirs(tmp_path: Path):
    """Test merging vars, options, and actions from parent and child directories."""
    # 1. Setup Parent Directory and Config
    parent_dir = tmp_path
    parent_cfg = parent_dir / ".pathaction.yaml"
    parent_cfg.write_text(
        "vars:\n"
        "  parent_var: 'parent_value'\n"
        "  shared_var: 'parent_value'\n"
        "options:\n"
        "  timeout: 42\n"
        "  verbose: false\n"
        "actions:\n"
        "  - path_match: '*'\n"
        "    tags: 'parent_tag'\n"
        "    command: 'parent_cmd'\n",
        encoding="utf-8",
    )

    # 2. Setup Child Directory and Config
    child_dir = parent_dir / "child"
    child_dir.mkdir()
    child_cfg = child_dir / ".pathaction.yaml"
    child_cfg.write_text(
        "vars:\n"
        "  child_var: 'child_value'\n"
        "  shared_var: 'child_value'\n"
        "options:\n"
        "  verbose: true\n"
        "actions:\n"
        "  - path_match: '*'\n"
        "    tags: 'child_tag'\n"
        "    command: 'child_cmd'\n",
        encoding="utf-8",
    )

    # 3. Target file inside the child directory
    target_file = child_dir / "test.py"
    target_file.touch()

    # 4. Load configuration
    pathactioncfg = PathActionCfg(source_code=str(target_file))
    loaded = pathactioncfg.load_all_cfg(limit=5)

    # Verify both configurations were loaded
    assert len(loaded) == 2
    assert str(parent_cfg.resolve()) in loaded
    assert str(child_cfg.resolve()) in loaded

    # 5. Verify Vars are merged (child overrides parent for shared keys)
    assert pathactioncfg.cfg["vars"]["parent_var"] == "parent_value"
    assert pathactioncfg.cfg["vars"]["child_var"] == "child_value"
    assert pathactioncfg.cfg["vars"]["shared_var"] == "child_value"

    # 6. Verify Options are merged (child overrides parent for shared keys)
    assert pathactioncfg.cfg["options"]["timeout"] == 42
    assert pathactioncfg.cfg["options"]["verbose"] is True

    # 7. Verify Actions are merged and accessible by their respective tags
    action_parent = pathactioncfg.find_command("parent_tag")
    assert action_parent is not None
    assert action_parent["command"] == "parent_cmd"

    action_child = pathactioncfg.find_command("child_tag")
    assert action_child is not None
    assert action_child["command"] == "child_cmd"
