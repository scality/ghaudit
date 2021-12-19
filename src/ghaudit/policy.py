import functools
import logging
import operator
from collections import namedtuple
from typing import (
    Any,
    Callable,
    Collection,
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    NewType,
    Optional,
    Set,
    Tuple,
    TypeVar,
    Union,
    cast,
)
from typing import get_args as typing_get_args

from typing_extensions import TypedDict

from ghaudit import config, schema, user_map

Perm = Literal["read", "write", "admin"]
BPRMode = Literal["baseline", "strict"]
Visibility = Literal["public", "private"]
TeamAccessKey = NewType("TeamAccessKey", str)
UserAccessKey = NewType("UserAccessKey", str)
BPRModel_Requirements = TypedDict(
    "BPRModel_Requirements",
    {
        "approvals": int,
        "owner approval": bool,
        "commit signatures": bool,
        "linear history": bool,
        # 'status check': todo
        "up to date": bool,
    },
)


class UserActor(TypedDict):
    type: Literal["User"]
    login: str


class TeamActor(TypedDict):
    type: Literal["Team"]
    name: str


BPRPushAllowance = Union[UserActor, TeamActor]
BPRDismissReviewAllowance = Union[UserActor, TeamActor]


class BPRPushRestriction(TypedDict):
    enable: bool
    exceptions: List[BPRPushAllowance]


class BPRDismissReviewRestriction(TypedDict):
    enable: bool
    exceptions: List[BPRDismissReviewAllowance]


class BPRDeletionRestriction(TypedDict):
    enable: bool


BPRRestrictions = TypedDict(
    "BPRRestrictions",
    {
        "push": BPRPushRestriction,
        "dismiss review": BPRDismissReviewRestriction,
        "deletion": BPRDeletionRestriction,
    },
)
BPRModel = TypedDict(
    "BPRModel",
    {
        "name": str,
        "requirements": BPRModel_Requirements,
        "admin enforced": bool,
        "restrictions": BPRRestrictions,
    },
)
BranchProtectionRule = namedtuple("BranchProtectionRule", ["model", "mode"])


class RawRepoVisibility(TypedDict):
    repo: str
    visibility: Visibility


class RawBPRule(TypedDict):
    pattern: str
    model: str
    mode: BPRMode


RawRule = TypedDict(
    "RawRule",
    {
        "name": str,
        "repositories": Collection[str],
        "team access": Mapping[Perm, str],
        "branch protection rules": Collection[RawBPRule],
    },
)


# pylint: disable=invalid-name
T = TypeVar("T")


def _find_duplicates(
    sequence: Iterable[T],
    hash_func: Optional[Callable[[T], str]] = None,
) -> Set[str]:
    if hash_func:
        hsequence = cast(Iterable[str], map(hash_func, sequence))
    else:
        hsequence = cast(Iterable[str], sequence)
    first_seen = set()  # type: Set[str]
    first_seen_add = first_seen.add
    duplicates = set(
        i for i in hsequence if i in first_seen or first_seen_add(i)
    )
    return duplicates


class Policy:
    def __init__(self) -> None:
        self._default_visibility = None  # type: Optional[Visibility]
        self._repos = {}  # type: MutableMapping[str, Optional[Visibility]]
        self._repos_blacklist = []  # type: List[str]
        self._team_access = (
            {}
        )  # type: MutableMapping[TeamAccessKey, Optional[Perm]]
        self._user_access = {}  # type: MutableMapping[UserAccessKey, Perm]
        self._branch_protection = (
            {}
        )  # type: MutableMapping[str, MutableMapping[str, BranchProtectionRule]]
        self._branch_protection_model = (
            {}
        )  # type: MutableMapping[str, BPRModel]
        self._load_errors = []  # type: List[str]

    @staticmethod
    def team_access_key(team: str, repo: str) -> TeamAccessKey:
        return TeamAccessKey("{},{}".format(team, repo))

    @staticmethod
    def user_access_key(login: str, repo: str) -> UserAccessKey:
        return UserAccessKey("{},{}".format(login, repo))

    def _add_merge_rule_team_access(
        self,
        name: str,
        team_access: Mapping[Perm, str],
        repos: Collection[str],
    ) -> None:
        for level, teams in team_access.items():
            logging.debug(
                "adding rule part: name=%s level=%s for %s teams to %s repos",
                name,
                level,
                len(teams),
                len(repos),
            )
            if level not in typing_get_args(Perm):
                # pylint: disable=line-too-long
                msg = 'Error: Invalid access level "{}" in rule "{}". Accepted values are "{}"'  # noqa: E501
                self._load_errors.append(
                    msg.format(level, name, list(typing_get_args(Perm)))
                )
                continue
            for team in teams:
                for repo in repos:
                    if repo not in self._repos:
                        self._repos[repo] = None
                    key = Policy.team_access_key(team, repo)
                    if key in self._team_access:
                        self._team_access[key] = perm_highest(
                            level, self._team_access[key]
                        )
                    else:
                        self._team_access[key] = level

    def _add_merge_rule_bpr(
        self,
        bprules: Collection[RawBPRule],
        repos: Collection[str],
    ) -> None:
        for bprule in bprules:
            for repo in repos:
                value = BranchProtectionRule(bprule["model"], bprule["mode"])
                pattern = bprule["pattern"]
                if repo in self._branch_protection:
                    if pattern in self._branch_protection[repo]:
                        # pylint: disable=line-too-long
                        msg = 'Error: duplicated branch protection rule for repository "{}" and pattern "{}"'  # noqa: E501
                        self._load_errors.append(msg.format(repo, pattern))
                        continue
                    self._branch_protection[repo][pattern] = value
                else:
                    self._branch_protection[repo] = {pattern: value}

    def add_merge_rule(self, rule: RawRule) -> None:
        logging.debug("loading rule %s", rule["name"])

        if "team access" not in rule or "branch protection rules" not in rule:
            print("Empty rule named {}".format(rule["name"]))

        repos = rule["repositories"]

        duplicates = _find_duplicates(repos)
        if duplicates:
            # pylint: disable=line-too-long
            msg = 'Error: duplicate definition of the repository "{}" in rule "{}"'  # noqa: E501
            self._load_errors.append(msg.format(duplicates, rule["name"]))

        if "team access" in rule:
            self._add_merge_rule_team_access(
                rule["name"], rule["team access"], repos
            )

        if "branch protection rules" in rule:
            self._add_merge_rule_bpr(rule["branch protection rules"], repos)

    def add_repository_blacklist(self, repo: str) -> None:
        logging.info("will ignore repository: %s", repo)
        self._repos_blacklist.append(repo)

    def add_repository(self, repo_data: RawRepoVisibility) -> None:
        name = repo_data["repo"]
        visibility = repo_data["visibility"]
        if visibility not in typing_get_args(Visibility):
            # pylint: disable=line-too-long
            msg = 'Error: invalid value for repository visibility "{}". Repository: "{}". Accepted values are "{}"'  # noqa: E501
            msg = msg.format(
                visibility, name, list(typing_get_args(Visibility))
            )
            self._load_errors.append(msg)

        if name in self._repos:
            if self._repos[name] or self._repos[name] != visibility:
                # pylint: disable=line-too-long
                msg = 'Error: defining repository visibility more than once for repository "{}"'  # noqa
                self._load_errors.append(msg.format(name))

        self._repos[name] = visibility

    def set_default_visibility(self, visibility: Visibility) -> None:
        if self._default_visibility and self._default_visibility != visibility:
            # pylint: disable=line-too-long
            msg = "Error: redefining default repository visibility to a different value ({}, already set to {})."  # noqa: E501
            self._load_errors.append(
                msg.format(visibility, self._default_visibility)
            )

        if visibility not in typing_get_args(Visibility):
            # pylint: disable=line-too-long
            msg = 'Error: invalid value for repository visibility "{}". Accepted values are "{}".'  # noqa
            self._load_errors.append(
                msg.format(visibility, list(typing_get_args(Visibility)))
            )

        self._default_visibility = visibility

    def sanity_check(self) -> None:
        intersection = [v for v in self._repos if v in self._repos_blacklist]
        if intersection:
            msg = 'Error: trying do use repositories set to be ignored: "{}".'
            self._load_errors.append(msg.format(intersection))
        if not self._default_visibility:
            not_defined = filter(
                lambda x: x[1],
                self._repos.items(),
            )
            # pylint: disable=line-too-long
            msg = 'Error: default visibility is not defined, and no visibility is defined for the following repositories either: "{}"'  # noqa: E501
            self._load_errors.append(msg.format(list(not_defined)))
        allbprules = functools.reduce(
            lambda a, b: a + list(b.values()),
            self._branch_protection.values(),
            [],
        )  # type: List[BranchProtectionRule]
        for bprule in allbprules:
            if bprule.model not in self._branch_protection_model:
                # pylint: disable=line-too-long
                msg = 'Error: referencing branch protection that is not defined "{}"'  # noqa: E501
                self._load_errors.append(msg.format(bprule.model))

    def _load_config_repositories(self, repos_config: Mapping) -> None:
        duplicates = _find_duplicates(
            repos_config["visibility"],
            cast(Callable[[Mapping[str, str]], str], lambda x: x["repo"]),
        )
        if duplicates:
            # pylint: disable=line-too-long
            msg = 'Error: defining more than once the visibility of the following repositories: "{}"'  # noqa: E501
            self._load_errors.append(msg.format(duplicates))

        if "default visibility" in repos_config:
            value = repos_config["default visibility"]
            self.set_default_visibility(value)
        for repo_data in repos_config["visibility"]:
            self.add_repository(repo_data)

        if "exceptions" in repos_config and repos_config["exceptions"]:
            duplicates = _find_duplicates(repos_config["exceptions"])
            if duplicates:
                # pylint: disable=line-too-long
                msg = 'Error: trying to ignore the following repositories more than once: "{}"'  # noqa: E501
                self._load_errors.append(msg.format(duplicates))

            for repo in repos_config["exceptions"]:
                self.add_repository_blacklist(repo)

    def _load_config_policy(self, policy_config: Mapping) -> None:
        if "rules" in policy_config:
            for rule in policy_config["rules"]:
                self.add_merge_rule(rule)

            if "exceptions" in policy_config:
                for perm_exception in policy_config["exceptions"]:
                    repo = perm_exception["repo"]
                    login = perm_exception["user"]
                    perm = perm_exception["permissions"]
                    key = Policy.user_access_key(login, repo)
                    self._user_access[key] = perm
                    if repo not in self._repos:
                        self._repos[repo] = None

    def _load_config_post_check_repositories(
        self, repos_config: Mapping
    ) -> None:
        if "exceptions" in repos_config:
            for repo in repos_config["exceptions"]:
                if repo in self._repos:
                    # pylint: disable=line-too-long
                    msg = 'Error: trying to ignore repositories defined elsewhere: "{}".'  # noqa
                    self._load_errors.append(msg.format(repo))

        for repo_data in repos_config["visibility"]:
            name = repo_data["repo"]
            if name in self._repos_blacklist:
                # pylint: disable=line-too-long
                msg = 'Error: trying to ignore and specify the visibility of repositories at the same time: "{}".'  # noqa
                self._load_errors.append(msg.format(name))

    def load_config(self, data: Mapping) -> None:
        if "repositories" in data:
            self._load_config_repositories(data["repositories"])

        if "policy" in data:
            self._load_config_policy(data["policy"])

        if "branch protection models" in data:
            for model in data["branch protection models"]:
                name = model.pop("name")
                self._branch_protection_model[name] = model

        if "repositories" in data:
            self._load_config_post_check_repositories(data["repositories"])

        self.sanity_check()

        if self._load_errors:
            err = list(set(self._load_errors))
            err.sort()
            err.insert(0, "Invalid Policy configuration")
            raise RuntimeError(" \n".join(err))

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
        visibility = (
            self._repos[repo]
            if self._repos[repo]
            else self._default_visibility
        )
        assert visibility  # nosec: testing only
        return visibility

    def branch_protection_patterns(self, repo_name: str) -> Collection[str]:
        if repo_name in self._branch_protection:
            return self._branch_protection[repo_name].keys()
        return []

    def branch_protection_get(
        self, repo_name: str, pattern: str
    ) -> BranchProtectionRule:
        return self._branch_protection[repo_name][pattern]

    def branch_protection_get_model(self, modelname: str) -> BPRModel:
        return self._branch_protection_model[modelname]


def bprule_model_approvals(model: BPRModel) -> int:
    return model["requirements"]["approvals"]


def bprule_model_owner_approval(model: BPRModel) -> bool:
    return model["requirements"]["owner approval"]


def bprule_model_commit_signatures(model: BPRModel) -> bool:
    return model["requirements"]["commit signatures"]


def bprule_model_linear_history(model: BPRModel) -> bool:
    return model["requirements"]["linear history"]


def bprule_model_admin_enforced(model: BPRModel) -> bool:
    return model["admin enforced"]


def bprule_model_restrict_pushes(model: BPRModel) -> bool:
    return model["restrictions"]["push"]["enable"]


def bprule_model_push_allowances(model: BPRModel) -> List[BPRPushAllowance]:
    return model["restrictions"]["push"]["exceptions"]


def bprule_model_push_allowance_type(
    push_allowance: BPRPushAllowance,
) -> schema.ActorType:
    return push_allowance["type"]


def bprule_model_push_allowance_user_login(push_allowance: UserActor) -> str:
    return push_allowance["login"]


def bprule_model_push_allowance_team_name(push_allowance: TeamActor) -> str:
    return push_allowance["name"]


# def bprule_model_push_allowance_app_name(push_allowance):
#     return push_allowance["name"]


def bprule_model_restrict_deletion(model: BPRModel) -> bool:
    return model["restrictions"]["deletion"]["enable"]


def cmp_actor(
    rstate: schema.Rstate,
    from_rule: schema.PushAllowance,
    from_model: BPRPushAllowance,
) -> bool:
    get_map = {
        "User": (
            lambda x: schema.user_login(schema.actor_get_user(rstate, x)),
            bprule_model_push_allowance_user_login,
        ),
        "Team": (
            lambda x: schema.team_name(schema.actor_get_team(rstate, x)),
            bprule_model_push_allowance_team_name,
        ),
        # TODO support app
        # 'App': (
        #     lambda x: ,
        #     lambda x: bprule_model_push_allowance_app_name(x)
        # ),
    }  # type: Mapping[str, Tuple[Callable[[schema.Actor], str], Callable[[Any], str]]]
    actor_from_rule = schema.push_allowance_actor(from_rule)
    from_rule_type = schema.actor_type(actor_from_rule)
    from_model_type = bprule_model_push_allowance_type(from_model)
    logging.debug(
        "comparing %s and %s",
        {"User": schema.actor_get_user, "Team": schema.actor_get_team}[
            from_rule_type
        ](rstate, actor_from_rule),
        from_model,
    )
    if from_rule_type == from_model_type:
        getters = get_map[from_model_type]
        return getters[0](actor_from_rule) == getters[1](from_model)
    return False


def cmp_actors_baseline(
    rstate: schema.Rstate,
    from_rules: Iterable[schema.PushAllowance],
    from_models: List[BPRPushAllowance],
) -> bool:
    logging.debug(
        "cmp baseline models: %s, rules: %s", from_models, from_rules
    )
    for from_rule in from_rules:
        predicate = functools.partial(cmp_actor, rstate, from_rule)
        for matched in filter(predicate, from_models):
            from_models.remove(matched)
    return not len(from_models) > 0


def cmp_actors_strict(rstate: schema.Rstate, from_rules, from_models) -> bool:
    if len(from_rules) != len(from_models):
        return False
    return cmp_actors_baseline(rstate, from_rules, from_models)


def bprule_cmp(
    rstate: schema.Rstate,
    policy: Policy,
    rule: schema.BranchProtectionRuleNode,
    modelname: str,
    mode: BPRMode,
) -> List[str]:
    def cmp_bool_baseline(from_rule: bool, from_model: bool) -> bool:
        return from_rule if from_model else not from_model

    model = policy.branch_protection_get_model(modelname)
    get_map = {
        "approvals": (
            schema.branch_protection_approvals,
            bprule_model_approvals,
        ),
        "owner approval": (
            schema.branch_protection_owner_approval,
            bprule_model_owner_approval,
        ),
        "commit signatures": (
            schema.branch_protection_owner_approval,
            bprule_model_owner_approval,
        ),
        "linear history": (
            schema.branch_protection_linear_history,
            bprule_model_linear_history,
        ),
        "restrict pushes": (
            schema.branch_protection_restrict_pushes,
            bprule_model_restrict_pushes,
        ),
        "restrict deletion": (
            schema.branch_protection_restrict_deletion,
            bprule_model_restrict_deletion,
        ),
        "push allowances": (
            schema.branch_protection_push_allowances,
            bprule_model_push_allowances,
        ),
        "admin enforced": (
            schema.branch_protection_admin_enforced,
            bprule_model_admin_enforced,
        ),
    }
    cmp_map = {
        "baseline": {
            "approvals": operator.ge,
            "owner approval": cmp_bool_baseline,
            "commit signatures": cmp_bool_baseline,
            "linear history": cmp_bool_baseline,
            "restrict pushes": cmp_bool_baseline,
            "restrict deletion": cmp_bool_baseline,
            "push allowances": lambda a, b: cmp_actors_baseline(rstate, a, b),
            "admin enforced": cmp_bool_baseline,
        },
        "strict": {
            "approvals": operator.eq,
            "owner approval": operator.eq,
            "commit signatures": operator.eq,
            "linear history": operator.eq,
            "restrict pushes": operator.eq,
            "restrict deletion": operator.eq,
            "push allowances": lambda a, b: cmp_actors_strict(rstate, a, b),
            "admin enforced": operator.eq,
        },
    }
    result = []
    for k, get in get_map.items():
        if not cmp_map[mode][k](get[0](rule), get[1](model)):
            result.append(k)
    return result


def branch_protection_patterns(
    policy: Policy, repo_name: str
) -> Collection[str]:
    return policy.branch_protection_patterns(repo_name)


def branch_protection_get(
    policy: Policy, repo_name: str, pattern: str
) -> BranchProtectionRule:
    return policy.branch_protection_get(repo_name, pattern)


def repo_excluded(policy: Policy, repo: schema.Repo) -> bool:
    return policy.is_excluded(schema.repo_name(repo))


def repo_in_scope(policy: Policy, repo: schema.Repo) -> bool:
    return not repo_excluded(policy, repo) and not (
        schema.repo_archived(repo) or schema.repo_forked(repo)
    )


def get_repos(policy: Policy) -> Collection[str]:
    return policy.get_repos()


def perm_translate(perm: str) -> Perm:
    perm_map = {
        "READ": "read",
        "WRITE": "write",
        "ADMIN": "admin",
    }  # type: Mapping[str, Perm]
    return perm_map[perm]


# check if perm1 is higher than perm2
def perm_higher(perm1: Perm, perm2: Perm) -> bool:
    assert perm1 in typing_get_args(Perm)  # nosec: testing only
    if perm1 == "read":
        return False
    if perm1 == "write":
        return perm2 == "read"
    # then perm1 == 'admin'
    return perm2 != "admin"


def perm_highest(
    perm1: Optional[Perm], perm2: Optional[Perm]
) -> Optional[Perm]:
    if not perm1 and not perm2:
        return None
    if not perm1:
        return perm2
    if not perm2:
        return perm1
    assert perm1 in typing_get_args(Perm)  # nosec: testing only
    assert perm2 in typing_get_args(Perm)  # nosec: testing only
    if "admin" in [perm1, perm2]:
        return "admin"
    if "write" in [perm1, perm2]:
        return "write"
    return "read"


def team_repo_explicit_perm(
    conf: config.Config, policy: Policy, team_name: str, repo: schema.Repo
) -> Optional[Perm]:
    """
    returns the permissions of a team as explicitly defined in the policy,
    without taking into account ancestors permissions
    """
    del conf
    return policy.team_repo_perm(team_name, schema.repo_name(repo))


def team_repo_effective_perm(
    conf: config.Config,
    policy: Policy,
    conf_team: config.Team,
    repo: schema.Repo,
) -> Optional[Perm]:
    """
    returns the effective permissions of a team, taking into account
    ancestors permissions
    """
    related_teams = config.team_ancestors(conf, conf_team)
    related_teams.add(config.team_name(conf_team))
    perms = [
        team_repo_explicit_perm(conf, policy, x, repo) for x in related_teams
    ]
    return functools.reduce(perm_highest, perms)


def team_repo_perm(
    conf: config.Config, policy: Policy, team_name: str, repo: schema.Repo
) -> Optional[Perm]:
    """
    returns the effective permission of a team if the repository
    is part of the policy.
    """
    conf_team = config.get_team(conf, team_name)

    if schema.repo_name(repo) not in get_repos(policy) or not conf_team:
        return None
    return team_repo_effective_perm(conf, policy, conf_team, repo)


def user_perm(
    conf: config.Config,
    policy: Policy,
    usermap: user_map.UserMap,
    repo: schema.Repo,
    login: str,
) -> Optional[Perm]:
    email = user_map.email(usermap, login)
    if email and config.is_owner(conf, email):
        return "admin"
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
