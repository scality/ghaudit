from functools import reduce
from collections import namedtuple
import operator

from typing import Literal
from typing import Optional
from typing import Mapping
from typing import MutableMapping
from typing import NewType
from typing import Collection
from typing import List

from ghaudit import schema
from ghaudit import config
from ghaudit import user_map

Perm = Literal["read", "write", "admin"]
Visibility = Literal["public", "private"]
TeamAccessKey = NewType('TeamAccessKey', str)
UserAccessKey = NewType('UserAccessKey', str)

BranchProtectionRule = namedtuple('BranchProtectionRule', 'model mode')


class Policy:
    def __init__(self) -> None:
        self._default_visibility = None     # type: Optional[Visibility]
        self._repos = {}                    # type: MutableMapping[str, Optional[Visibility]]
        self._repos_blacklist = []          # type: List[str]
        self._team_access = {}              # type: MutableMapping[TeamAccessKey, Perm]
        self._user_access = {}              # type: MutableMapping[UserAccessKey, Perm]
        self._branch_protection = {}        # type: MutableMapping[str, MutableMapping[str, BranchProtectionRule]]
        self._branch_protection_model = {}  # type: MutableMapping[str, dict]

    @staticmethod
    def team_access_key(team: str, repo: str) -> TeamAccessKey:
        return TeamAccessKey('{},{}'.format(team, repo))

    @staticmethod
    def user_access_key(login: str, repo: str) -> UserAccessKey:
        return UserAccessKey('{},{}'.format(login, repo))

    def add_merge_rule(self, rule) -> None:
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
                            self._team_access[key] = perm_highest(
                                level, self._team_access[key]
                            )
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

    def add_repository_blacklist(self, repo: str) -> None:
        assert repo not in self._repos
        self._repos_blacklist.append(repo)

    def add_repository(self, repo_data: Mapping) -> None:
        # print('adding repo from conf: {}'.format(repo_data))
        name = repo_data['repo']
        visibility = repo_data['visibility']
        assert visibility in ['public', 'private']
        assert name not in self._repos_blacklist
        if name in self._repos:
            assert not self._repos[name] or self._repos[name] == visibility
        self._repos[name] = visibility

    def set_default_visibility(self, visibility: Visibility) -> None:
        assert not self._default_visibility or self._default_visibility == visibility
        assert visibility in ['private', 'public']
        self._default_visibility = visibility

    def sanity_check(self) -> None:
        intersection = [v for v in self._repos if v in self._repos_blacklist]
        assert not intersection
        # todo assert that either _default_visibility is not none, or that every
        # repository has an explicit visibility
        allbprules = reduce(
            lambda a, b: a + list(b.values()),
            self._branch_protection.values(),
            []
        ) # type: List[BranchProtectionRule]
        for bprule in allbprules:
            assert(bprule.model in self._branch_protection_model)

    def load_config(self, data) -> None:
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

    def team_repo_perm(self, team: str, repo: str) -> Optional[Perm]:
        key = Policy.team_access_key(team, repo)
        if key in self._team_access:
            return self._team_access[key]
        return None

    def get_repos(self) -> Collection[str]:
        return self._repos.keys()

    def is_excluded(self, repo: str) -> bool:
        return repo in self._repos_blacklist

    def user_access(self, login: str, repo: str) -> Optional[Perm]:
        key = Policy.user_access_key(login, repo)
        if key in self._user_access:
            return self._user_access[key]
        return None

    def repo_visibility(self, repo: str) -> Visibility:
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
    return model['admin enforced']


def bprule_model_restrict_pushes(model):
    return model['restrictions']['push']['enable']


def bprule_model_push_allowances(model):
    return model['restrictions']['push']['exceptions']


def bprule_model_push_allowance_type(push_allowance):
    return push_allowance['type']


def bprule_model_push_allowance_user_login(push_allowance):
    return push_allowance['login']


def bprule_model_push_allowance_team_name(push_allowance):
    return push_allowance['name']


def bprule_model_push_allowance_app_name(push_allowance):
    return push_allowance['name']


def bprule_model_restrict_deletion(model):
    return model['restrictions']['deletion']['enable']


def cmp_actor(rstate, from_rule, from_model):
    get_map = {
        'User': (
            lambda x: schema.user_login(schema.actor_get_user(rstate, x)),
            lambda x: bprule_model_push_allowance_user_login(x)
        ),
        'Team': (
            lambda x: schema.team_name(schema.actor_get_team(rstate, x)),
            lambda x: bprule_model_push_allowance_team_name(x)
        ),
        # TODO support app
        # 'App': (
        #     lambda x: ,
        #     lambda x: bprule_model_push_allowance_app_name(x)
        # ),
    }
    actor_from_rule = schema.push_allowance_actor(from_rule)
    from_rule_type = schema.actor_type(actor_from_rule)
    from_model_type = bprule_model_push_allowance_type(from_model)
    # print(
    #     'comparing {} and {}'.format({
    #         'User': schema.actor_get_user,
    #         'Team': schema.actor_get_team,
    #         }[from_rule_type](rstate, actor_from_rule), from_model
    #     )
    # )
    if from_rule_type == from_model_type:
        getters = get_map[from_model_type]
        return getters[0](actor_from_rule) == getters[1](from_model)
    return False


def cmp_actors_baseline(rstate, from_rules, from_models):
    print('cmp baseline from models: {}'.format(from_models))
    print('cmp baseline from rules: {}'.format(from_rules))
    to_check = set([tuple(x.items()) for x in from_models])
    for from_rule in from_rules:
        matched = reduce(
            lambda accum, x: accum or x if cmp_actor(rstate, from_rule, {y[0]:y[1] for y in x}) else None,
            to_check,
            None
        )
        if matched:
            to_check.remove(matched)
    return not to_check


def cmp_actors_strict(rstate, from_rules, from_models):
    if len(from_rules) != len(from_models):
        return False
    return cmp_actors_baseline(rstate, from_rules, from_models)


def bprule_cmp(rstate, policy, rule, modelname, mode):
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
        'push allowances': (
            schema.branch_protection_push_allowances,
            bprule_model_push_allowances
        ),
        'admin enforced': (
            schema.branch_protection_admin_enforced,
            bprule_model_admin_enforced
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
            'push allowances': lambda a, b: cmp_actors_baseline(rstate, a, b),
            'admin enforced': cmp_bool_baseline,
        },
        'strict': {
            'approvals': approval_cmp_baseline,
            'owner approval': operator.eq,
            'commit signatures': operator.eq,
            'linear history': operator.eq,
            'restrict pushes': operator.eq,
            'restrict deletion': operator.eq,
            'push allowances': lambda a, b: cmp_actors_strict(rstate, a, b),
            'admin enforced': operator.eq
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


def repo_excluded(policy: Policy, repo) -> bool:
    return policy.is_excluded(schema.repo_name(repo))


def repo_in_scope(policy: Policy, repo) -> bool:
    return not repo_excluded(policy, repo) and not (
        schema.repo_archived(repo)
        or schema.repo_forked(repo)
    )


def get_repos(policy: Policy) -> Collection[str]:
    return policy.get_repos()


def perm_translate(perm: str) -> Perm:
    perm_map = {
        'READ': 'read',
        'WRITE': 'write',
        'ADMIN': 'admin'
    } # type: Mapping[str, Perm]
    return perm_map[perm]


# chek if perm1 is higher than perm2
def perm_higher(perm1: Perm, perm2: Perm) -> bool:
    assert perm1 in ['read', 'write', 'admin']
    if perm1 == 'read':
        return False
    if perm1 == 'write':
        return perm2 == 'read'
    # then perm1 == 'admin'
    return perm2 != 'admin'


def perm_highest(perm1: Perm, perm2: Perm) -> Perm:
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


def team_repo_explicit_perm(conf, policy: Policy, team_name, repo) -> Optional[Perm]:
    """
    returns the permissions of a team as explicitly defined in the policy,
    without taking into account ancestors permissions
    """
    return policy.team_repo_perm(team_name, schema.repo_name(repo))


def team_repo_effective_perm(conf, policy: Policy, conf_team, repo) -> Optional[Perm]:
    """
    returns the effective permissions of a team, taking into account
    ancestors permissions
    """
    related_teams = config.team_ancestors(conf, conf_team)
    related_teams.add(config.team_name(conf_team))
    perms = [team_repo_explicit_perm(conf, policy, x, repo) for x in related_teams]
    return reduce(perm_highest, perms)


def team_repo_perm(conf, policy: Policy, team_name: str, repo) -> Optional[Perm]:
    """
    returns the effective permission of a team if the repo
    is part of the policy.
    """
    conf_team = config.get_team(conf, team_name)

    if schema.repo_name(repo) not in get_repos(policy) or not conf_team:
        return None
    return team_repo_effective_perm(conf, policy, conf_team, repo)


def user_perm(conf, policy: Policy, usermap, repo, login: str) -> Optional[Perm]:
    email = user_map.email(usermap, login)
    if email and config.is_owner(conf, email):
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


def repo_visibility(policy: Policy, repo_name: str) -> Visibility:
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
