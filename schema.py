
def get_team_by_id(rstate, team_id):
    teams = rstate['data']['organization']['teams']['edges']
    elems = [x for x in teams if x['node']['id'] == team_id]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def get_team_by_name(rstate, name):
    teams = rstate['data']['organization']['teams']['edges']
    elems = [x for x in teams if x['node']['name'] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def get_repo_by_id(rstate, repo_id):
    repos = rstate['data']['organization']['repositories']['edges']
    elems = [x for x in repos if x['node']['id'] == repo_id]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def get_repo_by_name(rstate, name):
    repos = rstate['data']['organization']['repositories']['edges']
    elems = [x for x in repos if x['node']['name'] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def get_user_by_id(rstate, user_id):
    users = rstate['data']['organization']['membersWithRole']['edges']
    elems = [x for x in users if x['node']['id'] == user_id]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def repo_archived(repo):
    return repo['node']['isArchived']


def repo_forked(repo):
    return repo['node']['isFork']


def repo_name(repo):
    return repo['node']['name']


def team_name(team):
    return team['node']['name']


def team_repos(rstate, team):
    def mkobj(rstate, edge):
        return {
            'permission': edge['permission'],
            'node': get_repo_by_id(rstate, edge['node']['id'])['node']
        }
    if 'repositories' in team['node'] and team['node']['repositories']:
        return [mkobj(rstate, x) for x in team['node']['repositories']['edges'] if x is not None]
    return []


def team_members(rstate, team):
    def mkobj(rstate, edge):
        return {
            'role': edge['role'],
            'node': get_user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'members' in team['node'] and team['node']['members']:
        return [mkobj(rstate, x) for x in team['node']['members']['edges'] if x is not None]
    return []


def repo_collaborators(rstate, repo):
    def mkobj(rstate, edge):
        return {
            'role': edge['permission'],
            'node': get_user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'collaborators' in repo['node'] and repo['node']['collaborators']:
        return [mkobj(rstate, x) for x in repo['node']['collaborators']['edges'] if x is not None]
    return []


def user_name(user):
    return user['node']['name']


def user_login(user):
    return user['node']['login']


def org_repositories(rstate):
    try:
        return rstate['data']['organization']['repositories']['edges']
    except KeyError:
        return []


def org_teams(rstate):
    try:
        return rstate['data']['organization']['teams']['edges']
    except KeyError:
        return []


def org_members(rstate):
    try:
        return rstate['data']['organization']['membersWithRole']['edges']
    except KeyError:
        return []


def empty():
    return {}


def merge_team(old_value, new_value):
    result = old_value
    # print('merge old:')
    # print(old_value)
    # print('merge new:')
    # print(new_value)
    repositories = old_value['node']['repositories'] if 'repositories' in old_value['node'] else {'edges': []}
    members = old_value['node']['members'] if 'repositories' in old_value['node'] else {'edges': []}
    if 'repositories' in new_value['node'] and new_value['node']['repositories']:
        for item in new_value['node']['repositories']['edges']:
            if item:
                repositories['edges'].append(item)
    if 'members' in new_value['node'] and new_value['node']['members']:
        for item in new_value['node']['members']['edges']:
            if item:
                members['edges'].append(item)
    result['node']['repositories'] = repositories
    result['node']['members'] = members
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
    if 'collaborators' in new_value['node'] and new_value['node']['collaborators']:
        for item in new_value['node']['collaborators']['edges']:
            if item:
                collaborators['edges'].append(item)
    result['node']['collaborators'] = collaborators
    # print('merge result:')
    # print(result)
    return result


def merge_members(old_value, new_value):
    print('merge old:')
    print(old_value)
    print('merge new:')
    print(new_value)
    assert False


def merge(rstate, new_data):
    if not rstate:
        return new_data
    # print('>> #############')
    # print(new_data)
    funcs = {
        'teams': {
            'get_by_id': get_team_by_id,
            'merge': merge_team,
        },
        'repositories': {
            'get_by_id': get_repo_by_id,
            'merge': merge_repo,
        },
        'membersWithRole': {
            'get_by_id': get_user_by_id,
            'merge': merge_members,
        }
    }
    for key in ['repositories', 'teams', 'membersWithRole']:
        if key in new_data['data']['organization']:
            for item in new_data['data']['organization'][key]['edges']:
                existing_item = funcs[key]['get_by_id'](rstate, item['node']['id'])
                if existing_item:
                    new_list = [x for x in rstate['data']['organization'][key]['edges'] if x['node']['id'] != item['node']['id']]
                    new_list.append(funcs[key]['merge'](existing_item, item))
                    rstate['data']['organization'][key]['edges'] = new_list
                else:
                    rstate['data']['organization'][key]['edges'].append(item)
    if 'repository' in new_data['data']['organization']:
        repo = new_data['data']['organization']['repository']
        new_list = [x for x in rstate['data']['organization']['repositories']['edges'] if x['node']['id'] != repo['id']]
        new_list.append(merge_repo(get_repo_by_id(rstate, repo['id']), {'node': repo}))
        rstate['data']['organization']['repositories']['edges'] = new_list
    # print('<< #############')
    return rstate
