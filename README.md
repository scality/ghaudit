# Ghaudit

Github organisation security auditing tool.

Ghaudit verifies the state of a github organisation for compliance against a
reference configuration for access control. Properties that can be checked now:

 * repository sharing (private, public, or internal)
 * effective repository access
 * organisation teams, with their hierarchy and accesses
 * organisation team members with roles
 * organisation members with roles
 * repository branch protection rules

Ghaudit is caching a snapshot state of the github organisation in order to make
audit results reproducible.

Ghaudit is only for auditing: ghaudit can not run write operations for applying
remediation.

## Installation

ghaudit requires python 3.8 or later.


```shell
git clone https://github.com/scality/ghaudit
cd ghaudit
pip install .
```

## Configuration

Ghaudit relies on 3 configuration files:

 * a `user map.yml` file describing a mapping between github logins and emails
 * an `organisation.yml` file describing the expected organisation structure
 * a `policy.yml` file describing the policy of access to the github
   organisation resources

### Organisation configuration file

This configuration file describes the expected structure or the organisation
members and teams hierarchy, as well as the github organisation owners.

See the [example configuration file](example/organisation.yml) to find out how
to define an organisation structure.

The user map is stored in an XDG compliant user configuration directory by
default:

 * `$XDG_CONFIG_HOME/ghaudit/organisation.yml` if `XDG_CONFIG_HOME` is set and
   non empty.
 * `$HOME/ghaudit/organisation.yml` otherwise

An alternative path to the configuration file can be specified with `--config`.

### User map configuration

In order to help managing ghaudit configuration and policy in a corporate
environment, ghaudit relies on emails as much as possible. However a github
account email may not be trusted. This is why ghaudit relies on a configuration
file to make the relationship between accounts and emails.

See the [example configuration file](example/user%20map.yml) to find out how to
define the user map.

The user map is stored in an XDG compliant user configuration directory by
default:

 * `$XDG_CONFIG_HOME/ghaudit/user map.yml` if `XDG_CONFIG_HOME` is set and non
   empty.
 * `$HOME/ghaudit/user map.yml` otherwise

An alternative path to the user map can be specified with `--user-map`.

### Policy Configuration

The policy describes the desired access rules and security controls over the
github resources. Supported features are:

 * repository visibility
 * rules of access:
   * access mapping between lists of teams and repositories
   * branch protection rules to apply to repositories
 * exceptions to the rules: direct user access to team, including external
   collaborators

ghaudit supports 2 mode of branch protection rules checking:

 * a baseline mode: the described branch protection rules list the minimal
   restrictions to apply to branches for the policy to pass
 * a strict mode: the described branch protection rules represent the exact
   match of restrictions and authorisations for the policy to pass

See the [example configuration file](example/policy.yml) to find out how
to define a policy document.

ghaudit looks in the XDG compliant user configuration directory for the policy
by default:

 * `$XDG_CONFIG_HOME/ghaudit/policy.yml` if `XDG_CONFIG_HOME` is set and
   non empty.
 * `$HOME/ghaudit/policy.yml` otherwise

An alternative path to the policy can be specified with `--policy`.

### Github credentials

Github API credentials are required in order to run ghaudit. The following API
scopes are required:

 * user/read:user
 * admin:org/read:org
 * repo

Without read only admin access, branch protection rules can not be tested and
hidden teams will not be seen by ghaudit.

See also the [github
documentation](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/creating-a-personal-access-token)
about personal access token creation.

The personal access token must be stored in a
[pass](https://www.passwordstore.org) store, with `ghaudit/github-token` as
name by default:

```shell
$> pass insert ghaudit/github-token
Enter password for ghaudit/github-token:
Retype password for ghaudit/github-token:
#>
```

Alternatively, if you do not have pass installed, you can use
[passpy](https://pypi.org/project/passpy/) instead, which is included with
ghaudit:

```shell
$> passpy insert ghaudit/github-token
Enter password for ghaudit/github-token:
Repeat for confirmation:
#>
```

The name of the token can be specified using the option `--token-pass-name`, if
the default pass path is not used. See `ghaudit cache refresh --help` for more
details.

## Usage

ghaudit is split in multiple sub commands which can themselves have sub
commands. All commands have their own detailed usage:

```shell
$> ghaudit
Usage: ghaudit [OPTIONS] COMMAND [ARGS]...

  Github organisation security auditing tool.

Options:
  -c, --config TEXT
  --user-map TEXT
  --policy TEXT
  -h, --help         Show this message and exit.

Commands:
  cache       Cache manipulation commands.
  compliance  Compliance tests against policies and configuration.
  org         Cached state views.
  stats       Show some statistics about the cached state.
  user        Cached state view for github users.
  usermap     Login to email and email to loginUsage: ghaudit [OPTIONS] COMMAND [ARGS]...
$> ghaudit cache
Usage: ghaudit cache [OPTIONS] COMMAND [ARGS]...

  Cache manipulation commands.

Options:
  --help  Show this message and exit.

Commands:
  path
  refresh
```

### Typical workflow

A typical workflow using ghaudit consists of:

 * a cache refresh
 * a compliance check run
 * investigating

```shell
$> ghaudit cache refresh
[redacted]
validating cache
persisting cache
$> ghaudit compliance check all
[errors]
```

Investigating the state of the organisation can be done by using the following
command groups:

 * `ghaudit org`: show information about the state of the audited organisation
 * `ghaudit user`: show information about a user if the user is related to the
   organisation or if they are a collaborator to a repository owned by the
   organisation

Most investigation commands have output formatting mode that can be specified
using the `--format` option.

## Audit scope

ghaudit will implicitly audit all repositories that are not forks or not
archived by default. To silence compliance errors for some repositories,
repositories can be explicitly excluded in the policy configuration. See also
the [example file](example/policy.yml) for the policy configuration.

## Security

If you found a security vulnerability in ghaudit, please refer to our security
policy for instruction on how to report it. The Security policy can be found
here: [docs/SECURITY.md](docs/SECURITY.md).

## Contributing

Contributing guidelines can be found here:
[docs/contributing.md](docs/contributing.md).
