
from typing import Optional
from typing import Hashable
from typing import Mapping
from typing import Collection
from typing import List
from typing_extensions import TypedDict

class TeamMemberNode(TypedDict):
    id: Hashable

class TeamMemberEdge(TypedDict):
    node: TeamMemberNode
    role: str

class TeamMemberEdges(TypedDict):
    edges: List[TeamMemberEdge]

class TeamRepoNode(TypedDict):
    id: Hashable

class TeamRepoEdge(TypedDict):
    node: TeamRepoNode
    permission: str

class TeamRepoEdges(TypedDict):
    edges: List[TeamRepoEdge]

class TeamRef(TypedDict):
    id: Hashable

class ChildTeam(TypedDict):
    node: TeamRef

class ChildTeams(TypedDict):
    edges: List[ChildTeam]

class TeamNode(TypedDict):
    name: str
    description: str
    repositories: TeamRepoEdges
    members: TeamMemberEdges
    parentTeam: Optional[TeamRef]
    childTeams: ChildTeams

class Team(TypedDict):
    node: TeamNode

class TeamEdges(TypedDict):
    edges: List[Team]

class UserNode(TypedDict):
    name: Optional[str]
    login: str
    email: str
    company: str

class User(TypedDict):
    node: UserNode

class RepoCollaborator(TypedDict):
    role: str
    node: UserNode

class RepoCollaboratorNode(TypedDict):
    id: Hashable
    login: str

class RepoCollaboratorEdge(TypedDict):
    node: RepoCollaboratorNode
    permission: str

class RepoCollaboratorEdges(TypedDict):
    edges: List[RepoCollaboratorEdge]

class RepoNode(TypedDict):
    name: str
    isArchived: bool
    isFork: bool
    isPrivate: bool
    description: str
    collaborators: RepoCollaboratorEdges

class Repo(TypedDict):
    node: RepoNode

class RepoEdges(TypedDict):
    edges: List[Repo]


OrgUsers = Mapping[Hashable, User]

class Organisation(TypedDict):
    teams: TeamEdges
    repositories: RepoEdges
    membersWithRole: List[Hashable]

class RstateData(TypedDict):
    organization: Organisation
    users: OrgUsers

class Rstate(TypedDict):
    data: RstateData

# internal common

def _get_root(rstate: Rstate) -> RstateData:
    return rstate['data']


def _get_org(rstate: Rstate) -> Organisation:
    return _get_root(rstate)['organization']


def _get_org_teams(rstate: Rstate) -> list[Team]:
    return _get_org(rstate)['teams']['edges']


def _get_org_repos(rstate: Rstate) -> list[Repo]:
    return _get_org(rstate)['repositories']['edges']


def _get_org_members(rstate: Rstate) -> list[Hashable]:
    return _get_org(rstate)['membersWithRole']


def _get_x_by_y(rstate: Rstate, seq_get, key, value):
    seq = seq_get(rstate)
    return [x for x in seq if x['node'][key] == value]


def _get_unique_x_by_y(rstate: Rstate, seq_get, key, value):
    elems = _get_x_by_y(rstate, seq_get, key, value)
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None

# users queries


def user_by_login(rstate: Rstate, login: str) -> str:
    return _get_unique_x_by_y(rstate, users, 'login', login)


def _user_by_id_noexcept(rstate: Rstate, user_id) -> Optional[User]:
    return rstate['data']['users'].get(user_id)


def user_by_id(rstate: Rstate, user_id) -> User:
    user = _user_by_id_noexcept(rstate, user_id)
    assert user
    return user


def users(rstate: Rstate) -> Collection[User]:
    return rstate['data']['users'].values()

# org queries


def org_repositories(rstate: Rstate) -> list[Repo]:
    return _get_org_repos(rstate)


def org_teams(rstate: Rstate) -> list[Team]:
    return _get_org_teams(rstate)


def org_members(rstate: Rstate) -> list[User]:
    return [user_by_id(rstate, x) for x in _get_org_members(rstate)]


def org_team_by_id(rstate: Rstate, team_id) -> Team:
    return _get_unique_x_by_y(rstate, _get_org_teams, 'id', team_id)


def org_team_by_name(rstate: Rstate, name: str) -> Team:
    return _get_unique_x_by_y(rstate, _get_org_teams, 'name', name)


def org_repo_by_id(rstate: Rstate, repo_id) -> Repo:
    return _get_unique_x_by_y(rstate, _get_org_repos, 'id', repo_id)


def org_repo_by_name(rstate: Rstate, name: str) -> Repo:
    return _get_unique_x_by_y(rstate, _get_org_repos, 'name', name)

# repository info


def repo_archived(repo: Repo) -> bool:
    return repo['node']['isArchived']


def repo_forked(repo: Repo) -> bool:
    return repo['node']['isFork']


def repo_private(repo: Repo) -> bool:
    return repo['node']['isPrivate']


def repo_name(repo: Repo) -> str:
    return repo['node']['name']


def repo_description(repo: Repo) -> str:
    return repo['node']['description']


def repo_collaborators(rstate: Rstate, repo: Repo):
    def mkobj(rstate: Rstate, edge: RepoCollaboratorEdge) -> RepoCollaborator:
        return {
            'role': edge['permission'],
            'node': user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'collaborators' in repo['node'] and repo['node']['collaborators']:
        collaborators = repo['node']['collaborators']['edges']
        return [mkobj(rstate, x) for x in collaborators if x is not None]
    return []


def repo_branch_protection_rules(repo):
    return repo['node']['branchProtectionRules']['nodes']


def _repo_branch_protection_rules_noexcept(repo):
    if 'branchProtectionRules' in repo['node']:
        return repo_branch_protection_rules(repo)
    return None


def repo_branch_protection_rule(repo, pattern):
    rules = repo_branch_protection_rules(repo)
    elems = [x for x in rules if branch_protection_pattern(x) == pattern]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None

# team info


def team_name(team: Team) -> str:
    return team['node']['name']


def team_description(team: Team) -> str:
    return team['node']['description']


def team_repos(rstate: Rstate, team: Team) -> list[Repo]:
    def mkobj(rstate: Rstate, edge):
        return {
            'permission': edge['permission'],
            'node': org_repo_by_id(rstate, edge['node']['id'])['node']
        }
    if 'repositories' in team['node'] and team['node']['repositories']:
        repositories = team['node']['repositories']['edges']
        return [mkobj(rstate, x) for x in repositories if x is not None]
    return []


def team_members(rstate: Rstate, team: Team) -> list[User]:
    def mkobj(rstate, edge):
        return {
            'role': edge['role'],
            'node': user_by_id(rstate, edge['node']['id'])['node']
        }
    if 'members' in team['node'] and team['node']['members']:
        members = team['node']['members']['edges']
        return [mkobj(rstate, x) for x in members if x is not None]
    return []


def team_parent(rstate: Rstate, team: Team) -> Optional[Team]:
    parent_team = team['node']['parentTeam']
    if parent_team:
        return org_team_by_id(rstate, parent_team)
    return None


def team_children(rstate: Rstate, team: Team) -> list[Team]:
    def mkobj(rstate, edge):
        return {
            'node': org_team_by_id(rstate, edge['node']['id'])['node']
        }
    if 'childTeams' in team['node'] and team['node']['childTeams']:
        children = team['node']['childTeams']['edges']
        return [mkobj(rstate, x) for x in children if x is not None]
    return []

# user info


def user_name(user: User) -> str:
    return user['node']['name']


def user_login(user: User) -> str:
    return user['node']['login']


def user_email(user: User) -> str:
    return user['node']['email']


def user_company(user: User) -> str:
    return user['node']['company']


def user_is_owner(user):
    return 'role' in user and user['role'] == 'ADMIN'

# branch protection rules


def branch_protection_id(rule):
    return rule['id']


def branch_protection_pattern(rule):
    return rule['pattern']


def branch_protection_admin_enforced(rule):
    return rule['isAdminEnforced']


def branch_protection_approvals(rule):
    if rule['requiresApprovingReviews']:
        return rule['requiredApprovingReviewCount']
    return 0


def branch_protection_owner_approval(rule):
    return rule['requiresCodeOwnerReviews']


def branch_protection_commit_signatures(rule):
    return rule['requiresCommitSignatures']


def branch_protection_linear_history(rule):
    return rule['requiresLinearHistory']


def branch_protection_restrict_pushes(rule):
    return rule['restrictsPushes']


def branch_protection_restrict_deletion(rule):
    return not rule['allowsDeletions']


def branch_protection_creator(rule):
    return rule['creator']['login']


def branch_protection_push_allowances(rule):
    return rule['pushAllowances']


def push_allowance_actor(allowance):
    return allowance['actor']

###

def actor_type(actor):
    return actor['__typename']


def actor_get_user(rstate, actor):
    return user_by_id(rstate, actor['id'])


def actor_get_team(rstate, actor):
    return org_team_by_id(rstate, actor['id'])


def actor_get_app(rstate, actor):
    raise NotImplementedError()

###

def all_bp_rules(rstate: Rstate):
    result = set()
    for repo in org_repositories(rstate):
        bprules = _repo_branch_protection_rules_noexcept(repo)
        if bprules:
            for bprule in bprules:
                result.add(branch_protection_id(bprule))
    return result

###


def _user_create(rstate: Rstate, user: Mapping) -> Rstate:
    assert 'node' in user
    assert 'login' in user['node'] and user['node']['login']
    assert 'id' in user['node'] and user['node']['id']
    assert 'email' in user['node']
    assert isinstance(user['node']['id'], Hashable)
    user_id = user['node'].pop('id')
    rstate['data']['users'][user_id] = user
    return rstate


def _org_member_create(rstate: Rstate, member: Mapping) -> Rstate:
    user_id = member['node']['id']
    rstate = _user_create(rstate, member)
    rstate['data']['organization']['membersWithRole'].append(user_id)
    return rstate


def empty() -> Rstate:
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


def merge_team(old_value: Team, new_value: Mapping) -> Team:
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

    if 'branchProtectionRules' in old_value['node']:
        branch_protection_rules = old_value['node']['branchProtectionRules']
    else:
        branch_protection_rules = {'nodes': []}
    if 'branchProtectionRules' in new_value['node'] \
       and new_value['node']['branchProtectionRules']:
        for item in new_value['node']['branchProtectionRules']['nodes']:
            if item:
                item['pushAllowances'] = []
                branch_protection_rules['nodes'].append(item)

    result['node']['collaborators'] = collaborators
    result['node']['branchProtectionRules'] = branch_protection_rules
    # print('merge result:')
    # print(result)
    return result


def merge_repo_branch_protection(repo, push_allowance):
    assert 'branchProtectionRules' in repo['node']
    bprule_id = push_allowance['branchProtectionRule']['id']
    # del push_allowance['branchProtectionRule']
    bprule = [x for x in repo_branch_protection_rules(repo) if x['id'] == bprule_id][0]
    rules_filtered = [x for x in repo_branch_protection_rules(repo) if x['id'] != bprule_id]
    bprule['pushAllowances'].append(push_allowance)
    rules_filtered.append(bprule)
    repo['node']['branchProtectionRules']['nodes'] = rules_filtered
    return repo

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
            'get_by_id': _user_by_id_noexcept,
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
        if 'pushAllowances' in new_data['data']['organization']:
            print('found push allowances')
            for item in new_data['data']['organization']['pushAllowances']['nodes']:
                repo = org_repo_by_id(
                    rstate, item['branchProtectionRule']['repository']['id']
                )
                edges = rstate['data']['organization']['repositories']['edges']
                new_list = [x for x in edges
                                if x['node']['id'] != repo['node']['id']]
                new_list.append(merge_repo_branch_protection(repo, item))
                rstate['data']['organization']['repositories']['edges'] = new_list
    if 'repository' in new_data['data']['organization']:
        repo = new_data['data']['organization']['repository']
        edges = rstate['data']['organization']['repositories']['edges']
        new_list = [x for x in edges
                    if x['node']['id'] != repo['id']]
        new_list.append(
            merge_repo(org_repo_by_id(rstate, repo['id']), {'node': repo})
        )
        rstate['data']['organization']['repositories']['edges'] = new_list
    if 'team' in new_data['data']['organization']:
        team = new_data['data']['organization']['team']
        merge_team(org_team_by_id(rstate, team['id']), {'node': team})
    return rstate


def missing_collaborators(rstate: Rstate, repo: Repo) -> list[str]:
    missing = []
    if 'collaborators' in repo['node'] and repo['node']['collaborators']:
        edges = repo['node']['collaborators']['edges']
        for edge in [x for x in edges if x is not None]:
            user_id = edge['node']['id']
            if not _user_by_id_noexcept(rstate, user_id):
                missing.append(edge['node']['login'])
    return missing


def validate(rstate: Rstate) -> bool:
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
