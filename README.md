# plan-d

[![Ruff](https://img.shields.io/endpoint?url=https://raw.githubusercontent.com/astral-sh/ruff/main/assets/badge/v2.json)](https://github.com/astral-sh/ruff)
![PyPI - Version](https://img.shields.io/pypi/v/plan-d)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/plan-d)
![GitHub License](https://img.shields.io/github/license/zen-xu/plan-d)

Python Language's Another Nonpareil remote Debugger

## Table of Contents

- [plan-d](#plan-d)
  - [Table of Contents](#table-of-contents)
  - [Introduction](#introduction)
  - [Features](#features)
  - [Installation](#installation)
  - [Gallery](#gallery)
    - [Debugger commands](#debugger-commands)
    - [Print object info](#print-object-info)
    - [IPython magic func](#ipython-magic-func)
  - [Auto launch debugger when exception](#auto-launch-debugger-when-exception)
  - [FAQ](#faq)
    - [How to exit the debugger?](#how-to-exit-the-debugger)

## Introduction

`plan-d` is a remote debugger for Python, designed to provide an unparalleled debugging experience. It allows developers to debug Python applications running on remote servers seamlessly.

## Features

- ✨ Provide a more pretty printing using `rich`
- 🕹️ Remote debugging capabilities
- ⌨️ Code autocompletion
- 🔴 Breakpoint management
- 🔎 Variable inspection
- 🔄 Terminal size auto-adjustment
- 🪄 Support for IPython magic functions
- 🐍 Support for multiple Python versions

## Installation

To install `plan-d`, you can use pip:

```sh
pip install plan-d
```

## Gallery

On the server side, you can set a breakpoint with `plan_d.set_trace()`. When the server reaches the breakpoint, it will print the connection command.

<figure class="image">
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-connect.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">syntax highlight</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-highlight-output.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">support multiline</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-multilines.jpg">
</figure>

### Debugger commands

<figure class="image">
  <figcaption style="text-align: center;">(h)elp</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-cmd-h.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">(v)ars</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-cmd-vars.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">vt|varstree</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-cmd-vt.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">(i)nspect</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-cmd-i.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">bt</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-cmd-bt.jpg">
</figure>

### Print object info

<figure class="image">
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-pinfo.jpg">
</figure>

<figure class="image">
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-pinfo2.jpg">
</figure>

### IPython magic func

<figure class="image">
  <figcaption style="text-align: center;">magic func</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-magic.jpg">
</figure>

<figure class="image">
  <figcaption style="text-align: center;">time</figcaption>
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-magic-time.jpg">
</figure>

## Auto launch debugger when exception

`plan-d` supports automatically launching the debugger when an exception occurs.

You can enclose code with the with statement to launch `plan-d` if an exception is raised:

```python
import plan_d

with plan_d.lpe():
    [...]
```

Or you can use `lpe` as a function decorator to launch `plan-d` if an exception is raised:


```python
import plan_d

@plan_d.lpe()
def main():
    [...]
```
When the client connects, the stack information will be displayed.
<figure class="image">
  <img src="https://zenxu-github-asset.s3.us-east-2.amazonaws.com/plan-d/pland-decorator.jpg">
</figure>

## FAQ

### How to exit the debugger?

Exit by typing the command `exit` or pressing <kbd>ctrl+d</kbd>.
