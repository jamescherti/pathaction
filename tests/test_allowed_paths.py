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
"""Test the class AllowedPaths()."""

from pathlib import Path

from pathaction.allowed_paths import AllowedPaths

QA_BASEDIR = Path("./tests/pathactioncfg_cases")


def test_allowed_paths_repr():
    """Test the string representation of AllowedPaths."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    assert str(QA_BASEDIR.resolve()) in str(allowed_paths).replace("\\\\", "\\")


def test_allowed_paths_add_and_get_all():
    """Test adding paths and retrieving all allowed paths."""
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
    """Test removing paths from AllowedPaths."""
    allowed_paths = AllowedPaths()

    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.remove(QA_BASEDIR)

    allowed_paths.add(QA_BASEDIR, permanent=False)
    allowed_paths.remove(QA_BASEDIR)

    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)
    assert allowed_paths.get_all() == {QA_BASEDIR.resolve() / "case1"}


def test_allowed_paths_dump_and_load_yaml_from_string():
    """Test dumping and loading allowed paths from a YAML string."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    allowed_paths2 = AllowedPaths()
    allowed_paths2.load_yaml_from_string(allowed_paths.dump_to_yaml())

    assert allowed_paths._permanently_allowed == allowed_paths2._permanently_allowed
    assert allowed_paths2._temporarily_allowed == set()


def test_allowed_paths_save_and_load_yaml_from_file(tmp_path: Path):
    """Test saving and loading allowed paths from a YAML file."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    yaml_file = tmp_path / "allowed.yaml"

    allowed_paths2 = AllowedPaths()
    allowed_paths.save_to_yaml(yaml_file)
    allowed_paths2.load_from_yaml(yaml_file)

    assert allowed_paths._permanently_allowed == allowed_paths2._permanently_allowed
    assert allowed_paths2._temporarily_allowed == set()


def test_allowed_paths_is_allowed():
    """Test checking whether a path is allowed."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)

    assert allowed_paths.is_allowed(QA_BASEDIR / "case1")
    assert allowed_paths.is_allowed(QA_BASEDIR.joinpath("case1", "subfile"))

    assert not allowed_paths.is_allowed(QA_BASEDIR / "case2")
    assert not allowed_paths.is_allowed(QA_BASEDIR.parent)


def test_allowed_paths_reset():
    """Test resetting permanent and temporary paths in AllowedPaths."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.add(QA_BASEDIR / "case1", permanent=False)
    allowed_paths.reset()
    assert allowed_paths.get_all() == set()


def test_allowed_paths_load_empty_or_invalid_yaml():
    """Test loading empty or malformed YAML strings in AllowedPaths."""
    allowed_paths = AllowedPaths()
    allowed_paths.add(QA_BASEDIR, permanent=True)

    allowed_paths.load_yaml_from_string("")
    assert allowed_paths.get_all() == set()

    allowed_paths.add(QA_BASEDIR, permanent=True)
    allowed_paths.load_yaml_from_string("permanently_allowed: not_a_list")
    assert allowed_paths.get_all() == set()
