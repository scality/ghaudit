from functools import reduce
from collections import namedtuple
import operator

from ghaudit import schema
from ghaudit import config
from ghaudit import user_map

# todo switch to enum at least for access level

BranchProtectionRule = namedtuple('BranchProtectionRule', 'model mode')


class Policy:
    def __init__(self):
        self._default_visibility = None     # str
        self._repos = {}                    # repo_name -> visibility
        self._repos_blacklist = []          # repo_name
        self._team_access = {}              # team_name + repo_name -> access
        self._user_access = {}              # login + repo_name -> access
        self._branch_protection = {}        # repo_name -> (model_name, mode_
        self._branch_protection_model = {}  # model_name -> model_data

    @staticmethod
    def team_access_key(team, repo):
        return '{},{}'.format(team, repo)

    @staticmethod
    def user_access_key(login, repo):
        return '{},{}'.format(login, repo)

    def add_merge_rule(self, rule):
        # print('loading rule {}'.format(rule['name']))
        repos = rule['repositories']
        if 'team access' in rule:
            for level, teams in rule['team access'].items():
                assert level in ['read', 'write', 'admin']
                # print('adding rule part: name={} level={} teams={} repos={}'.format(
                #     rule['name'], level, teams, repos
                # ))
                for team in teams:
                    for repo in repos:
                        assert repo not in self._repos_blacklist
                        if repo not in self._repos:
                            self._repos[repo] = None
                        key = Policy.team_access_key(team, repo)
                        if key in self._team_access:
                            self._team_access[key] = perm_highest(level, self._team_access[key])
                        else:
                            self._team_access[key] = level

        if 'branch protection rules' in rule:
            for bprule in rule['branch protection rules']:
                for repo in repos:
                    value = BranchProtectionRule(
                        bprule['model'], bprule['mode']
                    )
                    pattern = bprule['pattern']
                    if repo in self._branch_protection:
                        assert pattern not in self._branch_protection[repo]
                        self._branch_protection[repo][pattern] = value
                    else:
                        self._branch_protection[repo] = {pattern: value}

    def add_repository_blacklist(self, repo):
        assert repo not in self._repos
        self._repos_blacklist.append(repo)

    def add_repository(self, repo_data):
        # print('adding repo from conf: {}'.format(repo_data))
        name = repo_data['repo']
        visibility = repo_data['visibility']
        assert visibility in ['public', 'private']
        assert name not in self._repos_blacklist
        if name in self._repos:
            assert not self._repos[name] or self._repos[name] == visibility
        self._repos[name] = visibility

    def set_default_visibility(self, visibility):
        assert not self._default_visibility or self._default_visibility == visibility
        assert visibility in ['private', 'public']
        self._default_visibility = visibility

    def sanity_check(self):
        intersection = [v for v in self._repos if v in self._repos_blacklist]
        assert not intersection
        # todo assert that either _default_visibility is not none, or that every
        # repository has an explicit visibility
        for bprule in reduce(lambda a, b: a + list(b.values()), self._branch_protection.values(), []):
            assert(bprule.model in self._branch_protection_model)

    def load_config(self, data):
        if 'repositories' in data:
            repos_config = data['repositories']
            if 'exceptions' in repos_config:
                for repo in repos_config['exceptions']:
                    self.add_repository_blacklist(repo)
            if 'default visibility' in repos_config:
                value = repos_config['default visibility']
                self.set_default_visibility(value)
            for repo_data in repos_config['visibility']:
                self.add_repository(repo_data)

        if 'policy' in data:
            if 'rules' in data['policy']:
                for rule in data['policy']['rules']:
                    self.add_merge_rule(rule)

            if 'exceptions' in data['policy']:
                for perm_exception in data['policy']['exceptions']:
                    repo = perm_exception['repo']
                    login = perm_exception['user']
                    perm = perm_exception['permissions']
                    key = Policy.user_access_key(login, repo)
                    assert repo not in self._repos_blacklist
                    self._user_access[key] = perm

        if 'branch protection models' in data:
            for model in data['branch protection models']:
                name = model.pop('name')
                self._branch_protection_model[name] = model

    def team_repo_perm(self, team, repo):
        key = Policy.team_access_key(team, repo)
        if key in self._team_access:
            return self._team_access[key]
        return None

    def get_repos(self):
        return self._repos.keys()

    def is_excluded(self, repo):
        return repo in self._repos_blacklist

    def user_access(self, login, repo):
        key = Policy.user_access_key(login, repo)
        if key in self._user_access:
            return self._user_access[key]
        return None

    def repo_visibility(self, repo):
        visibility = self._repos[repo] if self._repos[repo] else self._default_visibility
        assert visibility
        return visibility

    def branch_protection_patterns(self, repo):
        if repo in self._branch_protection:
            return self._branch_protection[repo].keys()
        return []

    def branch_protection_get(self, repo, pattern):
        return self._branch_protection[repo][pattern]

    def branch_protection_get_model(self, modelname):
        return self._branch_protection_model[modelname]


def bprule_model_approvals(model):
    return model['requirements']['approvals']


def bprule_model_owner_approval(model):
    return model['requirements']['owner approval']


def bprule_model_commit_signatures(model):
    return model['requirements']['commit signatures']


def bprule_model_linear_history(model):
    return model['requirements']['linear history']


def bprule_model_admin_enforced(model):
    return model['requirements']['admin enforced']


def bprule_model_restrict_pushes(model):
    return model['restrictions']['push']['enable']


def bprule_model_restrict_deletion(model):
    return model['restrictions']['deletion']['enable']


def bprule_cmp(policy, rule, modelname, mode):
    def cmp_bool_baseline(from_rule, from_model):
        return (from_model and from_rule) or not from_model
    def approval_cmp_baseline(from_rule, from_model):
        return not from_model or (from_rule >= from_model)
    model = policy.branch_protection_get_model(modelname)
    get_map = {
        'approvals': (
            schema.branch_protection_approvals,
            bprule_model_approvals
        ),
        'owner approval': (
            schema.branch_protection_owner_approval,
            bprule_model_owner_approval
        ),
        'commit signatures': (
            schema.branch_protection_owner_approval,
            bprule_model_owner_approval
        ),
        'linear history': (
            schema.branch_protection_linear_history,
            bprule_model_linear_history
        ),
        'restrict pushes': (
            schema.branch_protection_restrict_pushes,
            bprule_model_restrict_pushes
        ),
        'restrict deletion': (
            schema.branch_protection_restrict_deletion,
            bprule_model_restrict_deletion
        ),
    }
    cmp_map = {
        'baseline': {
            'approvals': approval_cmp_baseline,
            'owner approval': cmp_bool_baseline,
            'commit signatures': cmp_bool_baseline,
            'linear history': cmp_bool_baseline,
            'restrict pushes': cmp_bool_baseline,
            'restrict deletion': cmp_bool_baseline,
        },
        'strict': {
            'approvals': approval_cmp_baseline,
            'owner approval': operator.eq,
            'commit signatures': operator.eq,
            'linear history': operator.eq,
            'restrict pushes': operator.eq,
            'restrict deletion': operator.eq,
        }
    }
    result = []
    for k, get in get_map.items():
        if not cmp_map[mode][k](get[0](rule), get[1](model)):
            result.append(k)
    return result


def branch_protection_patterns(policy, repo):
    return policy.branch_protection_patterns(repo)


def branch_protection_get(policy, repo, pattern):
    return policy.branch_protection_get(repo, pattern)


def repo_excluded(policy, repo):
    return policy.is_excluded(schema.repo_name(repo))


def repo_in_scope(policy, repo):
    return not repo_excluded(policy, repo) and not (
        schema.repo_archived(repo)
        or schema.repo_forked(repo)
    )


def get_repos(policy):
    return policy.get_repos()


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
        return False
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


def team_repo_explicit_perm(conf, policy, team_name, repo):
    """
    returns the permissions of a team as explicitly defined in the policy,
    without taking into account ancestors permissions
    """
    return policy.team_repo_perm(team_name, schema.repo_name(repo))


def team_repo_effective_perm(conf, policy, conf_team, repo):
    """
    returns the effective permissions of a team, taking into account
    ancestors permissions
    """
    related_teams = config.team_ancestors(conf, conf_team)
    related_teams.add(config.team_name(conf_team))
    perms = [team_repo_explicit_perm(conf, policy, x, repo) for x in related_teams]
    return reduce(perm_highest, perms)


def team_repo_perm(conf, policy, team_name, repo):
    """
    returns the effective permission of a team if the repo
    is part of the policy.
    """
    conf_team = config.get_team(conf, team_name)

    if schema.repo_name(repo) not in get_repos(policy) or not conf_team:
        return None
    return team_repo_effective_perm(conf, policy, conf_team, repo)


def user_perm(conf, policy, usermap, repo, login):
    email = user_map.email(usermap, login)
    if config.is_owner(conf, email):
        return 'admin'
    user_access = policy.user_access(login, schema.repo_name(repo))
    if user_access:
        return user_access
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


def repo_visibility(policy, repo_name):
    return policy.repo_visibility(repo_name)


def test():
    assert not perm_higher('admin', 'admin')
    assert perm_higher('admin', 'write')
    assert perm_higher('admin', 'read')
    assert not perm_higher('write', 'admin')
    assert not perm_higher('write', 'write')
    assert perm_higher('write', 'read')
    assert not perm_higher('read', 'admin')
    assert not perm_higher('read', 'write')
    assert not perm_higher('read', 'read')
    assert perm_highest('admin', 'admin') == 'admin'
    assert perm_highest('admin', 'write') == 'admin'
    assert perm_highest('admin', 'read') == 'admin'
    assert perm_highest('write', 'admin') == 'admin'
    assert perm_highest('write', 'write') == 'write'
    assert perm_highest('write', 'read') == 'write'
    assert perm_highest('read', 'admin') == 'admin'
    assert perm_highest('read', 'write') == 'write'
    assert perm_highest('read', 'read') == 'read'
