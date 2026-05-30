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

from pathlib import Path

from setuptools import find_packages, setup

setup(
    name="pathaction",
    version="1.0.1",
    packages=find_packages(),
    description=("A universal Makefile for any file in the filesystem: "
                 "Rule-driven commands for any file or directory"),
    long_description=((Path(__file__).parent.resolve().joinpath("README.md"))
                      .read_text(encoding="utf-8")),
    long_description_content_type="text/markdown",
    url="https://github.com/jamescherti/pathaction",
    author="James Cherti",
    setup_requires=[
        "pytest",
        "pytest-cov",
    ],
    install_requires=[
        "jinja2",
        "schema",
        "PyYAML",
    ],
    extras_require={
        "colors": ["colorama"],
        "proctitle": ["setproctitle"],
    },
    python_requires=">=3.6, <4",
    classifiers=[
        "Development Status :: 5 - Production/Stable",
        "Programming Language :: Python :: 3",
        "License :: OSI Approved :: GNU General Public License (GPL)",
        "License :: OSI Approved :: GNU General Public License v3 (GPLv3)",
        "Operating System :: OS Independent",
        "Intended Audience :: Developers",
        "Topic :: Software Development :: Build Tools",
        "Topic :: Utilities",
        "Topic :: Software Development :: Libraries :: Python Modules",
        "Topic :: System :: Systems Administration",
        "Topic :: System :: Filesystems",
        "Topic :: System :: Software Distribution",
        "Environment :: Console",
        "Operating System :: POSIX :: Linux",
        "Operating System :: POSIX :: Other",
    ],
    entry_points={
        "console_scripts": [
            "pathaction=pathaction.__init__:command_line_interface",
        ],
    },
)
