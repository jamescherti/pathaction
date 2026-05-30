# Pathaction | A universal Makefile for any file in the filesystem: Rule-driven commands for any file or directory
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)

The `pathaction` tool is a flexible command-line utility for running commands on files and directories. Pass a file path as an argument, and the tool handles the rest, whether you are working with code, media, or configurations.

Think of `pathaction` like a Makefile for any file or directory in the filesystem. It uses a `.pathaction.yaml` file to determine which command to run, and you can use Jinja2 templating to make those commands dynamic. You can also use tags to define multiple actions for the exact same file type. For example, you can set up one tag to run a script, another to debug it, and a third to run a linter.

This tool is built for software engineers who manage multiple projects across diverse environments. It eliminates the cognitive load of switching between different build tools, environment configurations, and deployment methods. Run a single unified command on any file and trust that it gets handled correctly.

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

There are many ways to match paths, including using regular expressions and MIME types. See below for more details.

## Editor Plugins

- **Emacs**: [pathaction.el](https://github.com/jamescherti/pathaction.el)
- **Vim**: [vim-pathaction](https://github.com/jamescherti/vim-pathaction)
- Other editors: Contributions are welcome.

## Installation

Here is how to install `pathaction` using [pip](https://pypi.org/project/pip/):
```sh
pip install --user pathaction
```

The pip command above will install the `pathaction` executable in the directory `~/.local/bin/`.

(Python requirements: jinja2, schema, PyYAML.)

## Optional Dependencies

The `pathaction` CLI offers optional dependencies that extend its functionality. These extras can be installed according to environment requirements.

* **Colored Terminal Output (`colors`)**: Installs `colorama` to provide consistent cross-platform ANSI color support. This enhances the readability of standard output and error messages.

  ```bash
  pip install "pathaction[colors]"
  ```

* **Custom Process Title (`proctitle`)**: Installs `setproctitle` to rename the running process from `python` to `pathaction`. This simplifies identification in system monitoring tools such as `top`, `htop`, and `ps`.

  ```bash
  pip install "pathaction[proctitle]"
  ```

To install both extras at once, use a comma-separated list:

```bash
pip install "pathaction[colors,proctitle]"
```

## Getting Started

### 1. Authorize your working directory

By default, `pathaction` does not read rule-set files from arbitrary directories for security reasons. The allowed directories must be explicitly permitted. To allow `pathaction` to load rules from your projects folder and its subdirectories, run:

```sh
pathaction --allow-dir ~/projects
```

### 2. Create a rule-set file

Navigate to your project root (e.g., `~/projects/my-app/`) and create a `.pathaction.yaml` file. Here is a basic example to run Python files:

```yaml
---
actions:
  - path_match: "*.py"
    tags: main
    command:
      - "python"
      - "{{ file }}"
```

### 3. Execute the file

Now, instead of manually invoking the Python interpreter, you can pass the file directly to `pathaction`. It will read the rule, match the `.py` extension, and execute the command.

```sh
pathaction src/main.py

```

Because the default tag is `main`, `pathaction` automatically targets the block we just defined.

## Comprehensive Examples

The real value of `pathaction` comes from defining complex, multi-tag workflows across different file types. Here are detailed examples of how to configure `.pathaction.yaml` for various scenarios.

### Example 1: Full Python and Bash Workflow

Instead of memorizing different tools and their command-line arguments, you can define them as actions.

```yaml
---
actions:
  # Execute the Python script
  - path_match: "*.py"
    tags: main
    command:
      - "python"
      - "{{ file }}"

  # Run tests
  - path_match: "*.py"
    tags: test
    command: "pytest -v {{ file|quote }}"

  # Type checking
  - path_match: "*.py"
    tags: typecheck
    command: "mypy {{ file|quote }}"

  # Execute Bash shell scripts
  - path_match: "*.sh"
    tags:
      - main
    command: "bash {{ file|quote }}"
```

You can invoke these specific actions by passing the `-t` (tag) flag:

```sh
pathaction -t typecheck src/utils.py
pathaction -t test src/test_utils.py

```

### Example 2: Managing Infrastructure with Ansible

You can set up rules to apply Ansible playbooks directly.

```yaml
---
actions:
  - path_match: "*playbook.yml"
    tags: main
    command: "ansible-playbook -i inventory.ini {{ file|quote }}"

```

### Example 3: C/C++ Compilation and Execution

You can use `pathaction` to compile files on the fly and put the output binary in the correct directory.

```yaml
---
actions:
  # Compile C++ source code
  - path_match: "*.cpp"
    tags: build
    cwd: "{{ file|dirname }}"
    command: "g++ -Wall -O2 {{ file|quote }} -o {{ file|basename|replace('.cpp', '') }}"

  # Run the compiled binary
  - path_match: "*.cpp"
    tags: run
    cwd: "{{ file|dirname }}"
    command: "./{{ file|basename|replace('.cpp', '') }}"

```

## Command-Line Arguments

The `pathaction` utility accepts several arguments to control execution behavior:

* `-t`, `--tag`: Execute the action associated with this tag (default is `main`).
* `-b`, `--confirm-before`: Prompt for confirmation before executing the defined action.
* `-a`, `--confirm-after`: Ask the user if they want to execute the action again after it finishes (respects the `confirm_after_timeout` configuration).
* `-l`, `--list`: List all the `.pathaction.yaml` configuration files that apply to the given file path. Useful for debugging rule resolution.
* `-d`, `--allow-dir`: Permanently allow `pathaction` to execute rules from the provided directory and its subdirectories.
* `--disallow-dir`: Revoke access and remove a specific directory from your allowed list.
* `--list-allowed-dirs`: Print a list of all permanently allowed directories.

## Configuration Guide (`.pathaction.yaml`)

The rule-sets cascade hierarchically. When you execute a file, `pathaction` looks for `.pathaction.yaml` in the file's current directory, and then walks up the filesystem tree (parent directories) to find and merge all other `.pathaction.yaml` files. This loading behavior is similar to that of a `.gitignore` file. In case of conflicting rules or configurations, priority is given to the rule set that is located in the directory closest to the specified file.

Each rule defined in the rule-set file must include at least the matching rule and the command.

### Match Methods

You can target files using various matching strategies. Every match method also has a corresponding `_exclude` variant (e.g., `path_match_exclude`) to explicitly ignore files that would otherwise match.

* **`path_match`**: Standard glob pattern matching (e.g., `*.py`).
* **`path_match_case`**: Case-sensitive glob pattern matching.
* **`path_regex`**: Regular expression path matching (case-insensitive by default).
* **`path_regex_case`**: Case-sensitive regular expression matching.
* **`mimetype`**: Strict MIME type matching (e.g., `text/x-python`).
* **`mimetype_match`**: Glob pattern matching for MIME types (e.g., `text/*`).
* **`mimetype_regex`**: Regular expression matching for MIME types.

### Action Configuration

An action block can include the following optional attributes:

* **`tags`**: A string or list of strings indicating the tag names.
* **`comment`**: An informative string describing what the action does.
* **`timeout`**: An integer specifying the maximum execution time in seconds.
* **`cwd`**: The current working directory for the command.
* **`stdout`**: Redirect the standard output of the command to the specified file path.
* **`stderr`**: Redirect the standard error of the command to the specified file path. (If both `stdout` and `stderr` point to the exact same file path, they are combined).
* **`shell`**: Boolean indicating if the command should be executed within a shell environment.
* **`command`** / **`list_commands`**: The command string/array to execute. These two are mutually exclusive.

### Global Options

You can define an `options` block at the root of your `.pathaction.yaml` to specify execution defaults:

* **`shell_path`**: The absolute path to the shell executable used when `shell: true` (defaults to the user's login shell).
* **`verbose`**: Enable verbose logging.
* **`debug`**: Enable debug mode.
* **`timeout`**: A global timeout constraint in seconds.
* **`confirm_after_timeout`**: The timeout in seconds when waiting for user input during a `--confirm-after` prompt.
* **`last`**: If set to `true`, `pathaction` stops loading configurations from higher parent directories.

## Jinja2 Variables and Filters

### Jinja2 Variables

| Variable | Description |
| --- | --- |
| `{{ file }}` | Replaced with the full absolute path to the targeted file. |
| `{{ cwd }}` | Refers to the current working directory of the matched action. |
| `{{ env }}` | Represents the operating system environment variables (dictionary). |
| `{{ pathsep }}` | Denotes the path separator (e.g., `/` on Linux, `\` on Windows). |

### Jinja2 Filters

* **`quote`**: Escapes a string for use as a shell argument by wrapping it in single quotes and escaping internal single quotes. This prevents shell injection vulnerabilities. *Example:* `"/home/user/my file.txt" | quote` evaluates to `'/home/user/my file.txt'`.
* **`basename`**: Extracts the trailing filename or leaf component of a filesystem path. *Example:* `"/home/user/src/main.py" | basename` evaluates to `"main.py"`.
* **`dirname`**: Returns the parent directory portion of a filesystem path. *Example:* `"/home/user/src/main.py" | dirname` evaluates to `"/home/user/src"`.
* **`file_only_dirname`**: Returns the parent directory if the path is a file, or returns the path itself if it is already a directory.
* **`realpath`**: Resolves all symbolic links, relative segments (like `..`), and duplicate separators to return the canonical absolute path. *Example:* `"/usr/bin/../local/bin/python" | realpath` evaluates to `"/usr/local/bin/python"`.
* **`abspath`**: Converts a relative path into an absolute path by prefixing it with the current working directory. *Example:* `"src/main.py" | abspath` evaluates to `"/home/user/project/src/main.py"`.
* **`relpath`**: Computes the relative path between two directories.
* **`joinpath`**: Combines one or more path segments using the system filesystem separator. *Example:* `"/var/log" | joinpath("nginx", "error.log")` evaluates to `"/var/log/nginx/error.log"`.
* **`joincmd`**: Converts an array of command-line tokens into a single properly escaped shell command string. *Example:* `["grep", "-i", "error log"] | joincmd` evaluates to `'grep -i "error log"'`.
* **`splitcmd`**: Parses a raw shell command string into an array of distinct arguments while honoring quotation rules and escape sequences. *Example:* `"git commit -m 'initial release'" | splitcmd` evaluates to `["git", "commit", "-m", "initial release"]`.
* **`expanduser`**: Replaces a leading tilde notation (`~` or `~user`) with the absolute path of the corresponding user home directory. *Example:* `"~/config/tmux.conf" | expanduser` evaluates to `"/home/user/config/tmux.conf"`.
* **`expandvars`**: Substitutes environment variables within a string matching `$VARIABLE` or `${VARIABLE}` with their current active system values. *Example:* `"$HOME/.config" | expandvars` evaluates to `"/home/user/.config"`.
* **`shebang`**: Inspects a file and extracts the first line directly if it begins with an executable script prefix (`#!`). *Example:* `"/home/user/script.sh" | shebang` evaluates to `"#!/usr/bin/env bash"`.
* **`shebang_list`**: Extracts the shebang line from a file, discards the initial `#!` marker, and parses the remaining contents into a clean token array. *Example:* `"/home/user/script.sh" | shebang_list` evaluates to `["/usr/bin/env", "bash"]`.
* **`shebang_quote`**: Extracts the shebang line from a file, strips the `#!` marker, and returns the runtime interpreter directive as a safely balanced, shell-quoted string. *Example:* `"/home/user/script.sh" | shebang_quote` evaluates to `"/usr/bin/env bash"`.
* **`which`**: Searches the system environment variable `PATH` to locate the absolute path of an executable binary. Raises an error if the binary cannot be found. *Example:* `"emacs" | which` evaluates to `"/usr/bin/emacs"`.
* **`startswith`**: Evaluates to true if the string starts with the given prefix.
* **`endswith`**: Evaluates to true if the string ends with the given suffix.

## Frequently Asked Questions

### Does pathaction walk the filesystem from the current directory to the top in search of .pathaction.yaml ruleset files?

Pathaction walks from the directory containing the file passed to it and merges `.pathaction.yaml` rules from all allowed parent directories.

There is a security measure by default: loading rules is allowed only in directories that have been explicitly permitted using `pathaction --allow-dir ~/dir/projects/`, which enables access to `~/dir/projects/` and all its subdirectories. If the entire home directory is allowed with `pathaction --allow-dir ~/`, rules can be loaded from any directory within the home directory.

### What are the differences between make and pathaction?

The make tool centers on targets and dependency tracking, making it good for compiling software based on file timestamps. In contrast, the pathaction tool acts as a universal file execution router. Passing a file path directly to Pathaction determines the correct command to run based on defined file extensions or patterns.

While make relies on project-specific files with strict syntax, Pathaction uses YAML files that cascade hierarchically across your filesystem. Much like how Git handles ignore files, Pathaction loads and merges all `.pathaction.yaml` rule-set files found in parent directories. This allows you to define rules in your home directory that can be overridden by specific settings within individual project folders.

For example, a Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`, similar to how Git handles .gitignore files.

### What is the difference between Pathaction and a command such as `find | xargs`?

It is very different from `find | xargs`. The pathaction tool functions like a customizable, developer-focused xdg-open. It acts as the intelligent router that receives each file path and automatically determines the correct command to execute based on your defined rules. Just as xdg-open relies on rigid system MIME types to launch GUI applications, Pathaction uses your hierarchical `.pathaction.yaml` configurations and Jinja2 templating to dynamically run commands.

### How is pathaction different from a shebang?

Shebangs are fine for basic execution, but they have limitations that Pathaction was built to address.

A shebang only defines how to execute a script. It cannot tell your system how to lint, format, debug, or test files. With pathaction, you can use tags. Passing `pathaction -t run file.py` executes it, while passing `pathaction -t test file.py` can run it through pytest.

### How is pathaction different from xdg-open?

File associations such as xdg-open apply globally. Pathaction uses cascading YAML files similar to how Git handles `.gitignore` files. A Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`.

In addition to that, Pathaction uses Jinja2 templating, allowing you to dynamically build complex shell commands based on the file name, its parent directory, or environment variables.

### How does the author use pathaction?

The author's `.pathaction.yaml` rules function as a universal bridge across distinct software environments.

* For Python, Bash, C, C++, and related languages, rules are defined to install dependencies, build projects, execute binaries, run test suites, and launch debuggers.
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
