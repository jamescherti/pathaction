# Pathaction - One command to run, compile, lint, deploy, or debug any file or directory
![Build Status](https://github.com/jamescherti/pathaction/actions/workflows/ci.yml/badge.svg)
[![License: GPL v3](https://img.shields.io/badge/License-GPLv3-blue.svg)](https://www.gnu.org/licenses/gpl-3.0)
[![PyPI Version](https://img.shields.io/pypi/v/pathaction.svg)](https://pypi.org/project/pathaction/)
![Linux](https://img.shields.io/badge/Linux-FCC624?logo=linux&logoColor=black)
![Windows](https://img.shields.io/badge/Windows-0078D6?logo=windows&logoColor=white)
![macOS](https://img.shields.io/badge/macOS-000000?logo=apple&logoColor=white)

- Author: James Cherti <[https://www.jamescherti.com/](https://www.jamescherti.com/)>
- License: GPL 3.0 or later

When jumping between different codebases and environments, it can be hard to remember the specific deployment methods, build tools, linters, and test runners for each file or project. The **[pathaction](https://github.com/jamescherti/pathaction)** tool is a command-line tool for running commands on files and directories.

Think of **pathaction** as the equivalent of your IDE's "Run" and "Debug" buttons, or a `Makefile` that works on individual files and directories. Unlike `make`, it selects commands by target path and tag rather than tracking build dependencies.

Pass any file or directory as an argument, and `pathaction` executes the right command based on a `.pathaction.yaml` configuration:

- Selects configured commands for paths such as source files, configuration files, media, and directories.
- Supports Jinja2 in `.pathaction.yaml` to construct commands from the target path and custom variables.
- Defines multiple actions for the same file type. Tags such as `main`, `debug`, and `lint` select configured commands.

This tool is built for software developers or system administrators who manage multiple files and projects across diverse environments.

Note: If this tool helps your workflow, please show your support by **⭐ starring pathaction on GitHub** and sharing it on your website, blog, Mastodon, Reddit, X, LinkedIn, or other social media platforms to help more Git users discover its benefits.

### Example

With the configuration below and an allowed target directory, execute a Python file with:

```sh
pathaction -t main file.py
```

Or:

```sh
pathaction -t edit another-file.jpg
```

The `-t` option selects a tag. The first matching action with that tag is executed.

Here is an example of what a `.pathaction.yaml` rule-set file looks like:

```yaml
---
# Variables
vars:
  image_editor: "gimp"

# Pathaction options
options:
  verbose: false

  # 'timeout': Prevent the command from hanging by killing it after 60 seconds
  # Set 'timeout' to 0 to disable it.
  timeout: 1800

actions:
  # Python files
  - path_match: "*.py"
    tags: main
    # This 'command:' is a list. We do not need to use '| quote' here.
    command:
      - "python"
      - "{{ file }}"

  # A specific project
  - path_match:
      # 'cwd' is the current directory containing .pathaction.yaml
      - "{{ cwd }}/my-project-name/*"
      - "{{ cwd }}/my-project-name"
    tags:
      - install
      - deploy
    command:
      - "{{ cwd }}/my-project-name/deploy-script.sh"
      - "--unattended"

  # Images
  - mimetype_match: "image/*"
    timeout: 0  # No timeout for the image editor
    tags:
      - edit
      - show
    # We need to use '| quote' here because 'command:' is a string.
    command: "{{ image_editor | quote }} {{ file | quote }}"
```

There are many ways to match paths, including using regular expressions and MIME types. See below for more details.

## Requirements

- Operating system: UNIX/Linux, Windows, Mac OS X
- Python 3
- Python dependencies: jinja2, prompt_toolkit, PyYAML, schema. (Optional: colorama, setproctitle)

## Editor Plugins

- **Emacs**: [pathaction.el](https://github.com/jamescherti/pathaction.el)
- **Vim**: [vim-pathaction](https://github.com/jamescherti/vim-pathaction)
- Other editors: Contributions are welcome.

## Installation

Install `pathaction` using [pip](https://pypi.org/project/pip/):

```sh
pip install --user pathaction
```

The executable is installed in the Python user installation scripts directory, commonly `~/.local/bin/` on Linux. The location varies by platform.

Required Python packages: jinja2, schema, PyYAML, and prompt_toolkit.

## Optional Dependencies

The `pathaction` CLI offers optional dependencies that extend its functionality. These extras can be installed according to environment requirements.

**Colored Terminal Output (`colors`)**: Installs `colorama` to provide consistent cross-platform ANSI color support. (Pathaction uses this package for its own terminal messages. It does not add color to subprocess output.)

```bash
pip install --user "pathaction[colors]"
```

**Custom Process Title (`proctitle`)**: Installs `setproctitle` to set the process title to the invoked executable basename, normally `pathaction`. This simplifies identification in system monitoring tools such as `top`, `htop`, and `ps`.

```bash
pip install --user "pathaction[proctitle]"
```

To install both extras at once, use a comma-separated list:

```bash
pip install --user "pathaction[colors,proctitle]"
```

## Getting Started

### 1. Authorize the target directory

The CLI requires the resolved target path to be inside an allowed directory. To permit targets in an existing projects directory and its descendants, run:

```sh
pathaction --allow-dir ~/projects
```

Permissions are stored in `~/.config/pathaction/permissions.yml`. The allow list checks targets, not individual configuration files; ancestor configurations outside the allowed subtree can still be loaded.

### 2. Create a rule-set file

Create `.pathaction.yaml` in the project root, for example `~/projects/my-app/.pathaction.yaml`:

```yaml
---
# .pathaction.yaml

vars:
  python_bin: "python"

options:
  # 'timeout': Prevent the command from hanging by killing it after 60 seconds
  timeout: 1800  # Set the timeout to 0 to disable it
  verbose: false

actions:
  - path_match: "*.py"
    tags: main
    command:
      - "{{ python_bin }}"
      - "{{ file }}"
```

### 3. Execute the file

Pass an existing Python file to `pathaction`. The `*.py` pattern matches its absolute path and selects the configured interpreter command.

```sh
pathaction ~/projects/my-app/dir1/dir2/file.py
```

The default tag is `main`, so the action above is selected.

The tag can also be specified explicitly:

```sh
pathaction -t main ~/projects/my-app/dir1/dir2/file.py
```

## Comprehensive Examples

The real value of `pathaction` comes from defining complex, multi-tag workflows across different file types. Here are detailed examples of how to configure `.pathaction.yaml` for various scenarios.

(The following configurations are independent examples. Required external programs must be installed and available in `PATH`, unless an executable path is configured. String-command examples assume POSIX parsing; argument lists with `shell: false` are preferred on Windows.)

### Example 1: Python and Bash Actions

Define separate tags for execution, testing, and type checking. The `test` action expects a Python file containing pytest tests.

```yaml
---
# .pathaction.yaml

vars:
  py_cmd: "python"

actions:
  # Execute the Python script
  - path_match: "*.py"
    tags: main
    command:
      - "{{ py_cmd }}"
      - "{{ file }}"

  # Run tests
  - path_match: "*.py"
    tags: test
    command: "pytest -v {{ file | quote }}"

  # Type checking
  - path_match: "*.py"
    tags: typecheck
    command: "mypy {{ file | quote }}"

  # Execute Bash shell scripts
  - path_match: "*.sh"
    tags:
      - main
    command: "bash {{ file | quote }}"
```

Select these actions with the `-t` flag:

```sh
pathaction -t typecheck src/utils.py
pathaction -t test src/test_utils.py
```

### Example 2: Managing Infrastructure with Ansible

Run an Ansible playbook whose filename ends in `playbook.yml`. The inventory path is relative to the action working directory, which defaults to the directory containing this configuration.

```yaml
---
# .pathaction.yaml

vars:
  inventory: "inventory.ini"

options:
  timeout: 300

actions:
  - path_match: "*playbook.yml"
    tags: main
    command: "ansible-playbook -i {{ inventory | quote }} {{ file | quote }}"
```

### Example 3: C++ Compilation and Execution

Compile a single, self-contained C++ source file and place the executable beside it. The `.bin` suffix is appended to the complete source path, preserving directory names that contain `.cpp`. Multi-file projects require an appropriate build command.

```yaml
---
# .pathaction.yaml

vars:
  compiler: "g++"
  flags: "-Wall -O2"

options:
  verbose: true

actions:
  # Compile C++ source code
  - path_match: "*.cpp"
    tags: ["compile", "build"]
    cwd: "{{ file|dirname }}"
    command: "{{ compiler | quote }} {{ flags }} {{ file | quote }} -o {{ (file ~ '.bin') | quote }}"

  # Compile and Run the compiled binary
  - path_match: "*.cpp"
    tags: main
    cwd: "{{ file|dirname }}"
    list_commands:
      - "{{ compiler | quote }} {{ flags }} {{ file | quote }} -o {{ (file ~ '.bin') | quote }}"
      - "{{ (file ~ '.bin') | quote }}"
```

### Example 4: Custom Variables and Output Redirection

Define reusable values in `vars`. The `stdout` and `stderr` fields accept filesystem paths, not shell arguments, so the `quote` filter must not be applied to them. The output files are overwritten for each command.

```yaml
---
# .pathaction.yaml

vars:
  deploy_env: "staging"

options:
  verbose: false

actions:
  - path_match: "*/deploy.sh"
    tags: main
    # Redirect stdout and stderr to deploy_stdout.log and deploy_stderr.log in cwd (the current directory).
    stdout: "{{ [cwd, 'deploy_stdout.log'] | joinpath }}"
    stderr: "{{ [cwd, 'deploy_stderr.log'] | joinpath }}"
    command: "bash {{ file | quote }} --env {{ deploy_env | quote }}"
```

### Example 5: Exclusion Rules

An exclusion prevents the current action from matching; later actions can still match the same target.

```yaml
---
# .pathaction.yaml

vars:
  py_env: "production"

options:
  timeout: 30

actions:
  - path_match: "*.py"
    path_match_exclude: "*/test_*.py"
    tags: main
    command: "python {{ file | quote }}"
```

### Example 6: Shell Features and Piping

Set `shell: true` to enable shell syntax. This POSIX example uses `/bin/sh`, a pipeline, and output redirection. `grep` returns status 1 when no lines match, which pathaction reports as a failed command. The output file is overwritten.

```yaml
---
# .pathaction.yaml

vars:
  grep_pattern: "error"

options:
  timeout: 10
  shell_path: /bin/sh

actions:
  - path_match: "*.log"
    tags: main
    shell: true
    command: "cat {{ file | quote }} | grep {{ grep_pattern | quote }} > {{ [cwd, 'log-summary.txt'] | joinpath | quote }}"
```

### Example 7: Advanced Matching (MIME Types and Regular Expressions)

Pathaction can match files based on their exact MIME type or evaluate regular expressions against the full path.

```yaml
---
# .pathaction.yaml

vars:
  image_viewer: "feh"

actions:
  - mimetype_match: "image/*"
    tags: main
    command:
      # Argument lists do not require the quote filter when shell is false
      - "{{ image_viewer }}"
      - "{{ file }}"

  - path_regex: "^.*/docs/.*\\.txt$"
    tags: main
    command: "cat {{ file | quote }}"
```

Note: MIME matchers use Python's `mimetypes.guess_type()` to infer a MIME type from the path, not the file contents. Results depend on the platform MIME database. Path regular expressions are searched against the absolute target path.

### Example 8: Action-Specific Overrides

An action-level `timeout` overrides the global timeout. An action-level `cwd` selects its working directory. This POSIX example runs pytest from the parent of the test file's directory.

```yaml
---
# .pathaction.yaml

vars:
  test_runner: "pytest"

options:
  timeout: 1

actions:
  - path_match: "*_e2e.py"
    tags: main
    # A timeout of 300 overrides the global timeout of 10.
    timeout: 300
    cwd: "{{ file|dirname }}/.."
    shell: true
    command: "echo \"Current dir: `pwd`\"; echo 'File:' {{ file | quote }}; echo Wait...; read v"
```

## Command-Line Arguments

The `pathaction` utility accepts several arguments to control execution behavior:

- `-t`, `--tag`: Execute the action associated with this tag (default is `main`).
- `-b`, `--confirm-before`: Request confirmation before execution. Once accepted, confirmation is disabled for the remainder of that CLI invocation.
- `-a`, `--confirm-after`: Ask the user if they want to execute the action again after it finishes (respects the `confirm_after_timeout` configuration).
- `-l`, `--list`: List `.pathaction.yaml` files that apply to the given target, nearest first, without executing an action.
- `-d`, `--allow-dir`: Permanently allow targets in the supplied directory and its descendants. This command authorizes the directory and exits without running an action.
- `--disallow-dir DIR`: Remove an explicitly stored directory from the allow list. This does not create a deny rule; a broader allowed ancestor still permits the target.
- `--list-allowed-dirs`: Print a list of all permanently allowed directories.

## Configuration Guide (.pathaction.yaml)

The rule-set files `pathaction.yaml` cascade hierarchically. When you execute a file, `pathaction` looks for `.pathaction.yaml` in the file's current directory, and then walks up the filesystem tree (parent directories) to find and merge all other `.pathaction.yaml` files. This loading behavior is similar to that of a `.gitignore` file. In case of conflicting rules or configurations, priority is given to the rule set that is located in the directory closest to the specified file.

Discovered files are loaded from ancestor to descendant. `vars` and `options` are shallow-merged by key, with nearer files overriding earlier values. Actions from nearer files are prepended, preserving their order within each file. Only the first action matching both the selected tag and an inclusion pattern runs. Failure of that command does not trigger a fallback action.

The allow list checks the resolved target path, not each discovered configuration file. Configuration files above the allowed directory can therefore be loaded. The `last` option resets inherited configuration but does not prevent ancestor files from being read.

Each usable action needs at least one inclusion matcher and either `command` or `list_commands`. The schema permits missing matchers, but such an action never matches.

### Match Methods

Actions can match files and directories using the following methods. Every match method has an `_exclude` variant. Each matcher accepts a string or list of strings. Any matching exclusion rejects that action; otherwise, any matching inclusion is sufficient. Multiple inclusion fields are alternatives, not combined requirements.

- **`path_match`**: Python `fnmatch.fnmatch` matching against the absolute path. Case sensitivity follows platform path normalization: usually case-sensitive on POSIX and case-insensitive on Windows. `*` can match directory separators. This is not filesystem glob expansion.
- **`path_match_case`**: Case-sensitive glob pattern matching.
- **`path_match_case_exclude`**: Case-sensitive glob pattern matching to explicitly ignore files.
- **`path_regex`**: Regular expression path matching (case-insensitive by default).
- **`path_regex_case`**: Case-sensitive regular expression matching.
- **`path_regex_case_exclude`**: Case-sensitive regular expression matching to explicitly ignore files.
- **`mimetype`**: Strict MIME type matching (e.g., `text/x-python`).
- **`mimetype_match`**: Glob pattern matching for MIME types (e.g., `text/*`).
- **`mimetype_regex`**: Regular expression matching for MIME types.

### Action Configuration

An action block can include the following optional attributes:

- **`tags`**: A string or list of strings indicating tag names. Defaults to `main`.
- **`comment`**: An informative string describing what the action does.
- **`timeout`**: Integer timeout in seconds for each command, overriding the global value. A value of `0` disables the timeout.
- **`cwd`**: Working directory for the command. Defaults to the directory containing the `pathaction.yaml` rule-set file. Relative values are resolved against that directory.
- **`stdout`**: Write command stdout to a file, truncating it before each command. Parent directories must already exist.
- **`stderr`**: Redirect command stderr with the same path and truncation rules as `stdout`.
- **`shell`**: Execute through the configured shell when `true`. Defaults to `false`. Use a command string for shell syntax. (`shell: false` are preferred on Windows.)
- **`command`**: One command, expressed as a string or argument list. With `shell: false`, strings are split with `shlex.split` (`posix=True` on POSIX, `False` on Windows); argument lists are passed directly without shell expansion.
- **`list_commands`**: A sequence of command strings or argument lists. Commands run sequentially in separate processes, stopping at the first nonzero exit status. Working-directory and shell state changes do not persist between commands. Mutually exclusive with `command`.

### Global Options

A top-level `options` block specifies execution defaults:

- **`shell_path`**: The absolute path to the shell executable used when `shell: true` (defaults to the user's login shell on POSIX and `%COMSPEC%`, or `cmd.exe` if unset, on Windows). Enable `shell: true` for shell features such as pipes, redirection, or built-in commands. Otherwise, prefer `shell: false` with an argument list, especially on Windows, to avoid command-string parsing issues.
- **`verbose`**: Enable verbose logging.
- **`debug`**: Enable debug mode.
- **`timeout`**: Default timeout in seconds for each command. A value of 0 disables it. On expiration, the directly launched process is killed.
- **`confirm_after_timeout`**: The timeout in seconds when waiting for user input during a `--confirm-after` prompt.
- **`last`**: If set to `true`, `pathaction` stops loading configurations from higher parent directories.

## Jinja2 Variables and Filters

### Jinja2 Variables

| Variable | Description |
| --- | --- |
| `{{ file }}` | Replaced with the full absolute path to the targeted file. |
| `{{ cwd }}` | Refers to the current working directory of the matched action. |
| `{{ env }}` | Represents the operating system environment variables (dictionary). |
| `{{ pathsep }}` | Denotes the path separator (e.g., `/` on Linux, `\` on Windows). |

### Jinja2 Filters

- **`quote`**: Escapes a string for use as a shell argument by wrapping it in single quotes and escaping internal single quotes. This prevents shell injection vulnerabilities. *Example:* `"/home/user/my file.txt" | quote` evaluates to `'/home/user/my file.txt'`.
- **`basename`**: Extracts the trailing filename or leaf component of a filesystem path. *Example:* `"/home/user/src/main.py" | basename` evaluates to `"main.py"`.
- **`dirname`**: Returns the parent directory portion of a filesystem path. *Example:* `"/home/user/src/main.py" | dirname` evaluates to `"/home/user/src"`.
- **`file_only_dirname`**: Returns the parent directory if the path is a file, or returns the path itself if it is already a directory.
- **`realpath`**: Resolves all symbolic links, relative segments (like `..`), and duplicate separators to return the canonical absolute path. *Example:* `"/usr/bin/../local/bin/python" | realpath` evaluates to `"/usr/local/bin/python"`.
- **`abspath`**: Converts a relative path into an absolute path by prefixing it with the current working directory. *Example:* `"src/main.py" | abspath` evaluates to `"/home/user/project/src/main.py"`.
- **`relpath`**: Computes the relative path between two directories.
- **`joinpath`**: Combines one or more path segments using the system filesystem separator. *Example:* `"/var/log" | joinpath("nginx", "error.log")` evaluates to `"/var/log/nginx/error.log"`.
- **`joincmd`**: Converts an array of command-line tokens into a single properly escaped shell command string. *Example:* `["grep", "-i", "error log"] | joincmd` evaluates to `'grep -i "error log"'`.
- **`splitcmd`**: Parses a raw shell command string into an array of distinct arguments while honoring quotation rules and escape sequences. *Example:* `"git commit -m 'initial release'" | splitcmd` evaluates to `["git", "commit", "-m", "initial release"]`.
- **`expanduser`**: Replaces a leading tilde notation (`~` or `~user`) with the absolute path of the corresponding user home directory. *Example:* `"~/config/tmux.conf" | expanduser` evaluates to `"/home/user/config/tmux.conf"`.
- **`expandvars`**: Substitutes environment variables within a string matching `$VARIABLE` or `${VARIABLE}` with their current active system values. *Example:* `"$HOME/.config" | expandvars` evaluates to `"/home/user/.config"`.
- **`shebang`**: Inspects a file and extracts the first line directly if it begins with an executable script prefix (`#!`). *Example:* `"/home/user/script.sh" | shebang` evaluates to `"#!/usr/bin/env bash"`.
- **`shebang_list`**: Extracts the shebang line from a file, discards the initial `#!` marker, and parses the remaining contents into a clean token array. *Example:* `"/home/user/script.sh" | shebang_list` evaluates to `["/usr/bin/env", "bash"]`.
- **`shebang_quote`**: Extracts the shebang line from a file, strips the `#!` marker, and returns the runtime interpreter directive as a safely balanced, shell-quoted string. *Example:* `"/home/user/script.sh" | shebang_quote` evaluates to `"/usr/bin/env bash"`.
- **`which`**: Searches the system environment variable `PATH` to locate the absolute path of an executable binary. Raises an error if the binary cannot be found. *Example:* `"emacs" | which` evaluates to `"/usr/bin/emacs"`.
- **`startswith`**: Evaluates to true if the string starts with the given prefix.
- **`endswith`**: Evaluates to true if the string ends with the given suffix.

## Frequently Asked Questions

### Does pathaction walk the filesystem from the current directory to the top in search of .pathaction.yaml ruleset files?

Pathaction walks from the directory containing the file passed to it and merges `.pathaction.yaml` rules from all allowed parent directories.

There is a security measure by default: loading rules is allowed only in directories that have been explicitly permitted using `pathaction --allow-dir ~/dir/projects/`, which enables access to `~/dir/projects/` and all its subdirectories. If the entire home directory is allowed with `pathaction --allow-dir ~/`, rules can be loaded from any directory within the home directory.

### .pathaction.yaml files cascade up the tree like .gitignore. If home and project .pathaction.yaml define the same tag, does the nearest .pathaction.yaml file override just that action or the whole rule for that file type?

The cascade behavior in pathaction merges `vars`, `options`, and `actions`.

When pathaction evaluates configuration files from your home directory down to your current working directory, it prepends local actions to the inherited list. This means local rules take precedence, but global rules for other file types remain active.

#### Example

For example, define parent configuration in the home directory `~/.pathaction.yaml`:

```yaml
# ~/.pathaction.yaml

vars:
  global_setting: "enabled"

options:
  timeout: 30
  verbose: false

actions:
  - tags: "main"
    path_match: "*.md"
    command: "glow {{ file | quote }}"

  - tags: "main"
    path_match: "*.py"
    command: "python {{ file | quote }}"
```

Then, create a local configuration in your project directory to change how Python files are handled:

```yaml
# ~/project/.pathaction.yaml
vars:
  local_setting: "enabled"

options:
  verbose: true

actions:
  - tags: "main"
    path_match: "*.py"
    command: "pytest {{ file | quote }}"
```

#### Resulting Behavior in the Project Directory

Here is what the configuration looks like internally after pathaction merges the two files:

```yaml
# Internal evaluated state for ~/project/
vars:
  global_setting: "enabled"
  local_setting: "enabled"

options:
  timeout: 30
  verbose: true

actions:
  # Local rules evaluate first
  - tags: "main"
    path_match: "*.py"
    command: "pytest {{ file | quote }}"

  # Inherited rules evaluate if local rules don't match
  - tags: "main"
    path_match: "*.md"
    command: "glow {{ file | quote }}"

  - tags: "main"
    path_match: "*.py"
    command: "python {{ file | quote }}" # Shadowed by the local rule above
```

- **Variables and options merge:** The active `vars` dictionary contains both `global_setting` and `local_setting`. The `options` dictionary updates `verbose` to `true` while retaining the inherited `timeout` value of `30`.
- **Actions merge (local priority):** The active `actions` list contains the local `pytest` command for `*.py` files and the inherited `glow` command for `*.md` files.
- Because the local `*.py` rule is evaluated first, it overrides the global `*.py` rule.

### This tool feels like "I couldn't remember the commands and did not want to read the README, so I built a new tool where I have to remember the commands"

The intent is the exact opposite.

The problem pathaction addresses is context switching. When you work across multiple ecosystems daily (such as Python, Node.js, Ansible, and Go), every project has its own specific way to run, build, test, or lint. You end up having to memorize many different toolchains or constantly check the README for every repository.

The goal of pathaction is to eliminate that mental overhead. You define the `.pathaction.yaml` configuration once. After that, you do not have to remember any of the underlying commands. You just run one unified command, or press a single hotkey in Emacs or Vim, and it executes the correct toolchain based on the exact file type or directory you are currently looking at.

It acts as a context-aware Makefile. You only ever have to interact with one interface, regardless of the language or framework you are working in at that moment.

### Why use pathaction when I can just run the specific target command directly?

If you are running a simple one-off command like `python script.py` in a terminal, typing the command directly is faster. That is not the problem `pathaction` solves.

The `pathaction` tool is an abstraction layer between your tools (editors, file managers, shell bindings) and the diverse environments on your filesystem:

- If you use an editor (e.g, Emacs or Vim), you want a single keybinding for "run", "test", "lint", or "deploy" on the current buffer. Without `pathaction`, you have to hardcode project-specific or language-specific runners inside your editor configuration. With `pathaction`, your editor just passes the current file path and a tag (e.g., `pathaction -t deploy <current-file>`), and the `.pathaction.yaml` dictates how that file is handled.
- The exact command you need often changes based on where the file lives. A `.py` file in `~/project_a` might need to run via `./.venv/bin/pytest`, while a `.py` file in `~/project_b` needs `docker exec -i container pytest`, and an Ansible `*playbook.yml` needs a specific `-i inventory.ini` flag. Because `.pathaction.yaml` files cascade up the directory tree like `.gitignore`, you define global defaults in `~/` and override them per project.
- Instead of typing or searching shell history for `g++ -Wall -O2 /path/to/file.cpp -o /path/to/file && /path/to/file` or remembering exact inventory paths and linter flags when jumping between ten different repositories, you define the `.pathaction.yaml` rule once in the directory and use the same interface everywhere.

It is the same reason software developers use `Makefile` targets instead of typing raw compiler and linker invocations every time, except `pathaction` operates on arbitrary file paths across the entire filesystem rather than static build targets in a single directory.

### What are the differences between make and pathaction?

The make tool centers on targets and dependency tracking, making it good for compiling software based on file timestamps. In contrast, the pathaction tool acts as a universal file execution router. Passing a file path directly to Pathaction determines the correct command to run based on defined file extensions or patterns.

While make relies on project-specific files with strict syntax, Pathaction uses YAML files that cascade hierarchically across your filesystem. Much like how Git handles ignore files, Pathaction loads and merges all `.pathaction.yaml` rule-set files found in parent directories. This allows you to define rules in your home directory that can be overridden by specific settings within individual project folders.

For example, a Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`, similar to how Git handles .gitignore files.

### What is the difference between Pathaction and a command such as `find | xargs`?

It is very different from `find | xargs`. The pathaction tool functions like a customizable, developer-focused xdg-open. It acts as the intelligent router that receives each file path and automatically determines the correct command to execute based on your defined rules. Just as xdg-open relies on rigid system MIME types to launch GUI applications, Pathaction uses your hierarchical `.pathaction.yaml` configurations and Jinja2 templating to dynamically run commands.

### How is pathaction different from a shebang?

Shebangs are fine for basic execution, but they have limitations that Pathaction was built to address.

A shebang only defines how to execute a script. It cannot tell your system how to lint, format, debug, or test files. With pathaction, you can use tags. Passing `pathaction -t main file.py` executes it, while passing `pathaction -t test file.py` can run it through pytest.

### How is pathaction different from xdg-open?

File associations such as xdg-open apply globally. Pathaction uses cascading YAML files similar to how Git handles `.gitignore` files. A Python script in `~/project_a` can be routed to a local virtual environment, while a Python script in `~/project_a/project_b` can trigger a Docker execution simply by defining different `.pathaction.yaml` files in those directories. Pathaction loads and merges all `.pathaction.yaml` ruleset files found in parent directories. This means that any rule in `~/project_a/project_b/.pathaction.yaml` that does not match a file falls back to the rules defined in `~/project_a/.pathaction.yaml`.

In addition to that, Pathaction uses Jinja2 templating, allowing you to dynamically build complex shell commands based on the file name, its parent directory, or environment variables.

### How does the author use pathaction?

The author's `.pathaction.yaml` rules function as a universal bridge across distinct software environments.

- For Python, Bash, C, C++, and related languages, rules are defined to install dependencies, build projects, execute binaries, run test suites, and launch debuggers.
- For Ansible, rules automatically upload playbooks to remote servers, execute them, and validate their results.
- For Emacs, rules integrate file-based actions directly with editor workflows, enabling evaluation, compilation, or linting based on context.
- For Vim, rules provide similar editor integration, allowing files to trigger build, run, or formatting actions without manual command construction.

Pathaction operates as an IDE-like action layer for the filesystem. Instead of embedding logic inside each editor or build system, actions are described declaratively and applied uniformly across tools.

The primary advantage is cognitive simplicity. There is no need to memorize complex command-line flags or tool-specific invocation patterns. A file is passed to Pathaction with a semantic tag such as `main`, `install`, or `debug`, and the corresponding rule determines how the operation is executed.

## License

Copyright (c) 2021-2026 [James Cherti](https://www.jamescherti.com)

This program is free software: you can redistribute it and/or modify it under the terms of the GNU General Public License as published by the Free Software Foundation, either version 3 of the License, or (at your option) any later version.

This program is distributed in the hope that it will be useful, but WITHOUT ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE. See the GNU General Public License for more details.

You should have received a copy of the GNU General Public License along with this program. If not, see [https://www.gnu.org/licenses/](https://www.gnu.org/licenses/).

## Links

- [pathaction @GitHub](https://github.com/jamescherti/pathaction)
- [pathaction @PyPI](https://pypi.org/project/pathaction/)

Plugins for editors:

- [pathaction.el](https://github.com/jamescherti/pathaction.el) (Emacs package): Executing the `pathaction` command-line tool directly from Emacs.
- [vim-pathaction](https://github.com/jamescherti/vim-pathaction) (Vim plugin): Executing the `pathaction` command-line tool directly from Vim.

Other projects by the same author:

- [git-rexec](https://github.com/jamescherti/git-rexec)
