# Contributing

* <a class="github-button" href="https://github.com/fgmacedo/python-statemachine" data-icon="octicon-star" aria-label="Star fgmacedo/python-statemachine on GitHub">Star this project</a>
* <a class="github-button" href="https://github.com/fgmacedo/python-statemachine/issues" data-icon="octicon-issue-opened" aria-label="Issue fgmacedo/python-statemachine on GitHub">Open an Issue</a>
* <a class="github-button" href="https://github.com/fgmacedo/python-statemachine/fork" data-icon="octicon-repo-forked" aria-label="Fork fgmacedo/python-statemachine on GitHub">Fork</a>

Contributions are welcome, and they are greatly appreciated! Every little bit helps, and credit
will always be given.

You can contribute in many ways:

## Types of Contributions

### Report Bugs

Report bugs at [https://github.com/simonweniger/agentkit/issues](https://github.com/simonweniger/agentkit/issues).

If you are reporting a bug, please include:

* Your operating system name and version.
* Any details about your local setup that might be helpful in troubleshooting.
* Detailed steps to reproduce the bug.

### Fix Bugs

Look through the GitHub issues for bugs. Anything tagged with "bug"
and "help wanted" is open to whoever wants to implement it.

### Implement Features

Look through the GitHub issues for features. Anything tagged with "enhancement"
and "help wanted" is open to whoever wants to implement it.

### Write Documentation

Agentkit Workflow could always use more documentation, whether as part of the
official Agentkit Workflow docs, in docstrings, or even on the web in blog posts,
articles, and such.

### Add a translation

Extract a `Portable Object Template` (`POT`) file:

```shell
pybabel extract agentkit -o ./locale/agentkit.pot
```

Then, copy the template as a `.po` file into the target locale folder. For example, if you're adding support for Brazilian Portuguese language, the code is `pt_BR`, and the file path should be `./locale/pt_BR/LC_MESSAGES/agenkit.po`:

```shell
cp ./locale/agentkit.pot ./locale/pt_BR/LC_MESSAGES/agentkit.po
```

Then open the `agentkit.po` and translate.

After translation, to get the new language working locally, you need to compile the `.po` files into `.mo`  (binary format). Run:

```shell
pybabel compile -d agentkit/locale/ -D agentkit
```

On Linux (Debian based), you can test changing the `LANGUAGE` environment variable.

```shell
# If the last line is `Can't guess when in Won.` something went wrong.
LANGUAGE=pt_BR python tests/examples/guess_the_number_machine.py
```

Then open a [pull request](https://github.com/simonweniger/agentkit/pulls) with your translation file.

### Submit Feedback

The best way to send feedback is to file an issue at <https://github.com/simonweniger/agentkit/issues>.

If you are proposing a feature:

* Explain in detail how it would work.
* Keep the scope as narrow as possible, to make it easier to implement.
* Remember that this is a volunteer-driven project, and that contributions
  are welcome :)

## Get Started

Ready to contribute? Here's how to set up `python-statemachine` for local development.

1. Install dependencies.
   1. [graphviz](https://graphviz.org/download/#linux)
   1. [poetry](https://python-poetry.org/docs/#installation)

1. Fork the `python-statemachine` repository on GitHub.

1. Clone the forked repository to your local flow by running::

```shell
        git clone https://github.com/YOUR-USERNAME/agentkit.git.
```

1. Run `poetry install` once to install all the dependencies and create a virtual environment::

```shell
        poetry install
```

1. Run `poetry shell` to enter the provided virtual

1. Install the pre-commit validations:

```shell
        pre-commit install
```

1. Create a branch for local development:

```shell
        git checkout -b <name-of-your-bugfix-or-feature>
```

1. Make changes to the code.

1. Run tests to ensure they pass by running:

```shell
        poetry run pytest
```

1. Update the documentation as needed.

    Build the documentation:

```shell
        poetry run sphinx-build docs docs/_build/html
```

Now you can serve the local documentation using a webserver, like the built-in included with python:

```shell
        python -m http.server --directory docs/_build/html
```

And access your browser at <http://localhost:8000/>

If you're specially writting documentation, I strongly recommend using `sphinx-autobuild` as it improves the workflow watching for file changes and with live reloading:

```shell
        poetry run sphinx-autobuild docs docs/_build/html --re-ignore "auto_examples/.*"
```

Sometimes you need a full fresh of the files being build for docs, you can safely remove all automatically generated files to get a clean state by running:

```shell
        rm -rf docs/_build/ docs/auto_examples
```

1. Commit your changes and push them to your forked repository:

```shell
    git add -A .
    git commit -s -m "Your detailed description of your changes."
    git push origin name-of-your-bugfix-or-feature
```

1. Create a pull request on the original repository for your changes to be reviewed and potentially
merged. Be sure to follow the project's code of conduct and contributing guidelines.

1. Use `exit` to leave the virtual environment.

## Pull Request Guidelines

Before you submit a pull request, check that it meets these guidelines:

1. The pull request should include tests.
2. If the pull request adds functionality, the docs should be updated. Put
   your new functionality into a function with a docstring, and add the
   feature to the list in the next release notes.
3. Consider adding yourself to the contributor's list.
4. The pull request should work for all supported Python versions.
