from ghaudit import schema


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


# chekc if perm1 is higher than perm2
def perm_higher(perm1, perm2):
    assert perm1 in ['read', 'write', 'admin']
    if perm1 == 'read':
        return perm2 != perm1
    if perm1 == 'write':
        return perm2 == 'admin'
    # then perm1 == 'admin'
    return False


def team_repo_perm(policy, team, repo):
    if schema.repo_name(repo) not in get_repos(policy):
        return None
    for perm in ['read', 'write', 'admin']:
        if perm not in policy:
            continue
        if schema.team_name(team) in policy[perm]:
            return perm
    return None
