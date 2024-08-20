# Pathaction - Create .pathaction.yaml rule-set files for executing commands on any file
![License](https://img.shields.io/github/license/jamescherti/pathaction)

## Introduction

The `pathaction` command-line tool enables the execution of specific commands on targeted files or directories. Its key advantage lies in its flexibility, allowing users to handle various types of files (such as source code, text files, images, videos, configuration files, and more) simply by passing the file or directory as an argument to the `pathaction` tool. The tool uses a *.pathaction.yaml* rule-set file to determine which command to execute. Additionally, **Jinja2** templating can be employed in the rule-set file to further customize the commands.

You can execute a file with the following commands:
```
pathaction -t main file.py
```

Or:
```
pathaction -t edit another-file.jpg
```

(Note: The -t option specifies the tag, which allows you to apply a tagged rule.)

This is how a `.pathaction.yaml` looks like:
``` yaml
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

The `pathaction` tool can be viewed as a type of Makefile but is applicable to any file or directory within the filesystem hierarchy (e.g., it can execute any file such as independent scripts, Ansible playbooks, Python scripts, configuration files, etc.). It executes specific actions (i.e., commands) using tags that allow the user to specify different commands for the same type of file (e.g., a tag for execution, another tag for debugging, another tag for installation, etc.).

By using predefined rules in a user-created rule-set file (`.pathaction.yaml`), `pathaction` enables the creation of various tagged actions (e.g., Install, Run, Debug, Compile) customized for different file types (e.g., C/C++ files, Python files, Ruby files, ini files, images, etc.).

## Requirements

- Python
- pip

## Installation

Here is how to install `pathaction` using pip:
```
sudo pip install pathaction
```

The pip command above will install the `pathaction` executable in the directory `~/.local/bin/`.

## The .pathaction.yaml rule-set file

### Example 1

The `pathaction` command-line tool utilizes regular expressions or filename pattern matching found in the rule-set file named `.pathaction.yaml` to associate commands with file types.

First off, we are going to create and change the current directory to the project directory:
```
mkdir ~/project
cd ~/project
```

After that, we are going to permanently allow `pathaction` to read rule-set files (`.pathaction.yaml`) from the current directory using the command:
```
$ pathaction --allow-dir ~/project
```

This is a security measure to ensure that only the directories that are explicitly allowed could execute arbitrary commands using the `pathaction` tool.

For instance, consider the following command:
```
$ pathaction file.py
```

The command above will load the `.pathaction.yaml` file not only from the directory where `file.py` is located but also from its parent directories. This loading behavior is similar to that of a `.gitignore` file. The rule sets from all these `.pathaction.yaml` files are combined. In case of conflicting rules or configurations, the priority is given to the rule set that is located in the directory closest to the specified file or directory passed as a parameter to the `pathaction` command.

Jinja2 templating can be used to dynamically replace parts of the commands defined in the rule-set file with information about the file being executed, such as its filename and path, among other details (more on this below). In the command `"python {{ file|quote }}"`, the placeholder `{{ file|quote }}` will be dynamically substituted with the path to the source code passed as a parameter to the `pathaction` command-line tool.

Each rule defined in the rule set file `.pathaction.yaml` must include at least:
- The matching rule (e.g. a file name pattern like `*.py` or a regex `.*py$`).
- The command or a shell command (the command and its arguments can be templated with Jinja2).

### Example 2

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
$ pathaction source_code.py
```

The command above command will:
1. Load the `source_code.py` file,
2. Attempt to locate `.pathaction.yaml` or `.pathaction.yml` in the directory where the source code is located or in its parent directories. The search for `.pathaction.yaml` follows the same approach as `git` uses to find `.gitignore` in the current and parent directories.
3. Execute the command defined in `.pathaction.yaml` (e.g. PathAction will execute the command `python {{ file }}` on all `*.py` files).

### Example 3

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
    regex_path_exclude: '^.*not_this_one$'   # optional
    tags: main
    cwd: "{{ file|dirname }}"          # optional
    shell: false                       # optional
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
| {{ env }}      | Represents the operating system environment variables (dictionary).
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
| shebang_quote  | Returns the shebang as a quoted string (e.g. "/usr/bin/env '/usr/bin/command name'")
| which          | Locates a command (raises an error if the command is not found)

## Frequently Asked Questions

### How to Integrate the pathaction tool with your favorite editor (e.g. Vim)

It is recommended to configure your source code editor to execute source code with the `pathaction` command when pressing a specific key combination, such as `CTRL-E`.

### Integrate with Vim

If the preferred editor is Vim, the following line can be added to the
`~/.vimrc`:

```viml
nnoremap <silent> <C-e> :!pathaction "%"<CR>
```

## License

Copyright (c) 2021-2024 [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see <https://www.gnu.org/licenses/>.

## Links

- [pathaction @GitHub](https://github.com/jamescherti/pathaction)
- [pathaction @PyPI](https://pypi.org/project/pathaction/)
