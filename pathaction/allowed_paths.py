#!/usr/bin/env python
#
# Copyright (C) 2021-2024 James Cherti
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
"""Manage permissions to allow execution only from specific paths."""

from pathlib import Path
from pprint import pformat
from typing import Dict, List, Set, Union

import yaml


class AllowedPaths:
    def __init__(self):
        self._temporarily_allowed = set()
        self._permanently_allowed = set()

    def reset(self):
        self._temporarily_allowed = set()
        self._permanently_allowed = set()

    def add(self, path: Union[str, Path], permanent: bool):
        """Add a path to the list of allowed paths.

        Args:
            path: The path to be added.
            permanent: True to add the path permanently.
        """
        path = Path(path).resolve()
        if permanent:
            self._permanently_allowed.add(path)
            self._temporarily_allowed.discard(path)
        else:
            self._temporarily_allowed.add(path)
            self._permanently_allowed.discard(path)

    def remove(self, path: Union[str, Path]):
        """Remove a path from the list of allowed paths.

        Args:
            path: The path to be removed.
        """
        path = Path(path).resolve()
        self._permanently_allowed.discard(path)
        self._temporarily_allowed.discard(path)

    def get_all(self) -> Set[Path]:
        """Return all paths (permanent and temporary)"""
        return set(self._temporarily_allowed | self._permanently_allowed)

    def __iter__(self):
        return iter(self.get_all())

    def is_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed, including subdirectories and files.

        Args:
            path: The path to be checked.

        Returns: True if the path is allowed, False otherwise.
        """
        rpath = Path(path).resolve()
        return any(rpath.is_relative_to(allowed_path)  # type: ignore
                   for allowed_path in self)

    def load_from_yaml(self, path: Union[str, Path]):
        """Load the list of allowed paths from a YAML file.

        Args:
            path: The path to the YAML file containing allowed paths.
        """
        with open(path, "r", encoding="utf-8") as fhandler:
            self.load_yaml_from_string(fhandler)

    def load_yaml_from_string(self, stream):
        """Load from a string that contains YAML data."""
        content = yaml.safe_load(stream)
        self._permanently_allowed = \
            set(map(Path, content["permanently_allowed"]))

    def save_to_yaml(self, path: Union[str, Path]):
        """Save the list of allowed paths to a YAML file.

        Args:
            path: The path to the YAML file where allowed paths will be saved.
        """
        file_path = Path(path)
        with open(file_path, "w", encoding="utf-8") as fhandler:
            yaml.dump(self._gen_saveable_data(),
                      fhandler,
                      default_flow_style=False)

    def dump_to_yaml(self) -> str:
        """Dump the list of allowed paths to a YAML string.

        Returns: The YAML representation of allowed paths.
        """
        return str(yaml.dump(self._gen_saveable_data(),
                             default_flow_style=False))

    def _gen_saveable_data(self) -> Dict[str, List[str]]:
        return {
            "permanently_allowed": [str(path)
                                    for path in self._permanently_allowed],
        }

    def __repr__(self) -> str:
        """Provide a string representation of the object.

        Returns: str: A string representation of the object.
        """
        return (
            "Temporary:\n"
            + pformat([str(path) for path in self._temporarily_allowed])
            + "\n\nPermanent:\n"
            + pformat([str(path) for path in self._permanently_allowed])
        )
