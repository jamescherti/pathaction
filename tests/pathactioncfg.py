#!/usr/bin/env python
"""Test the class PathActionCfg()"""

import os
import shlex
import shutil
import subprocess
import tempfile
from pathlib import Path

import pytest

from pathaction.exceptions import PathActionError
from pathaction.pathactioncfg import PathActionCfg

QA_BASEDIR = Path("./tests/pathactioncfg_cases")


def test_pathactioncfg_cwd_in_cwd():
    source_code = QA_BASEDIR.joinpath("case1", "file3.nh")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert os.path.basename(actioncommand["cwd"]) == "test_cwd"
    assert os.path.basename(os.path.dirname(actioncommand["cwd"])) == "case1"


def test_pathactioncfg_jinja_render():
    # FILE: file.py
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))

    # var: file
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ file }}", cwd="/") == \
        str(source_code.absolute())

    # var: pathsep (type: string)
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ pathsep }}", cwd="/") == \
        os.path.sep

    # var: pathsep (type: list)
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render(["{{ pathsep }}"], cwd="/") == \
        [os.path.sep]

    # var: pathsep (type: list)
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render(
        {"{{ pathsep }}": "{{ pathsep }}"}, cwd="/"
    ) == {"{{ pathsep }}": os.path.sep}

    # var: cwd
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render("{{ cwd }}", cwd="/") == "/"

    # var: cwd (2)
    # pylint: disable=protected-access
    assert pathactioncfg._jinja2_render(["{{ cwd }}"], cwd="/") == ["/"]

    # method: shebang
    # shebang
    assert pathactioncfg._jinja2_render("{{ file | shebang }}", cwd="/") \
        == "/usr/bin/env python"

    # method: quote (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render("{{ \"te'st\" | quote }}", cwd="/") \
        == shlex.quote(string)

    # method: quote (int)
    assert pathactioncfg._jinja2_render("{{ 1024 | quote }}", cwd="/") \
        == shlex.quote(str(1024))

    # method: quote (float)
    assert pathactioncfg._jinja2_render("{{ 1024.123 | quote }}", cwd="/") \
        == shlex.quote(str(1024.123))

    # method: quote list (string)
    string = r"te'st"
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[0] }}""",
        cwd="/") == shlex.quote(string)

    # method: quote list (number)
    string = r"""te'st"""
    assert pathactioncfg._jinja2_render(
        r"""{{ (["te'st", 255] | quote)[1] }}""",
        cwd="/") == shlex.quote(str(255))

    # method: basename
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | basename }}",
        cwd="/"
    ) == os.path.basename(r"/path/to/file.txt")

    # startswith(string)
    assert pathactioncfg._jinja2_render(
        "{{ 'true' if ('/path/to/file.txt' | startswith('/path')) else 'false' }}",
        cwd="/") == "true"

    # endsswith(string)
    assert pathactioncfg._jinja2_render(
        "{{ 'true' if ('/path/to/file.txt' | endswith('/file.txt')) else 'false' }}",
        cwd="/") == "true"

    # method: dirname
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | dirname }}",
        cwd="/"
    ) == os.path.dirname(r"/path/to/file.txt")

    assert pathactioncfg._jinja2_render(
        "{{ file | relpath }}",
        cwd="/"
    ) == os.path.relpath(source_code)

    # method: abspath
    assert pathactioncfg._jinja2_render(
        "{{ '/path/to/file.txt' | abspath }}",
        cwd="/"
    ) == os.path.abspath(r"/path/to/file.txt")

    # method: joinpath
    assert pathactioncfg._jinja2_render(
        "{{ ['/path', 'to', 'file.txt'] | joinpath }}",
        cwd="/"
    ) == os.path.join("/path", "to", "file.txt")

    # method: joincmd
    assert pathactioncfg._jinja2_render(
        "{{ ['cp', '/file', '/file2'] | joincmd }}",
        cwd="/"
    ) == subprocess.list2cmdline(["cp", "/file", "/file2"])

    # method: splitcmd
    assert pathactioncfg._jinja2_render(
        "{{ 'cp /file /file2' | splitcmd }}",
        cwd="/"
    ) == str(["cp", "/file", "/file2"])

    # method: expanduser
    assert pathactioncfg._jinja2_render(
        "{{ '~/file' | expanduser }}",
        cwd="/"
    ) == os.path.expanduser("~/file")

    # method: expandvars
    if "TEST" not in os.environ:
        os.environ["TEST"] = "TEST RESULT"
    assert pathactioncfg._jinja2_render(
        "{{ '$TEST' | expandvars }}",
        cwd="/"
    ) == os.path.expandvars("$TEST")

    # method: file_dirname
    assert os.path.basename(pathactioncfg._jinja2_render(
        "{{ file | file_only_dirname }}",
        cwd="/",
    )) == "case1"

    # method: file_dirname
    assert os.path.basename(pathactioncfg._jinja2_render(
        "{{ file | dirname | file_only_dirname }}",
        cwd="/",
    )) == "case1"


def test_pathactioncfg_directory_load_all_cfg():
    source_code = QA_BASEDIR.joinpath("case1")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    assert pathactioncfg.loaded_yaml_path == \
        [str(QA_BASEDIR.joinpath("case1", ".pathaction.yaml").resolve())]


def test_pathactioncfg_cwd_in_path_match():
    source_code = QA_BASEDIR.joinpath("case1", "file4.bash")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert os.path.basename(os.path.dirname(
        str(actioncommand["path_match"]))
    ) == "case1"


def test_pathactioncfg_reset():
    source_code = QA_BASEDIR.joinpath("case1", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.reset()
    assert pathactioncfg.env == os.environ
    assert pathactioncfg.loaded_yaml_path == []
    assert pathactioncfg.cfg == {
        "options": PathActionCfg.default_options,
        "vars": {},
        "actions": {}
    }


def test_pathactioncfg_test_case_schema_error():
    source_code = QA_BASEDIR.joinpath("case2_schema_error", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_more_than_one_cfg():
    source_code = QA_BASEDIR.joinpath("case3_two_cfg_files", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_shell_does_not_exist():
    source_code = QA_BASEDIR.joinpath("case4_shell", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_yaml_syntax():
    source_code = QA_BASEDIR.joinpath("case5_yaml_syntax", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_invalid_regex():
    source_code = QA_BASEDIR.joinpath("case6_invalid_regex", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_test_case_mimetype():
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ['false is good']


def test_pathactioncfg_test_case_mimetype_regex():
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ['false is good']


def test_pathactioncfg_test_case_mimetype_match():
    source_code = QA_BASEDIR.joinpath("case7_mimetype", "file.txt")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == ['false this is a text file']


def test_pathactioncfg_test_case_mimetype_empty_file():
    source_code = QA_BASEDIR.joinpath("case10_mimetype_empty", "empty")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert (actioncommand["list_commands"] ==
            ['true there is no mimetype'])


def test_pathactioncfg_test_case_conflict_command_list_commands():
    source_code = QA_BASEDIR.joinpath(
        "case8_conflict_list_commands_command", "file.txt")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    with pytest.raises(PathActionError):
        pathactioncfg.load_all_cfg(limit=1)


def test_pathactioncfg_path_match_cwd():
    """Test jinja2 variables in patterns."""
    source_code = QA_BASEDIR.joinpath("case9_path_match_cwd", "file.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    # print(pathactioncfg.cfg)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand is not None
    assert actioncommand["command"] == "true"


def test_pathactioncfg_options_jinja2():
    source_code = QA_BASEDIR.joinpath("case11_options_jinja2", "file4.bash")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    options = pathactioncfg.cfg["options"]
    assert options["shell_path"] == shutil.which("sh")


def test_pathactioncfg_file_does_not_have_to_exist():
    source_code = QA_BASEDIR.joinpath("case1", "doesnotexist.py")
    pathactioncfg = PathActionCfg(source_code=str(source_code))


def test_pathactioncfg_test_case_matches():
    # source_code = QA_BASEDIR.joinpath("case1", "file.doesnotexist")
    # with pytest.raises(PathActionError):
    #     pathactioncfg = PathActionCfg(source_code=str(source_code))

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

    assert actioncommand == {"shell": True,
                             "list_commands": ["true lynx /dev/null"],
                             "path_match": ['*.html', '*.htm'],
                             "tags": "main",
                             "timeout": 60,
                             "comment": "This is a comment"}

    # Test: success / regex
    source_code = QA_BASEDIR.joinpath("case1", "file.sh")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")
    assert actioncommand["list_commands"] == [
        ['/usr/bin/env', 'sh', 'file.sh']]
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
    assert actioncommand["path_cfg"].endswith(os.sep + ".pathaction.yaml") \
        is True

    assert pathactioncfg.debug is True
    assert pathactioncfg.verbose is True

    assert pathactioncfg.load_cfg(  # it sould be ignored
        str(QA_BASEDIR.joinpath("case1", ".pathaction.yaml"))
    ) is False


def test_pathactioncfg_stdout_stderr():
    source_code = QA_BASEDIR.joinpath("case12_stdout_stderr", "stdout_stderr")
    pathactioncfg = PathActionCfg(source_code=str(source_code))
    pathactioncfg.load_all_cfg(limit=1)
    actioncommand = pathactioncfg.find_command("main")

    # 2 different stdout and stderr
    for delete_file in [False, True]:
        tmp_stdout = None
        tmp_stderr = None
        try:
            _, tmp_stdout = tempfile.mkstemp(prefix="pathaction",
                                             suffix=".test")
            actioncommand["stdout"] = tmp_stdout

            _, tmp_stderr = tempfile.mkstemp(prefix="pathaction",
                                             suffix=".test")
            actioncommand["stderr"] = tmp_stderr

            if delete_file:
                os.remove(tmp_stdout)
                os.remove(tmp_stderr)

            assert actioncommand.run("/bin/sh")

            with open(actioncommand["stdout"], "r",
                      encoding="utf-8") as fhandler:
                line = fhandler.readline().strip()
                assert line == "stdout_test"

            with open(actioncommand["stderr"], "r",
                      encoding="utf-8") as fhandler:
                line = fhandler.readline().strip()
                assert line == "stderr_test"
        finally:
            if tmp_stdout:
                os.remove(tmp_stdout)

            if tmp_stderr:
                os.remove(tmp_stderr)

    # Same stdout and stderr
    for delete_file in [False, True]:
        tmp_stdout = None
        try:
            _, tmp_stdout = tempfile.mkstemp(
                prefix="pathaction", suffix=".test")
            if delete_file:
                os.remove(tmp_stdout)
            actioncommand["stdout"] = tmp_stdout
            actioncommand["stderr"] = tmp_stdout

            assert actioncommand.run("/bin/sh")

            with open(actioncommand["stdout"], "r",
                      encoding="utf-8") as fhandler:
                line = fhandler.read().splitlines()
                assert line == ["stdout_test", "stderr_test"]
        finally:
            if tmp_stdout:
                os.remove(tmp_stdout)
