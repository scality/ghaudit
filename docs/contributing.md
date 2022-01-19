# Contributing to the project

This document contains and defines the rules that have to be followed by any
contributor to the project, in order for any change to be merged into the stable
branches. These guidelines have been inspired from the main [Scality
Guidelines](https://github.com/scality/Guidelines/blob/development/8.1/CONTRIBUTING.md),
but have been simplified due to differences in the workflow and a much smaller
size of maintainer team.

## Coding for the project

### Branching guidelines

In order to work on the project, any contributor will be asked to create
separate branches for each task. A contributor must thus create a branch, that
he can push into the project's repository. He can then start working, and commit
following the [guidelines](#committing-guidelines).

The branch name should contain a Jira ticket identifier just after a potential
prefix, followed by a few words describing the work to be done in the branch.

Here is an example of valid branch names:

 * `my_work/JIRA-32-fixing-what-needs-fixing`
 * `JIRA-55-small-changes`
 * `category/project_name/JIRA-512-my_changes`

Note that the naming convention of branches matters only when a pull request is
created. From the beginning of the development work, the name of the branch can
change and should not matter until someone is asked to review it.

When the contributor's work is complete, he can create a pull request from their
branch into the master branch. Then, the code merging process described in
[Merging code into the master](#merging-code-into-the-master) starts.

### Development guidelines

With their own branch, a contributor can manage the branch's code as he wishes, as
the branch is their own responsibility, within the constraints of the project.
These constraints include:

* Complying to the [Coding Style Guidelines](#coding-style-guidelines)
* Providing the proper tests to validate the proposed code

In order for the project to be as stable as possible, every piece of code must
be tested. This means that any code submission must be associated with related
tests or changes on the existing tests, depending on the type of code you
submitted.

### Committing guidelines

In their own branch, a contributor can commit and manage the branch's history as
he wishes, as the branch is his own responsibility, within the constraints of
the project. These constraints for the commits include:

* Commit Message Formatting Policy
* Peer validation of the commit's atomicity and meaningfulness
* Squashing all commits into one message before doing pull request

It is asked of every contributor to provide commit messages as clear as
possible, while attempting to make one commit comply to the following
conditions:

* Provide one and only one feature/bug fix/meaningful change
* Provide working unit and functional tests associated to the change.

The commit message shall follow a **standardized formatting, that will be
checked automatically by a VCS hook on the commit**.

The first line of the commit message (often called the one-liner) shall provide
the essential information about the commit itself. It should contain the
identifier of the Jira ticket associated with the work related to the change,
followed by one space, and a short imperative sentence to describe the essence
of the commit in 55 characters.

If more details seem necessary or useful, one line must be left empty (to follow
the consensual git commit way), and either a paragraph, a list of items, or both
can be written to provide insight into the details of the commit. Those details
can include describing the workings of the change, explain a design choice, or
providing a tracker reference (issue number or bug report link).

## Merging code into the master

Once the work on their branch is complete, contributor A can submit a
`Pull-Request` to merge their branch into the `master` branch. At this point,
every contributor can review the `PR`, and comment on it. Once at least one
contributor validates the `PR` through an ostensible "+1" comment, we deem the
code change validated by enough peers to assume it is valid. Then, the core
members of the project can act on the `PR` by merging the given commits into the
`master` branch.

The code reviews must include the following checks:

* Ensuring the compliance to the coding style guidelines
* Ensuring the presence and coverage of tests
* Ensuring the code is functional and working, through the tests
* Ensuring the commit messages were properly formatted and as atomic as possible

## Coding style guidelines

This Coding Style guidelines exist for one simple reason: working together. This
means that by following those, the different contributors will naturally follow
a common style, making the project unified in this aspect. This will prove to be
a good way to minimize the time waste due to trying to read and understand a
code with completely different standards.

If any rule seems out-of-bounds, any contributor is welcome to discuss it, as
long as he/she follows the rules set for the project. Linter configuration is
provided in the project in order to help enforce as much as possible of it.

The coding styles relies on [the black coding
style](https://black.readthedocs.io/en/stable/the_black_code_style/current_style.html)
which is itself PEP 8 compliant. PEP 8 documentation can be found there:

 * [PEP 8 (Style Guide for
   PythonCode)](https://www.python.org/dev/peps/pep-0008/)
 * [https://pep8.org/](https://pep8.org/) (less formal)

The black coding style can be applied easily to the code using the [black
package](https://pypi.org/project/black/):

```shell
black src/ghaudit tests
```

It is advised to integrate black with an
[IDE](https://black.readthedocs.io/en/stable/integrations/editors.html) or with
a [git pre-commit
hook](https://black.readthedocs.io/en/stable/integrations/source_version_control.html).

### Additional rules and exceptions

#### Long strings and line length

Long strings should not be broken in multiple lines, even if this results in a
line of code longer than what is authorised by the coding style guidelines. The
rationale behind this is that strings should be easily searchable in the code,
with utilities such as `grep`, especially error messages.

#### Python type hints

Type hints are also required in the code in order to help checking various
issues with the code.

### Checking the style of the code

The compliance to the coding style can be easily checked using tox:

```shell
tox -e lint,typing
```
