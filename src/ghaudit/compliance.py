from typing import Optional

from ghaudit import cache, config, policy, schema, user_map


def error(msg: str) -> None:
    print("Error: {}".format(msg))


def user_str(login: str, username: Optional[str], email: Optional[str]) -> str:
    username_str = '("{}")'.format(username) if username else "(no username)"
    if email:
        return 'user "{}" {}, mapped as {}'.format(login, username_str, email)
    return 'user "{}" {}, not mapped'.format(login, username_str)


def check_team_unref(
    rstate: schema.Rstate,
    conf: config.Config,
    policy_: policy.Policy,
    team: schema.Team,
) -> bool:
    """Check if team is referenced in config

    Ignore teams that do not have access to repositories in scope
    """

    def in_scope(repo: schema.Repo) -> bool:
        return policy.repo_in_scope(policy_, repo)

    name = schema.team_name(team)
    if not config.get_team(conf, name):
        repos = [x for x in schema.team_repos(rstate, team) if in_scope(x)]
        if repos:
            error(
                'unknown team "{}" has access to the following repositories: {}'.format(  # noqa: E501
                    name, [schema.repo_name(x) for x in repos]
                )
            )
            return False
    return True


def check_repo_unref(
    rstate: schema.Rstate,
    conf: config.Config,
    policy_: policy.Policy,
    repo: schema.Repo,
) -> bool:
    """Check if repository is referenced in the policy

    Ignore repositories that are implicitly out of scope
    """
    del rstate
    del conf
    name = schema.repo_name(repo)
    if name not in policy.get_repos(policy_) and policy.repo_in_scope(
        policy_, repo
    ):
        error('repository "{}" not referenced in the policy'.format(name))
        return False
    return True


def check_repo_visibility(
    rstate: schema.Rstate, policy_: policy.Policy, repo: schema.Repo
) -> bool:
    del rstate
    name = schema.repo_name(repo)
    if not policy.repo_in_scope(policy_, repo) or name not in policy.get_repos(
        policy_
    ):
        # ignoring the repository, because it is already checked by repo_unref
        return True

    pol_visibility = policy.repo_visibility(policy_, name)
    rvisibility = "private" if schema.repo_private(repo) else "public"
    if pol_visibility != rvisibility:
        error(
            'repository "{}" is {}, but it should be {}'.format(
                name, rvisibility, pol_visibility
            )
        )
        return False
    return True


def _check_team_repo_permissions(
    rstate: schema.Rstate,
    conf: config.Config,
    policy_: policy.Policy,
    team: schema.Team,
    repo: schema.RepoWithPerms,
) -> bool:
    del rstate
    name = schema.team_name(team)
    repo_name = schema.repo_name(repo)
    policy_perm = policy.team_repo_perm(
        conf, policy_, schema.team_name(team), repo
    )
    perm = policy.perm_translate(repo["permission"])
    if not policy_perm:
        error(
            'team "{}" should not have access to "{}". current permission level for the team is {}'.format(  # noqa: E501
                name, repo_name, perm
            )
        )
        return False
    if policy.perm_higher(perm, policy_perm):
        error(
            'team "{}" has permission level too high to repository "{}" ({} instead of {}).'.format(  # noqa: E501
                name, repo_name, perm, policy_perm
            )
        )
        return False
    if perm != policy_perm:
        error(
            'team "{}" has permission level too low to repository "{}" ({} instead of {}).'.format(  # noqa: E501
                name, repo_name, perm, policy_perm
            )
        )
        return False
    return True


def check_team_permissions(
    rstate: schema.Rstate,
    conf: config.Config,
    policy_: policy.Policy,
    team: schema.Team,
) -> bool:
    repositories = schema.team_repos(rstate, team)
    success = True

    for repo in [x for x in repositories if policy.repo_in_scope(policy_, x)]:
        result = _check_team_repo_permissions(
            rstate, conf, policy_, team, repo
        )
        success = success and result
    return success


def check_team_members(
    rstate: schema.Rstate,
    conf: config.Config,
    usermap: user_map.UserMap,
    policy_: policy.Policy,
    team: schema.Team,
) -> bool:
    del policy_
    name = schema.team_name(team)
    conf_team = config.get_team(conf, name)
    success = True

    if conf_team:
        rmembers = schema.team_members(rstate, team)
        rmembers_emails = [
            user_map.email(usermap, schema.user_login(x)) for x in rmembers
        ]
        conf_members = config.team_direct_members(conf_team)
        for rmember, email in zip(rmembers, rmembers_emails):
            if email not in config.team_effective_members(conf, conf_team):
                error(
                    '{}, should not be part of the team "{}"'.format(
                        user_str(
                            schema.user_login(rmember),
                            schema.user_name(rmember),
                            email,
                        ),
                        name,
                    )
                )
                success = False
        for member in conf_members:
            if member not in rmembers_emails:
                error(
                    'user "{}" should be part of the team "{}"'.format(
                        member, name
                    )
                )
                success = False
    return success


def check_repo_collaborators(
    rstate: schema.Rstate,
    conf: config.Config,
    usermap: user_map.UserMap,
    policy_: policy.Policy,
    repo: schema.Repo,
) -> bool:
    name = schema.repo_name(repo)
    success = True

    if not policy.repo_in_scope(policy_, repo):
        return True

    for collaborator in schema.repo_collaborators(rstate, repo):
        login = schema.user_login(collaborator)
        username = schema.user_name(collaborator)
        email = user_map.email(usermap, login)
        perm = policy.perm_translate(collaborator["role"])
        policy_user_perm = policy.user_perm(
            conf, policy_, usermap, repo, login
        )
        if not policy_user_perm:
            error(
                '{}, should not have access to "{}". current permission level for "{}" is {}'.format(  # noqa: E501
                    user_str(login, username, email), name, login, perm
                )
            )
            success = False
        elif policy.perm_higher(perm, policy_user_perm):
            error(
                '{}, has permission level too high to repo "{}". ({} instead of {})'.format(  # noqa: E501
                    user_str(login, username, email),
                    name,
                    perm,
                    policy_user_perm,
                )
            )
            success = False
        elif perm != policy_user_perm:
            error(
                '{}, has permission level too low to repo "{}". ({} instead of {})'.format(  # noqa: E501
                    user_str(login, username, email),
                    name,
                    perm,
                    policy_user_perm,
                )
            )
            success = False
    return success


def check_user(
    rstate: schema.Rstate,
    conf: config.Config,
    usermap: user_map.UserMap,
    policy_: policy.Policy,
    user: schema.UserWithOrgRole,
) -> bool:
    del rstate
    del policy_
    result = True
    login = schema.user_login(user)
    email = user_map.email(usermap, login)
    if not email:
        error('user login "{}" is not mapped.'.format(login))
        result = False
    if schema.user_is_owner(user):
        if not email:
            error(
                "{} should not be an organisation owner".format(
                    user_str(login, schema.user_name(user), email)
                )
            )
            result = False
        elif not config.is_owner(conf, email):
            error(
                "{} should not be an organisation owner".format(
                    user_str(login, schema.user_name(user), email)
                )
            )
            result = False
    if (
        not schema.user_is_owner(user)
        and email
        and config.is_owner(conf, email)
    ):
        error(
            "{} should be an organisation owner".format(
                user_str(login, schema.user_name(user), email)
            )
        )
        result = False
    return result


def check_missing_repos(
    rstate: schema.Rstate, conf: config.Config, policy_: policy.Policy
) -> bool:
    """Check if a repository is part of the policy_, but does not exist"""
    del conf
    errors = False
    for repo_name in policy.get_repos(policy_):
        if not schema.org_repo_by_name(rstate, repo_name):
            print('Error: repository "{}" does not exist'.format(repo_name))
            errors = True
    return errors


def check_missing_teams(
    rstate: schema.Rstate, conf: config.Config, policy_: policy.Policy
) -> bool:
    """Check if a team is part of the policy_, but does not exist"""
    errors = False
    del policy_
    for team in config.get_teams(conf):
        name = config.team_name(team)
        if not schema.org_team_by_name(rstate, name):
            print('Error: team "{}" does not exist'.format(name))
            errors = True
    return errors


def check_repo_branch_protection(
    rstate: schema.Rstate,
    conf: config.Config,
    policy_: policy.Policy,
    repo: schema.Repo,
) -> bool:
    del conf
    errors = False
    name = schema.repo_name(repo)
    patterns = policy.branch_protection_patterns(policy_, name)
    for pattern in patterns:
        rstate_value = schema.repo_branch_protection_rule(repo, pattern)
        if not rstate_value:
            error(
                'missing branch protection rule with pattern "{}" for repository "{}"'.format(  # noqa: E501
                    pattern, name
                )
            )
            errors = True
        else:
            rule = policy.branch_protection_get(policy_, name, pattern)
            result = policy.bprule_cmp(
                rstate, policy_, rstate_value, rule.model, rule.mode
            )
            if result:
                error(
                    'mismatched branch protection rule in repository "{}" with pattern "{}". differences: {}'.format(  # noqa: E501
                        name, pattern, result
                    )
                )
            errors = True
    return errors


def check_all(
    conf: config.Config, usermap: user_map.UserMap, policy_: policy.Policy
) -> None:
    rstate = cache.load()
    for repo in schema.org_repositories(rstate):
        check_repo_unref(rstate, conf, policy_, repo)
    for repo in schema.org_repositories(rstate):
        check_repo_visibility(rstate, policy_, repo)
    for member in schema.org_members(rstate):
        check_user(rstate, conf, usermap, policy_, member)
    for team in schema.org_teams(rstate):
        check_team_unref(rstate, conf, policy_, team)
    for team in schema.org_teams(rstate):
        check_team_permissions(rstate, conf, policy_, team)
    for team in schema.org_teams(rstate):
        check_team_members(rstate, conf, usermap, policy_, team)
    for repo in schema.org_repositories(rstate):
        check_repo_collaborators(rstate, conf, usermap, policy_, repo)
    for repo in schema.org_repositories(rstate):
        check_repo_branch_protection(rstate, conf, policy_, repo)
    check_missing_teams(rstate, conf, policy_)
    check_missing_repos(rstate, conf, policy_)
