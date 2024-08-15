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

from setuptools import find_packages, setup

setup(
    name="pathaction",
    version="0.9.5",
    packages=find_packages(),
    setup_requires=[
        "pytest",
        "pytest-cov",
    ],
    install_requires=[
        "colorama",
        "jinja2",
        # "schema==v0.7.5",
        "schema",
        "PyYAML",
        "setproctitle",
    ],
    entry_points={
        "console_scripts": [
            "pathaction=pathaction.__init__:command_line_interface",
        ],
    },
)
