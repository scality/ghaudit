"""CLI interface."""

from typing import Any, Callable, Iterable, Mapping, Optional, cast

import click
from ruamel.yaml import YAML

from ghaudit import (
    auth,
    cache,
    compliance,
    config,
    policy,
    schema,
    ui,
    user_map,
)

try:
    from typing import get_args as typing_get_args
except ImportError:
    # python 3.7 support
    from typing_extensions import get_args as typing_get_args


def _load_organisation_conf(filename: str) -> user_map.RawData:
    with open(filename, encoding="UTF-8") as conf_file:
        conf = YAML(typ="safe").load(conf_file)
    return cast(user_map.RawData, conf)


def _load_user_map_conf(filename: str) -> Mapping:
    with open(filename, encoding="UTF-8") as usermap_file:
        usermap_data = YAML(typ="safe").load(usermap_file)
        usermap = user_map.load(usermap_data)
    return usermap


def _load_policy_conf(filename: str) -> policy.Policy:
    policy_ = policy.Policy()
    with open(filename, encoding="UTF-8") as policy_file:
        policy_data = YAML(typ="safe").load(policy_file)
        policy_.load_config(policy_data)
    return policy_


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.option(
    "-c",
    "--config",
    "config_filename",
    default=config.default_dir() / "organisation.yml",
)
@click.option(
    "--user-map",
    "usermap_filename",
    default=config.default_dir() / "user map.yml",
)
@click.option(
    "--policy", "policy_filename", default=config.default_dir() / "policy.yml"
)
@click.pass_context
def cli(
    ctx: click.Context,
    config_filename: str,
    usermap_filename: str,
    policy_filename: str,
) -> None:
    """Github organisation security auditing tool."""
    ctx.ensure_object(dict)
    ctx.obj["config"] = lambda: _load_organisation_conf(config_filename)
    ctx.obj["usermap"] = lambda: _load_user_map_conf(usermap_filename)
    ctx.obj["policy"] = lambda: _load_policy_conf(policy_filename)


@cli.group("compliance")
def compliance_group() -> None:
    """Compliance tests against policies and configuration."""


@compliance_group.command("check-all")
@click.pass_context
def compliance_check_all(ctx: click.Context) -> None:
    """Run all compliance checks."""
    compliance.check_all(
        ctx.obj["config"](), ctx.obj["usermap"](), ctx.obj["policy"]()
    )


@cli.group("cache")
def cache_group() -> None:
    """Cache manipulation commands."""


@cache_group.command("path")
def cache_path() -> None:
    """Show the path where the cache of ghaudit is stored."""
    print(cache.file_path())


@cache_group.command("refresh")
@click.option("--token-pass-name", default="ghaudit/github-token")
@click.pass_context
def cache_refresh(ctx: click.Context, token_pass_name: str) -> None:
    """Refresh ghaudit cache.

    Request the state of the configured github organisation and store it to a
    cache file to evaluate later.
    """
    auth_driver = auth.github_auth_token_passpy(token_pass_name)
    cache.refresh(
        ctx.obj["config"](),
        auth_driver,
        ui.Progress(),
    )


def _user_short_str(user: schema.User) -> str:
    if schema.user_name(user):
        return "{} ({})".format(
            schema.user_login(user), schema.user_name(user)
        )
    return "{}".format(schema.user_login(user))


def _repo_short_str(repo: schema.Repo) -> str:
    return schema.repo_name(repo)


def _team_short_str(team: schema.Team) -> str:
    return schema.team_name(team)


@cli.command()
def stats() -> None:
    """Show some statistics about the cached state."""
    rstate = cache.load()
    teams = len(schema.org_teams(rstate))
    repositories = len(schema.org_repositories(rstate))
    members = len(schema.org_members(rstate))
    users = len(schema.users(rstate))
    bp_rules = len(schema.all_bp_rules(rstate))
    print(
        "teams: {}\n"
        "repositories: {}\n"
        "org members: {}\n"
        "users: {}\n"
        "branch protection rules: {}\n"
        "total objects: {}".format(
            teams,
            repositories,
            members,
            users,
            bp_rules,
            teams + repositories + members + users + bp_rules,
        )
    )


def _common_list(
    list_func: Callable[[schema.Rstate], Iterable[Any]],
    mode: ui.DisplayMode,
    fmt: ui.Formatter,
    rstate: Optional[schema.Rstate] = None,
) -> None:
    if not rstate:
        rstate = cache.load()
    _list = list_func(rstate)
    ui.print_items(mode, _list, fmt)


@cli.group("org")
def org_group() -> None:
    """Cached state views."""


@org_group.group("repositories")
def org_repositories_group() -> None:
    """Cached state view of repositories."""


@org_repositories_group.command("list")
@click.option(
    "--format",
    "mode",
    type=click.Choice(typing_get_args(ui.DisplayMode)),
    default="basic",
)
def org_repositories_list(mode: ui.DisplayMode) -> None:
    """List the repositories of the configured organisation."""
    _common_list(
        schema.org_repositories,
        mode,
        ui.Formatter(
            (("name", 40), ("archived", 8), ("fork", 5)),
            lambda x: (
                (schema.repo_name(x), 40),
                (str(schema.repo_archived(x)), 8),
                (str(schema.repo_forked(x)), 5),
            ),
            _repo_short_str,
        ),
    )


@org_repositories_group.command("count")
def org_repositories_count() -> None:
    """Count the number of repositories in the configured organisation."""
    rstate = cache.load()
    repos = schema.org_repositories(rstate)
    print(len(repos))


@org_repositories_group.command("branch-protection")
@click.option(
    "--format",
    "mode",
    type=click.Choice(typing_get_args(ui.DisplayMode)),
    default="basic",
)
@click.argument("name")
@click.pass_context
def org_repositories_branch_protection(
    ctx: click.Context, name: str, mode: ui.DisplayMode
) -> None:
    """Show branch protection rules of a repository."""
    rstate = cache.load()
    usermap = ctx.obj["usermap"]()
    repo = schema.org_repo_by_name(rstate, name)
    _common_list(
        lambda _: schema.repo_branch_protection_rules(repo),
        mode,
        ui.Formatter(
            (
                ("pattern", 20),
                ("creator", 40),
                ("admin enforced", 14),
                ("approvals", 9),
                ("owner approval", 14),
                ("commit signatures", 17),
                ("linear history", 14),
                ("restrict pushes", 15),
                ("restrict deletion", 17),
            ),
            lambda x: (
                (schema.branch_protection_pattern(x), 20),
                (
                    user_map.email(
                        usermap, schema.branch_protection_creator(x)
                    ),
                    40,
                ),
                (str(schema.branch_protection_admin_enforced(x)), 14),
                (str(schema.branch_protection_approvals(x)), 9),
                (str(schema.branch_protection_owner_approval(x)), 14),
                (str(schema.branch_protection_commit_signatures(x)), 17),
                (str(schema.branch_protection_linear_history(x)), 14),
                (str(schema.branch_protection_restrict_pushes(x)), 15),
                (str(schema.branch_protection_restrict_deletion(x)), 17),
            ),
            schema.branch_protection_pattern,
        ),
    )


@org_group.group("members")
def org_members_group() -> None:
    """Cached state view of organisation members."""


@org_members_group.command("list")
@click.option(
    "--format",
    "mode",
    type=click.Choice(["basic", "json", "table"]),
    default="basic",
)
def org_members_list(mode: ui.DisplayMode) -> None:
    """Show the list of members in the configured organisation."""
    _common_list(
        schema.org_members,
        mode,
        ui.Formatter(
            (("login", 30), ("name", 30), ("company", 30), ("email", 30)),
            lambda x: (
                (schema.user_login(x), 30),
                (schema.user_name(x), 30),
                (schema.user_company(x), 30),
                (schema.user_email(x), 30),
            ),
            _user_short_str,
        ),
    )


@org_members_group.command("count")
def org_members_count() -> None:
    """Count the number of members in the configured organisation."""
    rstate = cache.load()
    members = schema.org_members(rstate)
    print(len(members))


@org_group.group("teams")
def org_teams_group() -> None:
    """Cached state view of organisation teams."""


@org_teams_group.command("tree")
def org_teams_tree() -> None:
    """Show the list of teams hierarchically."""

    def print_teams(teams: Iterable[schema.Team], indent: int) -> None:
        for team in teams:
            team_name = schema.team_name(team)
            print("{}* {}".format("".rjust(indent * 2), team_name))
            children = [
                x
                for x in schema.team_children(rstate, team)
                if schema.team_name(x) != team_name
            ]
            print_teams(children, indent + 1)

    rstate = cache.load()
    teams = schema.org_teams(rstate)
    roots = [x for x in teams if not schema.team_parent(rstate, x)]
    print_teams(roots, 1)


@org_teams_group.command("list")
@click.option(
    "--format",
    "mode",
    type=click.Choice(["basic", "json", "table"]),
    default="basic",
)
def org_teams_list(mode: ui.DisplayMode) -> None:
    """Show the list of teams in the configured organisation."""
    rstate = cache.load()
    _common_list(
        schema.org_teams,
        mode,
        ui.Formatter(
            (("name", 30), ("repositories", 12), ("members", 7)),
            lambda x: (
                (schema.team_name(x), 30),
                (str(len(schema.team_repos(rstate, x))), 12),
                (str(len(schema.team_members(rstate, x))), 7),
            ),
            _team_short_str,
        ),
        rstate,
    )


@org_teams_group.command("count")
def org_teams_count() -> None:
    """Count the number of teams in the configured organisation."""
    rstate = cache.load()
    teams = schema.org_teams(rstate)
    print(len(teams))


@org_group.group("repository")
def org_repository_group() -> None:
    """Cached state view for a given repository."""


@org_repository_group.command("show")
@click.argument("name")
def org_repository_show(name: str) -> None:
    """Show detailed attributes of a given repository."""

    def collaborators(repository: schema.Repo) -> str:
        result = "\n"
        for collaborator in schema.repo_collaborators(rstate, repository):
            permission = collaborator["role"]
            result += "   * {} ({}): {}\n".format(
                schema.user_name(collaborator),
                schema.user_login(collaborator),
                permission,
            )
        return result

    rstate = cache.load()
    repository = schema.org_repo_by_name(rstate, name)
    print(
        (
            " * name: {}\n"
            + " * description: {}\n"
            + " * archived: {}\n"
            + " * is fork: {}\n"
            + " * collaborators: {}"
        ).format(
            schema.repo_name(repository),
            schema.repo_description(repository),
            schema.repo_archived(repository),
            schema.repo_forked(repository),
            collaborators(repository),
        )
    )


@org_group.group("team")
def org_team_group() -> None:
    """Cached state view for a given team."""


@org_team_group.command("show")
@click.argument("name")
def org_team_show(name: str) -> None:
    """Show detailed attributes of a given team."""

    def members(team: schema.Team) -> str:
        result = "\n"
        for member in schema.team_members(rstate, team):
            permission = member["role"]
            result += "   * {} ({}): {}\n".format(
                schema.user_name(member),
                schema.user_login(member),
                permission,
            )
        return result

    def repositories(team: schema.Team) -> str:
        result = "\n"
        for repo in schema.team_repos(rstate, team):
            permission = repo["permission"]
            result += "   * {}: {}\n".format(
                schema.repo_name(repo),
                permission,
            )
        return result

    def children(team: schema.Team) -> str:
        result = "\n"
        for child in schema.team_children(rstate, team):
            result += "   * {}\n".format(
                schema.team_name(child),
            )
        return result

    rstate = cache.load()
    team = schema.org_team_by_name(rstate, name)
    print(
        (
            " * name: {}\n"
            + " * description: {}\n"
            + " * members: {}"
            + " * repositories: {}"
            + " * sub teams: {}"
        ).format(
            schema.team_name(team),
            schema.team_description(team),
            members(team),
            repositories(team),
            children(team),
        )
    )


@cli.group("user")
def user_group() -> None:
    """Cached state view for github users.

    Applies to organisation members and external collaborators."""


@user_group.command("show")
@click.argument("login")
def user_show(login: str) -> None:
    """Show detailed attributes of a given github user.

    The user does not need to belong to the organisation. ghaudit gathers user
    information for external collaborators as well."""

    def teams(rstate: schema.Rstate) -> str:
        result = "\n"
        for team in schema.org_teams(rstate):
            for member in schema.team_members(rstate, team):
                if schema.user_login(member) == login:
                    result += "   * {}\n".format(schema.team_name(team))
        return result

    rstate = cache.load()
    user = schema.user_by_login(rstate, login)
    if user:
        print(
            (
                " * name: {}\n"
                + " * login: {}\n"
                + " * email: {}\n"
                + " * company: {}\n"
                + " * teams: {}"
            ).format(
                schema.user_name(user),
                schema.user_login(user),
                schema.user_email(user),
                schema.user_company(user),
                teams(rstate),
            )
        )
    else:
        print("user {} not found".format(login))


@cli.group("usermap")
def usermap_group() -> None:
    """Login to email and email to login."""


@usermap_group.command("get-login")
@click.argument("email")
@click.pass_context
def usermap_get_login(ctx: click.Context, email: str) -> None:
    """Show the login of an organisation member given their email."""
    print(user_map.login(ctx.obj["usermap"](), email))


@usermap_group.command("get-email")
@click.argument("login")
@click.pass_context
def usermap_get_email(ctx: click.Context, login: str) -> None:
    """Show the email of an organisation member given their login."""
    print(user_map.email(ctx.obj["usermap"](), login))
