# Pathaction | A universal Makefile for your entire filesystem: Run rule-driven commands on any file or directory
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

The `pathaction` tool is a flexible command-line utility for running commands on files and directories. Just pass a file path as an argument, and it handles the rest, whether you're working with code, media, or configurations.

Think of `pathaction` like a Makefile for your entire filesystem. It uses a `.pathaction.yaml` file to figure out which command to run, and you can even use Jinja2 templating to make those commands dynamic. You can also use tags to define multiple actions for the exact same file type, like setting up one tag to run a script, and another to debug it.

This tool is for software developers who manage multiple projects across diverse ecosystems and want to eliminate the cognitive load of switching between different build tools, environment configurations, and deployment methods. Just run one single command on any file and trust that it gets handled correctly.

If this tool helps your workflow, please show your support by **⭐ starring pathaction on GitHub** to help more software developers discover its benefits.

### Example

You can execute a file with the following commands:
```
pathaction -t main file.py

```

Or:
```
pathaction -t edit another-file.jpg

```

The `-t` option specifies the tag, allowing you to apply a tagged rule.

Here is an example of what a `.pathaction.yaml` rule-set file looks like:

```yaml
---
actions:
  - path_match: "*.py"
    tags: main
    command:
      - "python"
      - "{{ file }}"

  - path_match: "*.jpg"
    tags:
      - edit
      - show
    command: "gimp {{ file|quote }}"

```

There are many ways to match paths, including using regex. See below for more details.

## Requirements

- Python

## Editor Plugins

- **Emacs**: [pathaction.el](https://github.com/jamescherti/pathaction.el)
- **Vim**: [vim-pathaction](https://github.com/jamescherti/vim-pathaction)
- Other editors: Contributions are welcome.

## Installation

To install *pathaction*, run:
```
sudo pip install pathaction

```

## Usage

### Allow a directory

By default, `pathaction` does not read rule-set files such as `.pathaction.yaml` from arbitrary directories. The target directory must be explicitly permitted.

For example, to allow Pathaction to load `.pathaction.yaml` rules from `~/projects` and its subdirectories, run the following command:

```
pathaction --allow-dir ~/projects

```

### Rule-set files: `.pathaction.yaml`

The `pathaction` command-line tool uses regular expressions or filename pattern matching found in the rule-set file named `.pathaction.yaml` to associate commands with file types.

For instance, consider the following command:
```
pathaction -t main ~/projects/project-name/sub-project/file.py

```

The command above will load the `.pathaction.yaml` file not only from the directory where `file.py` is located but also from its parent directories. This loading behavior is similar to that of a `.gitignore` file. The rule sets from all these `.pathaction.yaml` files are combined. In case of conflicting rules or configurations, priority is given to the rule set that is located in the directory closest to the specified file or directory passed as a parameter to the `pathaction` command.

Jinja2 templating can be used to dynamically replace parts of the commands defined in the rule-set file with information about the file being executed, such as its filename and path, among other details (more on this below). In the command `"python {{ file|quote }}"`, the placeholder `{{ file|quote }}` will be dynamically substituted with the path to the source code passed as a parameter to the `pathaction` command-line tool.

Each rule defined in the rule set file `.pathaction.yaml` must include at least:

* The matching rule (e.g., a file name pattern like `*.py` or a regex `.*py$`).
* The command or a shell command (the command and its arguments can be templated with Jinja2).

### Example 1

This is what the rule-set file `.pathaction.yaml` contains:

```yaml
---
actions:
  # *.py files
  - path_match: "*.py"
    tags: main
    command:
      - "python"
      - "{{ file }}"

  # *.sh files
  - path_match: "*.sh"
    tags:
      - main
    command: "bash {{ file|quote }}"

  - path_match: "*.sh"
    tags: install
    command: "cp {{ file|quote }} ~/.local/bin/"

```

Consider the following command:

```sh
pathaction source_code.py

```

The command above will:

1. Load the `source_code.py` file.
2. Attempt to locate `.pathaction.yaml` or `.pathaction.yml` in the directory where the source code is located or in its parent directories. The search for `.pathaction.yaml` follows the same approach as `git` uses to find `.gitignore` in the current and parent directories.
3. Execute the command defined in `.pathaction.yaml` (e.g., pathaction will execute the command `python {{ file }}` on all `*.py` files).

### Example 2

Here is another example of a rule-set file located at `~/.pathaction.yaml`:

```yaml
---

options:
  shell: /bin/bash
  verbose: false
  debug: false
  confirm_after_timeout: 120

actions:
  # A shell is used to run the following command:
  - path_match: "*.py"
    path_match_exclude: "*/not_this_one.py"    # optional
    tags:
      - main
    shell: true
    command: "python {{ file|quote }}"

  # The command is executed without a shell when shell=false
  - path_regex: '^.*ends_with_string$'
    regex_path_exclude: '^.*not_this_one$'  # optional
    tags: main
    cwd: "{{ file|dirname }}"               # optional
    shell: false                            # optional
    command:
      - "python"
      - "{{ file }}"

```

## Jinja2 Variables and Filters

### Jinja2 Variables

| Variable       | Description
|----------------|---------------------------------------------------
| {{ file }}     | Replaced with the full path to the source code.
| {{ cwd }}      | Refers to the current working directory.
| {{ env }}      | Represents the operating system environment variables (dict).
| {{ pathsep }}  | Denotes the path separator

### Jinja2 Filters

| Filter         | Description
|----------------|---------------------------------------------------
| quote          | Equivalent to the Python method `shlex.quote`
| basename       | Equivalent to the Python method `os.path.basename`
| dirname        | Equivalent to the Python method `os.path.dirname`
| realpath       | Equivalent to the Python method `os.path.realpath`
| abspath        | Equivalent to the Python method `os.path.abspath`
| joinpath       | Equivalent to the Python method `os.path.join`
| joincmd        | Equivalent to the Python method `os.subprocess.list2cmdline`
| splitcmd       | Equivalent to the Python method `shlex.split`
| expanduser     | Equivalent to the Python method `os.path.expanduser`
| expandvars     | Equivalent to the Python method `os.path.expandvars`
| shebang        | Loads the shebang from a file (e.g. Loads the first line from a Python file `#!/usr/bin/env python`)
| shebang_list   | Returns the shebang as a list (e.g. ["/usr/bin/env", "bash"])
| shebang_quote  | Returns the shebang as a quoted string (e.g. `"/usr/bin/env '/usr/bin/command name'"`)
| which          | Locates a command (raises an error if the command is not found)

## Frequently Asked Questions

### Does pathaction walk the filesystem from the current directory to the top in search of .pathaction.yaml ruleset files?

Pathaction walks from the directory containing the file passed to it and merges `.pathaction.yaml` rules from all allowed parent directories.

There is a security measure by default: loading rules is allowed only in directories that have been explicitly permitted using `pathaction --allow-dir ~/dir/projects/`, which enables access to `~/dir/projects/` and all its subdirectories. If the entire home directory is allowed with `pathaction --allow-dir ~/`, rules can be loaded from any directory within the home directory.

### What are the differences between make and pathaction?

The `make` tool centers on targets and dependency tracking, making it good for compiling software based on file timestamps. In contrast, the `pathaction` tool acts as a universal file execution router. Passing a file path directly to Pathaction determines the correct command to run based on defined file extensions or patterns.

While `make` relies on project-specific files with strict syntax, Pathaction uses YAML files that cascade hierarchically across your filesystem. Much like how Git handles ignore files, Pathaction loads and merges all `.pathaction.yaml` rule-set files found in parent directories. This allows you to define rules in your home directory that can be overridden by specific settings within individual project folders.

For example, a Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`, similar to how Git handles .gitignore files.

### What is the difference between Pathaction and a command such as `find | xargs`?

It is very different from `find | xargs`.

The `pathaction` tool functions like a customizable, developer-focused `xdg-open`. It acts as the intelligent router that receives each file path and automatically determines the correct command to execute based on your defined rules.

Just as `xdg-open` relies on rigid system MIME types to launch GUI applications, Pathaction uses your hierarchical `.pathaction.yaml` configurations and Jinja2 templating to dynamically run commands.

### How is `pathaction` different from a shebang?

Shebangs are fine for basic execution, but they have limitations that Pathaction was built to address.

A shebang only defines how to execute a script. It cannot tell your system how to lint, format, debug, or test files. With `pathaction`, you can use tags. Passing `pathaction -t run file.py` executes it, while passing `pathaction -t test file.py` can run it through pytest.

### How is `pathaction` different from `xdg-open`?

File associations such as `xdg-open` apply globally. Pathaction uses cascading YAML files similar to `.gitignore`. A Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`.

In addition to that, Pathaction uses Jinja2 templating, allowing you to dynamically build complex shell commands based on the file name, its parent directory, or environment variables.

### How does the author use pathaction?

The author's `.pathaction.yaml` rules function as a universal bridge across distinct software ecosystems.

* For Python, C, C++, and related languages, rules are defined to install dependencies, build projects, execute binaries, run test suites, and launch debuggers.
* For Ansible, rules automatically upload playbooks to remote servers, execute them, and validate their results.
* For Emacs, rules integrate file-based actions directly with editor workflows, enabling evaluation, compilation, or linting based on context.
* For Vim, rules provide similar editor integration, allowing files to trigger build, run, or formatting actions without manual command construction.

Pathaction operates as an IDE-like action layer for the filesystem. Instead of embedding logic inside each editor or build system, actions are described declaratively and applied uniformly across tools.

The primary advantage is cognitive simplicity. There is no need to memorize complex command-line flags or tool-specific invocation patterns. A file is passed to Pathaction with a semantic tag such as `main`, `install`, or `debug`, and the corresponding rule determines how the operation is executed.

## License

Copyright (c) 2021-2026 [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

## Links

- [pathaction @GitHub](https://github.com/jamescherti/pathaction)
- [pathaction @PyPI](https://pypi.org/project/pathaction/)

Plugins for editors:
- [pathaction.el](https://github.com/jamescherti/pathaction.el) (Emacs package): Executing the `pathaction` command-line tool directly from Emacs.
- [vim-pathaction](https://github.com/jamescherti/vim-pathaction) (Vim plugin): Executing the `pathaction` command-line tool directly from Vim.
