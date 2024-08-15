#!/usr/bin/env python
"""Test the class AllowedPaths()"""

import os
import tempfile
from pathlib import Path

import yaml
from pathaction.allowed_paths import AllowedPaths

QA_BASEDIR = Path("./tests/pathactioncfg_cases")


def test_allowed_paths_repr():
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    assert str(QA_BASEDIR.resolve()) in str(allowed_paths)


def test_allowed_paths_add_and_get_all():
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR, permanent=False)
    assert allowed_paths.get_all() == {QA_BASEDIR.resolve()}

    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    assert allowed_paths._permanently_allowed == {QA_BASEDIR.resolve()}

    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=False)
    assert allowed_paths._temporarily_allowed == {QA_BASEDIR.resolve()}


def test_allowed_paths_remove():
    allowed_paths = AllowedPaths()

    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.remove(QA_BASEDIR)

    allowed_paths.add(QA_BASEDIR, permanent=False)
    allowed_paths.remove(QA_BASEDIR)

    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)
    assert allowed_paths.get_all() == {QA_BASEDIR.resolve() / "case1"}


def test_allowed_paths_dump_and_load_yaml_from_string():
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    allowed_paths2 = AllowedPaths()
    allowed_paths2.load_yaml_from_string(allowed_paths.dump_to_yaml())

    assert allowed_paths._permanently_allowed == \
        allowed_paths2._permanently_allowed
    assert allowed_paths2._temporarily_allowed == set()


def test_allowed_paths_save_and_load_yaml_from_file():
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    tmp_path = None
    try:
        _, tmp_path = tempfile.mkstemp(prefix="pathaction", suffix=".test")

        allowed_paths2 = AllowedPaths()
        allowed_paths.save_to_yaml(tmp_path)
        allowed_paths2.load_from_yaml(tmp_path)
    finally:
        if tmp_path:
            os.remove(tmp_path)

        assert allowed_paths._permanently_allowed == \
            allowed_paths2._permanently_allowed
        assert allowed_paths2._temporarily_allowed == set()


def test_allowed_paths_is_allowed():
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    assert allowed_paths.is_allowed(QA_BASEDIR / "case1")
    assert allowed_paths.is_allowed(QA_BASEDIR.joinpath("case1", "subfile"))

    assert not allowed_paths.is_allowed(QA_BASEDIR / "case2")
    assert not allowed_paths.is_allowed(QA_BASEDIR.parent)
