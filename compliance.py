# https://realpython.com/primer-on-python-decorators/

from ghaudit import cache
from ghaudit import config
from ghaudit import policy
from ghaudit import schema


class ComplianceError():
    def msg():
        raise NotImplementedError('abstract function call')

    # Exact type of the error
    def err_type():
        raise NotImplementedError('abstract function call')

    # tell whether:
    # - something is missing
    # - something is added
    # - something is different
    def diff_type():
        raise NotImplementedError('abstract function call')

    # should return a dict containing
    # - target type (repo, team, member)
    # - target ID if applicable
    def err_targets():
        raise NotImplementedError('abstract function call')


def check_repo(rstate, conf, policy_, repo):
    """Repo compliance checks:

    check 1: check that the repository is referenced in the policy
    check 2: check that all collaborators conform to the policy
    """
    name = schema.repo_name(repo)
    if name not in policy.get_repos(policy_):
        if policy.repo_in_scope(policy_, repo):
            print('Error: repository "{}" not referenced in the policy'.format(name))
    else:
        if policy.repo_in_scope(policy_, repo):
            collaborators = schema.repo_collaborators(rstate, repo)
            for collaborator in collaborators:
                check_repo_collaborator(rstate, conf, policy_, repo,
                                        collaborator)


def check_missing_repos(rstate, conf, policy_):
    """Check if a repository is part of the policy_, but does not exist
    """
    for repo_name in policy.get_repos(policy_):
        if not schema.org_repo_by_name(rstate, repo_name):
            print('Error: repository "{}" does not exist'.format(repo_name))


def check_missing_teams(rstate, conf, policy_):
    """Check if a team is part of the policy_, but does not exist
    """
    for team in config.get_teams(conf):
        name = config.team_name(team)
        if not schema.org_team_by_name(rstate, name):
            print('Error: team "{}" does not exist'.format(name))


def check_repo_collaborator(rstate, conf, policy_, repo, collaborator):
    """Repo contributor compliance check:

    check 1: check that the contributor should have access to the repository
    check 2: check that the contributor has proper access level to the
             repository
    """


def check_team(rstate, conf, policy_, team):
    """Team compliance check:

    check 1: check in the configuration that the team should exist
    ? check 2: check that the team ancestors conform to the configuration ?
    ? check 3: check that the team children conform to the configuration ?
    """
    name = schema.team_name(team)
    if not config.get_team(conf, name):
        in_scope = False
        for repo in schema.team_repos(rstate, team):
            if policy.repo_in_scope(policy_, repo):
                in_scope = True
                break
        if in_scope:
            print(
                'Error: unknown team "{}" has access to repositories in the policy'.format(name)
            )
        else:
            print('Warning: unknown team "{}"'.format(name))

    repositories = schema.team_repos(rstate, team)
    for repo in [x for x in repositories if policy.repo_in_scope(policy_, x)]:
        repo_name = schema.repo_name(repo)
        policy_perm = policy.team_repo_perm(policy_, team, repo)
        if not policy_perm:
            print('Error: team "{}" should not have access to {}'.format(name, repo_name))
            continue
        perm = policy.perm_translate(repo['permission'])
        if policy.perm_higher(perm, policy_perm):
            print('Error: permission to "{}" is too high for team "{}".'.format(repo_name, name))
        if perm != policy_perm:
            print('Error: permission to "{}" is too low for team "{}".'.format(repo_name, name))

    if config.get_team(conf, name):
        for member in schema.team_members(rstate, team):
            check_team_member(rstate, conf, policy_, team, member)


def check_team_member(rstate, conf, policy_, team, member):
    """Team compliance check:

    check 1: check that the member should be part of the team
    check 2: check that the team has proper role
    """
    # name = schema.team_name(team)
    # login = schema.user_login(member)
    # TODO user_map
    # email = user_map.email(login)
    # if email and email not in config.get_team(name):
    #     print('Error: {} should not be part of the team "{}".'.format(login, name))
    # TODO check member role


def check_user(rstate, conf, policy_, user):
    login = schema.user_login(user)
    # TODO user_map
    # email = user_map.email(login)
    email = None
    if not email:
        print('Error: member login "{}" is not mapped.'.format(login))


def check_all(conf, usermap, policies):
    rstate = cache.load()
    policy_ = policies[0]
    for member in schema.org_members(rstate):
        check_user(rstate, conf, policy_, member)
    for team in schema.org_teams(rstate):
        check_team(rstate, conf, policy_, team)
    for repo in schema.org_repositories(rstate):
        check_repo(rstate, conf, policy_, repo)
    check_missing_teams(rstate, conf, policy_)
    check_missing_repos(rstate, conf, policy_)
