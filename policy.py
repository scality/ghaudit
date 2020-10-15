from functools import reduce

from ghaudit import schema
from ghaudit import config


def repo_exluded(policy, repo):
    return schema.repo_name(repo) in policy['excluded repositories']


def repo_in_scope(policy, repo):
    return not repo_exluded(policy, repo) and not (
        schema.repo_archived(repo)
        or schema.repo_forked(repo)
    )


def get_repos(policy):
    return policy['repositories']


def perm_translate(perm):
    perm_map = {
        'READ': 'read',
        'WRITE': 'write',
        'ADMIN': 'admin'
    }
    return perm_map[perm]


# chek if perm1 is higher than perm2
def perm_higher(perm1, perm2):
    assert perm1 in ['read', 'write', 'admin']
    if perm1 == 'read':
        return perm2 != perm1
    if perm1 == 'write':
        return perm2 == 'read'
    # then perm1 == 'admin'
    return perm2 != 'admin'


def perm_highest(perm1, perm2):
    if not perm1:
        return perm2
    if not perm2:
        return perm1
    assert perm1 in ['read', 'write', 'admin']
    assert perm2 in ['read', 'write', 'admin']
    if 'admin' in [perm1, perm2]:
        return 'admin'
    if 'write' in [perm1, perm2]:
        return 'write'
    return 'read'


def _team_perm(conf, policy, conf_team):
    perm = None
    parent_perm = None
    parent = config.team_parent(conf, conf_team)

    if parent:
        parent_perm = _team_perm(conf, policy, parent)

    for value in ['read', 'write', 'admin']:
        if value in policy and config.team_name(conf_team) in policy[value]:
            perm = value

    if parent_perm and perm:
        return perm_highest(parent_perm, perm)
    if parent_perm:
        return parent_perm
    if perm:
        return perm
    return None


def team_repo_explicit_perm(conf, policy, team_name):
    """
    returns the permissions of a team as explicitly defined in the policy,
    without taking into account ancestors permissions
    """
    for value in ['read', 'write', 'admin']:
        if value in policy and team_name in policy[value]:
            return value
    return None



def team_repo_effective_perm(conf, policy, conf_team):
    """
    returns the effective permissions of a team, taking into account
    ancestors permissions
    """
    related_teams = config.team_ancestors(conf, conf_team)
    related_teams.add(config.team_name(conf_team))
    perms = [team_repo_explicit_perm(conf, policy, x) for x in related_teams]
    return reduce(perm_highest, perms)


def team_repo_perm(conf, policy, team_name, repo):
    """
    returns the effective permission of a team if the repo
    is part of the policy.
    """
    conf_team = config.get_team(conf, team_name)

    if schema.repo_name(repo) not in get_repos(policy) or not conf_team:
        return None
    return team_repo_effective_perm(conf, policy, conf_team)


def user_perm(rstate, conf, policy, repo, email):
    if not email:
        return None
    policy_user_perm = None
    team_names = [config.team_name(x) for x in config.user_teams(conf, email)]
    for team_name in team_names:
        team_perm = team_repo_perm(conf, policy, team_name, repo)
        if not policy_user_perm:
            policy_user_perm = team_perm
        else:
            policy_user_perm = perm_highest(policy_user_perm, team_perm)
    return policy_user_perm
