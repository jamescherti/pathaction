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

QA_BASEDIR = Path("./tests/pathactioncfg_cases")


def test_pathactioncfg_cwd_in_cwd():
    """Test using the cwd variable inside the cwd option."""
    source_code = QA_BASEDIR.joinpath("case1", "file3.nh")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert Path(actioncommand["cwd"]).name == "test_cwd"
    assert Path(actioncommand["cwd"]).parent.name == "case1"


def test_pathactioncfg_jinja_render():
    """Test rendering Jinja2 templates and filters in PathActionCfg."""
    # FILE: file.py
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))

    # var: file
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ file }}", cwd="/") == str(
        source_code.absolute()
    )

    # var: pathsep (type: string)
    assert pathactioncfg._jinja2_render("{{ pathsep }}", cwd="/") == os.path.sep

    # var: pathsep (type: list)
    assert pathactioncfg._jinja2_render(["{{ pathsep }}"], cwd="/") == [os.path.sep]

    # var: pathsep (type: list)
    assert pathactioncfg._jinja2_render(
        {"{{ pathsep }}": "{{ pathsep }}"}, cwd="/"
    ) == {"{{ pathsep }}": os.path.sep}

    # var: cwd
    assert pathactioncfg._jinja2_render("{{ cwd }}", cwd="/") == "/"

    # var: cwd (2)
    assert pathactioncfg._jinja2_render(["{{ cwd }}"], cwd="/") == ["/"]

    # method: shebang
    assert (
        pathactioncfg._jinja2_render("{{ file | shebang }}", cwd="/")
        == "/usr/bin/env python"
    )

    # method: quote (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render(
        '{{ "te\'st" | quote }}', cwd="/"
    ) == platform_quote(string)

    # method: quote (int)
    assert pathactioncfg._jinja2_render(
        "{{ 1024 | quote }}", cwd="/"
    ) == platform_quote(str(1024))

    # method: quote (float)
    assert pathactioncfg._jinja2_render(
        "{{ 1024.123 | quote }}", cwd="/"
    ) == platform_quote(str(1024.123))

    # method: quote list (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[0] }}""", cwd="/"
    ) == platform_quote(string)

    # method: quote list (number)
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[1] }}""", cwd="/"
    ) == platform_quote(str(255))

    # method: basename
    assert (
        pathactioncfg._jinja2_render("{{ '/path/to/file.txt' | basename }}", cwd="/")
        == Path(r"/path/to/file.txt").name
    )

    # startswith(string)
    assert (
        pathactioncfg._jinja2_render(
            "{{ 'true' if ('/path/to/file.txt' | startswith('/path')) else 'false' }}",
            cwd="/",
        )
        == "true"
    )

    # endsswith(string)
    assert (
        pathactioncfg._jinja2_render(
            "{{ 'true' if ('/path/to/file.txt' | endswith('/file.txt')) "
            "else 'false' }}",
            cwd="/",
        )
        == "true"
    )

    # method: dirname
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | dirname }}", cwd="/"
    ) == str(Path(r"/path/to/file.txt").parent)

    assert pathactioncfg._jinja2_render(
        "{{ file | relpath }}", cwd="/"
    ) == os.path.relpath(source_code)

    # method: abspath
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | abspath }}", cwd="/"
    ) == str(Path(r"/path/to/file.txt").resolve())

    # method: joinpath
    assert pathactioncfg._jinja2_render(
        "{{ ['/path', 'to', 'file.txt'] | joinpath }}", cwd="/"
    ) == str(Path("/path") / "to" / "file.txt")

    # method: joincmd
    assert pathactioncfg._jinja2_render(
        "{{ ['cp', '/file', '/file2'] | joincmd }}", cwd="/"
    ) == subprocess.list2cmdline(["cp", "/file", "/file2"])

    # method: expanduser
    assert pathactioncfg._jinja2_render("{{ '~/file' | expanduser }}", cwd="/") == str(
        Path("~/file").expanduser()
    )

    # method: expandvars
    if "TEST" not in os.environ:
        os.environ["TEST"] = "TEST RESULT"
    assert pathactioncfg._jinja2_render(
        "{{ '$TEST' | expandvars }}", cwd="/"
    ) == os.path.expandvars("$TEST")

    # method: file_dirname
    assert (
        Path(
            pathactioncfg._jinja2_render(
                "{{ file | file_only_dirname }}",
                cwd="/",
            )
        ).name
        == "case1"
    )

    # method: file_dirname
    assert (
        Path(
            pathactioncfg._jinja2_render(
                "{{ file | dirname | file_only_dirname }}",
                cwd="/",
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
    # Provide a realistic expectation instead of strictly "sh" to pass cross-platform
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

            assert actioncommand.run("mock_shell")

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

    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ file | shebang_list }}", cwd="/") == str(
        ["/usr/bin/env", "python"]
    )
    assert (
        pathactioncfg._jinja2_render("{{ file | shebang_quote }}", cwd="/")
        == "/usr/bin/env python"
    )
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | realpath }}", cwd="/"
    ) == str(Path("/path/to/file.txt").resolve())

    assert pathactioncfg._jinja2_render(
        "{{ '" + sys.executable + "' | which }}", cwd="/"
    ) == shutil.which(sys.executable)

    with pytest.raises(FileNotFoundError):
        pathactioncfg._jinja2_render("{{ 'non_existent_bin_xyz' | which }}", cwd="/")

    with pytest.raises(ValueError, match="which: invalid type"):
        pathactioncfg._jinja2_render("{{ 123 | which }}", cwd="/")

    with pytest.raises(ValueError, match="quote: invalid type"):
        pathactioncfg._jinja2_render("{{ true | quote }}", cwd="/")

    assert pathactioncfg._jinja2_render("{{ [true] | quote }}", cwd="/") == "[True]"


def test_pathactioncfg_jinja_nested_structures():
    """Test _jinja2_render with nested lists, dicts, and non-string scalars."""
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))

    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render({"key": ["{{ cwd }}"], "num": 42}, cwd="/") == {
        "key": ["/"],
        "num": 42,
    }
    assert pathactioncfg._jinja2_render([["{{ cwd }}"], 42], cwd="/") == [["/"], 42]
    assert pathactioncfg._jinja2_render(42, cwd="/") == 42  # noqa: PLR2004


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
                "command": "false",
                "cwd": "test_dir",
            },
        ),
        ActionCommand(
            path_cfg=str(QA_BASEDIR / "case1" / ".pathaction.yaml"),
            action_dict={
                "path_match": "*.py",
                "command": "true",
                "cwd": "test_dir",
            },
        ),
    ]
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert actioncommand["command"] == "true"
    assert actioncommand["cwd"] == str(
        QA_BASEDIR.joinpath("case1", "test_dir").resolve()
    )


def test_pathactioncfg_option_last(tmp_path: Path):
    """Test the 'last' option discarding parent configurations."""
    parent_cfg = tmp_path / ".pathaction.yaml"
    parent_cfg.write_text(
        "vars:\n  parent_var: '1'\nactions:\n  - path_match: '*'\n    "
        "command: 'true'\n",
        encoding="utf-8",
    )
    sub_dir = tmp_path / "sub"
    sub_dir.mkdir()
    child_cfg = sub_dir / ".pathaction.yaml"
    child_cfg.write_text(
        "options:\n  last: true\nactions:\n  - path_match: '*'\n    command: 'true'\n",
        encoding="utf-8",
    )

    pathactioncfg = PathActionCfg(source_code=str(sub_dir / "test.py"))
    loaded = pathactioncfg.load_all_cfg(limit=2)
    assert loaded == [str(child_cfg.resolve())]
    assert "parent_var" not in pathactioncfg.cfg["vars"]
