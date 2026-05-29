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
"""Manage permissions to allow execution only from specific paths."""

from __future__ import annotations

from pathlib import Path
from pprint import pformat
from typing import TextIO, Union

import yaml


class AllowedPaths:
    """Manage allowed execution paths."""

    def __init__(self) -> None:
        """Initialize AllowedPaths class."""
        self._temporarily_allowed: set[Path] = set()
        self._permanently_allowed: set[Path] = set()

    def reset(self) -> None:
        """Reset the allowed path lists."""
        self._temporarily_allowed = set()
        self._permanently_allowed = set()

    def add(self, path: Union[str, Path], permanent: bool) -> None:
        """Add a path to the list of allowed paths.

        Args:
            path: The path to be added.
            permanent: True to add the path permanently.
        """
        resolved_path = Path(path).resolve()
        if permanent:
            self._permanently_allowed.add(resolved_path)
            self._temporarily_allowed.discard(resolved_path)
        else:
            self._temporarily_allowed.add(resolved_path)
            self._permanently_allowed.discard(resolved_path)

    def remove(self, path: Union[str, Path]) -> None:
        """Remove a path from the list of allowed paths.

        Args:
            path: The path to be removed.
        """
        resolved_path = Path(path).resolve()
        self._permanently_allowed.discard(resolved_path)
        self._temporarily_allowed.discard(resolved_path)

    def get_all(self) -> set[Path]:
        """Return all permanent and temporary paths."""
        return set(self._temporarily_allowed | self._permanently_allowed)

    def __iter__(self):
        """Iterate over all allowed paths."""
        return iter(self.get_all())

    def is_allowed(self, path: Union[str, Path]) -> bool:
        """Check if a path is allowed, including subdirectories and files.

        Args:
            path: The path to be checked.

        Returns:
            True if the path is allowed, False otherwise.
        """
        rpath = Path(path).resolve()
        return any(rpath.is_relative_to(allowed_path)  # type: ignore
                   for allowed_path in self)

    def load_from_yaml(self, path: Union[str, Path]) -> None:
        """Load the list of allowed paths from a YAML file.

        Args:
            path: The path to the YAML file containing allowed paths.
        """
        with open(Path(path), "r", encoding="utf-8") as fhandler:
            self.load_yaml_from_string(fhandler)

    def load_yaml_from_string(self, stream: TextIO) -> None:
        """Load from a string that contains YAML data."""
        content = yaml.safe_load(stream)
        self._permanently_allowed = \
            set(map(Path, content["permanently_allowed"]))

    def save_to_yaml(self, path: Union[str, Path]) -> None:
        """Save the list of allowed paths to a YAML file.

        Args:
            path: The path to the YAML file where allowed paths will be saved.
        """
        file_path = Path(path)
        with open(file_path, "w", encoding="utf-8") as fhandler:
            yaml.dump(self._gen_saveable_data(),
                      fhandler,
                      default_flow_style=False,
                      indent=2)

    def dump_to_yaml(self) -> str:
        """Dump the list of allowed paths to a YAML string.

        Returns:
            The YAML representation of allowed paths.
        """
        return str(yaml.dump(self._gen_saveable_data(),
                             default_flow_style=False,
                             indent=2))

    def _gen_saveable_data(self) -> dict[str, list[str]]:
        """Generate saveable data dictionary."""
        return {
            "permanently_allowed": [str(path)
                                    for path in self._permanently_allowed],
        }

    def __repr__(self) -> str:
        """Provide a string representation of the object.

        Returns:
            A string representation of the object.
        """
        return (
            "Temporary:\n"
            + pformat([str(path) for path in self._temporarily_allowed])
            + "\n\nPermanent:\n"
            + pformat([str(path) for path in self._permanently_allowed])
        )
