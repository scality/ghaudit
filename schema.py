
# internal common

def _get_root(rstate):
    return rstate['data']


def _get_org(rstate):
    return _get_root(rstate)['organization']


def _get_org_teams(rstate):
    return _get_org(rstate)['teams']['edges']


def _get_org_repos(rstate):
    return _get_org(rstate)['repositories']['edges']


def _get_org_members(rstate):
    return _get_org(rstate)['membersWithRole']


def _get_x_by_y(rstate, seq_get, key, value):
    seq = seq_get(rstate)
    return [x for x in seq if x['node'][key] == value]


def _get_unique_x_by_y(rstate, seq_get, key, value):
    elems = _get_x_by_y(rstate, seq_get, key, value)
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None

# users queries


def user_by_login(rstate, login):
    return _get_unique_x_by_y(rstate, users, 'login', login)


def user_by_id(rstate, user_id):
    return rstate['data']['users'].get(user_id)


def users(rstate):
    return rstate['data']['users'].values()

# org queries


def org_repositories(rstate):
    return _get_org_repos(rstate)


def org_teams(rstate):
    return _get_org_teams(rstate)


def org_members(rstate):
    return [user_by_id(rstate, x) for x in _get_org_members(rstate)]


def org_team_by_id(rstate, team_id):
    return _get_unique_x_by_y(rstate, _get_org_teams, 'id', team_id)


def org_team_by_name(rstate, name):
    return _get_unique_x_by_y(rstate, _get_org_teams, 'name', name)


def org_repo_by_id(rstate, repo_id):
    return _get_unique_x_by_y(rstate, _get_org_repos, 'id', repo_id)


def org_repo_by_name(rstate, name):
    return _get_unique_x_by_y(rstate, _get_org_repos, 'name', name)

# repository info


def repo_archived(repo):
    return repo['node']['isArchived']


def repo_forked(repo):
    return repo['node']['isFork']


def repo_private(repo):
    return repo['node']['isPrivate']


def repo_name(repo):
    return repo['node']['name']


def repo_description(repo):
    return repo['node']['description']


def repo_collaborators(rstate, repo):
    def mkobj(rstate, edge):
        return {
            'role': edge['permission'],
            'node': user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'collaborators' in repo['node'] and repo['node']['collaborators']:
        collaborators = repo['node']['collaborators']['edges']
        return [mkobj(rstate, x) for x in collaborators if x is not None]
    return []

# team info


def team_name(team):
    return team['node']['name']


def team_description(team):
    return team['node']['description']


def team_repos(rstate, team):
    def mkobj(rstate, edge):
        return {
            'permission': edge['permission'],
            'node': org_repo_by_id(rstate, edge['node']['id'])['node']
        }
    if 'repositories' in team['node'] and team['node']['repositories']:
        repositories = team['node']['repositories']['edges']
        return [mkobj(rstate, x) for x in repositories if x is not None]
    return []


def team_members(rstate, team):
    def mkobj(rstate, edge):
        return {
            'role': edge['role'],
            'node': user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'members' in team['node'] and team['node']['members']:
        members = team['node']['members']['edges']
        return [mkobj(rstate, x) for x in members if x is not None]
    return []


def team_parent(rstate, team):
    if team['node']['parentTeam']:
        return org_team_by_id(rstate, team['node']['parentTeam']['id'])
    return None


def team_children(rstate, team):
    def mkobj(rstate, edge):
        return {
            'node': org_team_by_id(rstate, edge['node']['id'])['node']
        }
    if 'childTeams' in team['node'] and team['node']['childTeams']:
        children = team['node']['childTeams']['edges']
        return [mkobj(rstate, x) for x in children if x is not None]
    return []

# user info


def user_name(user):
    return user['node']['name']


def user_login(user):
    return user['node']['login']


def user_email(user):
    return user['node']['email']


def user_company(user):
    return user['node']['company']

###


def _user_create(rstate, user):
    assert 'node' in user
    assert 'login' in user['node'] and user['node']['login']
    assert 'id' in user['node'] and user['node']['id']
    assert 'email' in user['node']
    user_id = user['node'].pop('id')
    rstate['data']['users'][user_id] = user
    return rstate


def _org_member_create(rstate, member):
    user_id = member['node']['id']
    rstate = _user_create(rstate, member)
    rstate['data']['organization']['membersWithRole'].append(user_id)
    return rstate


def empty():
    return {
        'data': {
            'users': {},
            'organization': {
                'repositories': {'edges': []},
                'membersWithRole': [],
                'teams': {'edges': []},
            }
        }
    }


def merge_team(old_value, new_value):
    result = old_value
    # print('merge old:')
    # print(old_value)
    # print('merge new:')
    # print(new_value)
    if 'repositories' in old_value['node']:
        repositories = old_value['node']['repositories']
    else:
        repositories = {'edges': []}
    if 'members' in old_value['node']:
        members = old_value['node']['members']
    else:
        members = {'edges': []}
    if 'childTeams' in old_value['node']:
        children = old_value['node']['childTeams']
    else:
        children = {'edges': []}
    if 'repositories' in new_value['node'] \
       and new_value['node']['repositories']:
        for item in new_value['node']['repositories']['edges']:
            if item:
                repositories['edges'].append(item)
    if 'members' in new_value['node'] and new_value['node']['members']:
        for item in new_value['node']['members']['edges']:
            if item:
                members['edges'].append(item)
    if 'childTeams' in new_value['node'] and new_value['node']['childTeams']:
        # print(new_value)
        for item in new_value['node']['childTeams']['edges']:
            if item:
                # print('adding {}'.format(item))
                children['edges'].append(item)
    result['node']['repositories'] = repositories
    result['node']['members'] = members
    result['node']['childTeams'] = children
    # print('merge result:')
    # print(result)
    return result


def merge_repo(old_value, new_value):
    result = old_value
    # print('merge old:')
    # print(old_value)
    # print('merge new:')
    # print(new_value)
    if 'collaborators' in old_value['node']:
        collaborators = old_value['node']['collaborators']
    else:
        collaborators = {'edges': []}
    if 'collaborators' in new_value['node'] \
       and new_value['node']['collaborators']:
        for item in new_value['node']['collaborators']['edges']:
            if item:
                collaborators['edges'].append(item)
    result['node']['collaborators'] = collaborators
    # print('merge result:')
    # print(result)
    return result


def merge_members(old_value, new_value):
    # print('merge old:')
    # print(old_value)
    # print('merge new:')
    # print(new_value)
    assert False


def merge(rstate, alias, new_data):
    funcs = {
        'teams': {
            'get_by_id': org_team_by_id,
            'merge': merge_team,
            'create': lambda rstate, x: org_teams(rstate).append(x),
        },
        'repositories': {
            'get_by_id': org_repo_by_id,
            'merge': merge_repo,
            'create': lambda rstate, x: org_repositories(rstate).append(x),
        },
        'membersWithRole': {
            'get_by_id': user_by_id,
            'merge': merge_members,
            'create': _org_member_create,
        }
    }
    if alias.startswith('user'):
        return _user_create(rstate, {'node': new_data['data']['organization']})
    for key in ['repositories', 'teams', 'membersWithRole']:
        if key in new_data['data']['organization']:
            for item in new_data['data']['organization'][key]['edges']:
                existing_item = funcs[key]['get_by_id'](
                    rstate, item['node']['id']
                )
                if existing_item:
                    edges = rstate['data']['organization'][key]['edges']
                    new_list = [x for x in edges
                                if x['node']['id'] != item['node']['id']]
                    new_list.append(funcs[key]['merge'](existing_item, item))
                    rstate['data']['organization'][key]['edges'] = new_list
                else:
                    funcs[key]['create'](rstate, item)
    if 'repository' in new_data['data']['organization']:
        repo = new_data['data']['organization']['repository']
        edges = rstate['data']['organization']['repositories']['edges']
        new_list = [x for x in edges
                    if x['node']['id'] != repo['id']]
        new_list.append(
            merge_repo(org_repo_by_id(rstate, repo['id']), {'node': repo})
        )
        rstate['data']['organization']['repositories']['edges'] = new_list
    return rstate


def missing_collaborators(rstate, repo):
    missing = []
    if 'collaborators' in repo['node'] and repo['node']['collaborators']:
        edges = repo['node']['collaborators']['edges']
        for edge in [x for x in edges if x is not None]:
            user_id = edge['node']['id']
            if not user_by_id(rstate, user_id):
                missing.append(edge['node']['login'])
    return missing


def validate(rstate):
    # * all repos referenced by teams should be known
    # * all users referenced by teams should be known
    # * all users referenced by repos should be known
    # for team in org_teams(rstate):
    for repo in org_repositories(rstate):
        for missing in missing_collaborators(rstate, repo):
            msg = 'unknown user "{}" referenced as a collaborator of "{}"'
            raise RuntimeError(msg.format(
                missing,
                repo_name(repo),
            ))
    return True
