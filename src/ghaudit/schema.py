import logging
from typing import (
    Any,
    Callable,
    Collection,
    Hashable,
    Iterable,
    List,
    Literal,
    Mapping,
    MutableMapping,
    Optional,
    Set,
    cast,
)

from typing_extensions import TypedDict

TeamRole = Literal["MEMBER", "MAINTAINER"]
OrgRole = Literal["MEMBER", "ADMIN"]
CollaboratorRole = Literal["MEMBER", "ADMIN"]

UserID = Hashable
TeamID = Hashable
RepoID = Hashable


class TeamMemberNode(TypedDict):
    id: UserID


class TeamMemberEdge(TypedDict):
    node: TeamMemberNode
    role: TeamRole


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
    id: TeamID
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
    id: UserID
    name: Optional[str]
    login: str
    email: str
    company: str


class User(TypedDict):
    node: UserNode


class UserWithRole(User):
    role: TeamRole


class UserWithOrgRole(User):
    role: OrgRole


class RepoCollaborator(TypedDict):
    role: CollaboratorRole
    node: UserNode


class RepoCollaboratorNode(TypedDict):
    id: Hashable
    login: str


class RepoCollaboratorEdge(TypedDict):
    node: RepoCollaboratorNode
    permission: CollaboratorRole


class RepoCollaboratorEdges(TypedDict):
    edges: List[RepoCollaboratorEdge]


ActorType = Literal["User", "Team"]


class Actor(TypedDict):
    id: Hashable
    # pylint: disable=unused-private-member
    __typename: ActorType


BranchProtectionRuleID = Hashable


# pylint: disable=too-few-public-methods
class BPRReferenceRepoID:
    id: Hashable


class BPRReference(TypedDict):
    id: BranchProtectionRuleID
    repository: BPRReferenceRepoID


class PushAllowance(TypedDict):
    actor: Actor
    branchProtectionRule: BPRReference
    # ...


class BranchProtectionRuleCreator(TypedDict):
    login: str


class BranchProtectionRuleNode(TypedDict):
    id: BranchProtectionRuleID
    pattern: str
    isAdminEnforced: bool
    requiresApprovingReviews: bool
    requiredApprovingReviewCount: int
    requiresCodeOwnerReviews: bool
    requiresCommitSignatures: bool
    requiresLinearHistory: bool
    restrictsPushes: bool
    restrictsReviewDismissals: bool
    allowsDeletions: bool
    pushAllowances: List[PushAllowance]
    creator: BranchProtectionRuleCreator


class BranchProtectionRules(TypedDict):
    nodes: List[BranchProtectionRuleNode]


class RepoNode(TypedDict):
    id: RepoID
    name: str
    isArchived: bool
    isFork: bool
    isPrivate: bool
    description: str
    collaborators: RepoCollaboratorEdges
    branchProtectionRules: BranchProtectionRules


class Repo(TypedDict):
    node: RepoNode


class RepoWithPerms(TypedDict):
    node: RepoNode
    permission: str


class RepoEdges(TypedDict):
    edges: List[Repo]


class Organisation(TypedDict):
    teams: TeamEdges
    repositories: RepoEdges
    membersWithRole: List[UserID]


class RstateData(TypedDict):
    organization: Organisation
    users: MutableMapping[UserID, UserWithOrgRole]


class Rstate(TypedDict):
    data: RstateData


class Node(TypedDict):
    node: Mapping


# internal common


def _get_root(rstate: Rstate) -> RstateData:
    return rstate["data"]


def _get_org(rstate: Rstate) -> Organisation:
    return _get_root(rstate)["organization"]


def _get_org_teams(rstate: Rstate) -> List[Team]:
    return _get_org(rstate)["teams"]["edges"]


def _get_org_repos(rstate: Rstate) -> List[Repo]:
    return _get_org(rstate)["repositories"]["edges"]


def _get_org_members(rstate: Rstate) -> List[UserID]:
    return _get_org(rstate)["membersWithRole"]


def _get_x_by_y(
    rstate: Rstate,
    seq_get: Callable[[Rstate], Iterable[Node]],
    key: str,
    value: Any,
) -> Any:
    seq = seq_get(rstate)
    return [x for x in seq if x["node"][key] == value]


def _get_unique_x_by_y(rstate: Rstate, seq_get, key: str, value):
    elems = _get_x_by_y(rstate, seq_get, key, value)
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


# users queries


def user_by_login(rstate: Rstate, login: str) -> UserWithOrgRole:
    return _get_unique_x_by_y(rstate, users, "login", login)


def _user_by_id_noexcept(
    rstate: Rstate, user_id: UserID
) -> Optional[UserWithOrgRole]:
    return rstate["data"]["users"].get(user_id)


def user_by_id(rstate: Rstate, user_id: UserID) -> UserWithOrgRole:
    user = _user_by_id_noexcept(rstate, user_id)
    assert user
    return user


def users(rstate: Rstate) -> Collection[User]:
    return rstate["data"]["users"].values()


# org queries


def org_repositories(rstate: Rstate) -> List[Repo]:
    return _get_org_repos(rstate)


def org_teams(rstate: Rstate) -> List[Team]:
    return _get_org_teams(rstate)


def org_members(rstate: Rstate) -> List[UserWithOrgRole]:
    return [user_by_id(rstate, x) for x in _get_org_members(rstate)]


def org_team_by_id(rstate: Rstate, team_id: TeamID) -> Team:
    return _get_unique_x_by_y(rstate, _get_org_teams, "id", team_id)


def org_team_by_name(rstate: Rstate, name: str) -> Team:
    return _get_unique_x_by_y(rstate, _get_org_teams, "name", name)


def org_repo_by_id(rstate: Rstate, repo_id: RepoID) -> Repo:
    return _get_unique_x_by_y(rstate, _get_org_repos, "id", repo_id)


def org_repo_by_name(rstate: Rstate, name: str) -> Repo:
    return _get_unique_x_by_y(rstate, _get_org_repos, "name", name)


# repository info


def repo_archived(repo: Repo) -> bool:
    return repo["node"]["isArchived"]


def repo_forked(repo: Repo) -> bool:
    return repo["node"]["isFork"]


def repo_private(repo: Repo) -> bool:
    return repo["node"]["isPrivate"]


def repo_name(repo: Repo) -> str:
    return repo["node"]["name"]


def repo_description(repo: Repo) -> str:
    return repo["node"]["description"]


def repo_collaborators(rstate: Rstate, repo: Repo) -> List[RepoCollaborator]:
    def mkobj(rstate: Rstate, edge: RepoCollaboratorEdge) -> RepoCollaborator:
        return {
            "role": edge["permission"],
            "node": user_by_id(rstate, edge["node"]["id"])["node"],
        }

    if "collaborators" in repo["node"] and repo["node"]["collaborators"]:
        collaborators = repo["node"]["collaborators"]["edges"]
        return [mkobj(rstate, x) for x in collaborators if x is not None]
    return []


def repo_branch_protection_rules(repo: Repo) -> List[BranchProtectionRuleNode]:
    return repo["node"]["branchProtectionRules"]["nodes"]


def _repo_branch_protection_rules_noexcept(
    repo: Repo,
) -> Optional[List[BranchProtectionRuleNode]]:
    if "branchProtectionRules" in repo["node"]:
        return repo_branch_protection_rules(repo)
    return None


def repo_branch_protection_rule(
    repo: Repo, pattern: str
) -> Optional[BranchProtectionRuleNode]:
    rules = repo_branch_protection_rules(repo)
    elems = [x for x in rules if branch_protection_pattern(x) == pattern]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


# team info


def team_name(team: Team) -> str:
    return team["node"]["name"]


def team_description(team: Team) -> str:
    return team["node"]["description"]


def team_repos(rstate: Rstate, team: Team) -> List[RepoWithPerms]:
    def mkobj(rstate: Rstate, edge: TeamRepoEdge) -> RepoWithPerms:
        return {
            "permission": edge["permission"],
            "node": org_repo_by_id(rstate, edge["node"]["id"])["node"],
        }

    if "repositories" in team["node"] and team["node"]["repositories"]:
        repositories = team["node"]["repositories"]["edges"]
        return [mkobj(rstate, x) for x in repositories if x is not None]
    return []


def team_members(rstate: Rstate, team: Team) -> List[UserWithRole]:
    def mkobj(rstate: Rstate, edge: TeamMemberEdge) -> UserWithRole:
        return {
            "role": edge["role"],
            "node": user_by_id(rstate, edge["node"]["id"])["node"],
        }

    if "members" in team["node"] and team["node"]["members"]:
        members = team["node"]["members"]["edges"]
        return [mkobj(rstate, x) for x in members if x is not None]
    return []


def team_parent(rstate: Rstate, team: Team) -> Optional[Team]:
    parent_team = team["node"]["parentTeam"]
    if parent_team:
        return org_team_by_id(rstate, parent_team)
    return None


def team_children(rstate: Rstate, team: Team) -> List[Team]:
    def mkobj(rstate: Rstate, edge: ChildTeam) -> Team:
        return {"node": org_team_by_id(rstate, edge["node"]["id"])["node"]}

    if "childTeams" in team["node"] and team["node"]["childTeams"]:
        children = team["node"]["childTeams"]["edges"]
        return [mkobj(rstate, x) for x in children if x is not None]
    return []


# user info


def user_name(user: User) -> Optional[str]:
    return user["node"]["name"]


def user_login(user: User) -> str:
    return user["node"]["login"]


def user_email(user: User) -> str:
    return user["node"]["email"]


def user_company(user: User) -> str:
    return user["node"]["company"]


def user_is_owner(user: UserWithOrgRole) -> bool:
    return "role" in user and user["role"] == "ADMIN"


# branch protection rules


def branch_protection_id(rule: BranchProtectionRuleNode) -> Hashable:
    return rule["id"]


def branch_protection_pattern(rule: BranchProtectionRuleNode) -> str:
    return rule["pattern"]


def branch_protection_admin_enforced(rule: BranchProtectionRuleNode) -> bool:
    return rule["isAdminEnforced"]


def branch_protection_approvals(rule: BranchProtectionRuleNode) -> int:
    if rule["requiresApprovingReviews"]:
        return rule["requiredApprovingReviewCount"]
    return 0


def branch_protection_owner_approval(rule: BranchProtectionRuleNode) -> bool:
    return rule["requiresCodeOwnerReviews"]


def branch_protection_commit_signatures(
    rule: BranchProtectionRuleNode,
) -> bool:
    return rule["requiresCommitSignatures"]


def branch_protection_linear_history(rule: BranchProtectionRuleNode) -> bool:
    return rule["requiresLinearHistory"]


def branch_protection_restrict_pushes(rule: BranchProtectionRuleNode) -> bool:
    return rule["restrictsPushes"]


def branch_protection_restrict_deletion(
    rule: BranchProtectionRuleNode,
) -> bool:
    return not rule["allowsDeletions"]


def branch_protection_creator(rule: BranchProtectionRuleNode) -> str:
    return rule["creator"]["login"]


def branch_protection_push_allowances(
    rule: BranchProtectionRuleNode,
) -> List[PushAllowance]:
    return rule["pushAllowances"]


def push_allowance_actor(allowance: PushAllowance) -> Actor:
    return allowance["actor"]


###


def actor_type(actor: Actor) -> ActorType:
    return actor["__typename"]


def actor_get_user(rstate: Rstate, actor: Actor) -> User:
    return user_by_id(rstate, actor["id"])


def actor_get_team(rstate: Rstate, actor: Actor) -> Team:
    return org_team_by_id(rstate, actor["id"])


def actor_get_app(rstate, actor):
    raise NotImplementedError()


###


def all_bp_rules(rstate: Rstate) -> Set[BranchProtectionRuleID]:
    result = set()
    for repo in org_repositories(rstate):
        bprules = _repo_branch_protection_rules_noexcept(repo)
        if bprules:
            for bprule in bprules:
                result.add(branch_protection_id(bprule))
    return result


###


def _user_create(rstate: Rstate, user: Mapping) -> Rstate:
    assert "node" in user
    assert "login" in user["node"] and user["node"]["login"]
    assert "id" in user["node"] and user["node"]["id"]
    assert "email" in user["node"]
    assert isinstance(user["node"]["id"], Hashable)
    user_id = user["node"].pop("id")
    rstate["data"]["users"][user_id] = cast(UserWithOrgRole, user)
    return rstate


def _org_member_create(rstate: Rstate, member: Mapping) -> Rstate:
    user_id = member["node"]["id"]
    rstate = _user_create(rstate, member)
    rstate["data"]["organization"]["membersWithRole"].append(user_id)
    return rstate


def empty() -> Rstate:
    return {
        "data": {
            "users": {},
            "organization": {
                "repositories": {"edges": []},
                "membersWithRole": [],
                "teams": {"edges": []},
            },
        }
    }


def merge_team(old_value: Team, new_value: Mapping) -> Team:
    result = old_value
    logging.debug("merging teams old: %s, new: %s", old_value, new_value)
    if "repositories" in old_value["node"]:
        repositories = old_value["node"]["repositories"]
    else:
        repositories = {"edges": []}
    if "members" in old_value["node"]:
        members = old_value["node"]["members"]
    else:
        members = {"edges": []}
    if "childTeams" in old_value["node"]:
        children = old_value["node"]["childTeams"]
    else:
        children = {"edges": []}
    if (
        "repositories" in new_value["node"]
        and new_value["node"]["repositories"]
    ):
        for item in new_value["node"]["repositories"]["edges"]:
            if item:
                repositories["edges"].append(item)
    if "members" in new_value["node"] and new_value["node"]["members"]:
        for item in new_value["node"]["members"]["edges"]:
            if item:
                members["edges"].append(item)
    if "childTeams" in new_value["node"] and new_value["node"]["childTeams"]:
        for item in new_value["node"]["childTeams"]["edges"]:
            if item:
                children["edges"].append(item)
    result["node"]["repositories"] = repositories
    result["node"]["members"] = members
    result["node"]["childTeams"] = children
    logging.debug("merged team result: %s", result)
    return result


def merge_repo(old_value: Repo, new_value: Repo) -> Repo:
    result = old_value
    logging.debug("merging repo old: %s, new: %s", old_value, new_value)
    if "collaborators" in old_value["node"]:
        collaborators = old_value["node"]["collaborators"]
    else:
        collaborators = {"edges": []}
    if (
        "collaborators" in new_value["node"]
        and new_value["node"]["collaborators"]
    ):
        for item1 in new_value["node"]["collaborators"]["edges"]:
            if item1:
                collaborators["edges"].append(item1)

    if "branchProtectionRules" in old_value["node"]:
        branch_protection_rules = old_value["node"]["branchProtectionRules"]
    else:
        branch_protection_rules = {"nodes": []}
    if (
        "branchProtectionRules" in new_value["node"]
        and new_value["node"]["branchProtectionRules"]
    ):
        for item2 in new_value["node"]["branchProtectionRules"]["nodes"]:
            if item2:
                item2["pushAllowances"] = []
                branch_protection_rules["nodes"].append(item2)

    result["node"]["collaborators"] = collaborators
    result["node"]["branchProtectionRules"] = branch_protection_rules
    logging.debug("merged repo result: %s", result)
    return result


def merge_repo_branch_protection(
    repo: Repo, push_allowance: PushAllowance
) -> Repo:
    assert "branchProtectionRules" in repo["node"]
    bprule_id = push_allowance["branchProtectionRule"]["id"]
    # del push_allowance['branchProtectionRule']
    bprule = [
        x for x in repo_branch_protection_rules(repo) if x["id"] == bprule_id
    ][0]
    rules_filtered = [
        x for x in repo_branch_protection_rules(repo) if x["id"] != bprule_id
    ]
    bprule["pushAllowances"].append(push_allowance)
    rules_filtered.append(bprule)
    repo["node"]["branchProtectionRules"]["nodes"] = rules_filtered
    return repo


def merge_members(old_value, new_value):
    raise NotImplementedError("not implemented")


def merge(rstate, alias, new_data):
    funcs = {
        "teams": {
            "get_by_id": org_team_by_id,
            "merge": merge_team,
            "create": lambda rstate, x: org_teams(rstate).append(x),
        },
        "repositories": {
            "get_by_id": org_repo_by_id,
            "merge": merge_repo,
            "create": lambda rstate, x: org_repositories(rstate).append(x),
        },
        "membersWithRole": {
            "get_by_id": _user_by_id_noexcept,
            "merge": merge_members,
            "create": _org_member_create,
        },
    }
    if alias.startswith("user"):
        return _user_create(rstate, {"node": new_data["data"]["organization"]})
    for key in ["repositories", "teams", "membersWithRole"]:
        if key in new_data["data"]["organization"]:
            for item in new_data["data"]["organization"][key]["edges"]:
                existing_item = funcs[key]["get_by_id"](
                    rstate, item["node"]["id"]
                )
                if existing_item:
                    edges = rstate["data"]["organization"][key]["edges"]
                    new_list = [
                        x
                        for x in edges
                        if x["node"]["id"] != item["node"]["id"]
                    ]
                    new_list.append(funcs[key]["merge"](existing_item, item))
                    rstate["data"]["organization"][key]["edges"] = new_list
                else:
                    funcs[key]["create"](rstate, item)
        if "pushAllowances" in new_data["data"]["organization"]:
            for item in new_data["data"]["organization"]["pushAllowances"][
                "nodes"
            ]:
                repo = org_repo_by_id(
                    rstate, item["branchProtectionRule"]["repository"]["id"]
                )
                edges = rstate["data"]["organization"]["repositories"]["edges"]
                new_list = [
                    x for x in edges if x["node"]["id"] != repo["node"]["id"]
                ]
                new_list.append(merge_repo_branch_protection(repo, item))
                rstate["data"]["organization"]["repositories"][
                    "edges"
                ] = new_list
    if "repository" in new_data["data"]["organization"]:
        repo = new_data["data"]["organization"]["repository"]
        edges = rstate["data"]["organization"]["repositories"]["edges"]
        new_list = [x for x in edges if x["node"]["id"] != repo["id"]]
        new_list.append(
            merge_repo(org_repo_by_id(rstate, repo["id"]), {"node": repo})
        )
        rstate["data"]["organization"]["repositories"]["edges"] = new_list
    if "team" in new_data["data"]["organization"]:
        team = new_data["data"]["organization"]["team"]
        merge_team(org_team_by_id(rstate, team["id"]), {"node": team})
    return rstate


def missing_collaborators(rstate: Rstate, repo: Repo) -> List[str]:
    missing = []
    if "collaborators" in repo["node"] and repo["node"]["collaborators"]:
        edges = repo["node"]["collaborators"]["edges"]
        for edge in [x for x in edges if x is not None]:
            user_id = edge["node"]["id"]
            if not _user_by_id_noexcept(rstate, user_id):
                missing.append(edge["node"]["login"])
    return missing


def validate(rstate: Rstate) -> bool:
    # * all repositories referenced by teams should be known
    # * all users referenced by teams should be known
    # * all users referenced by repositories should be known
    # for team in org_teams(rstate):
    for repo in org_repositories(rstate):
        for missing in missing_collaborators(rstate, repo):
            msg = 'unknown user "{}" referenced as a collaborator of "{}"'
            raise RuntimeError(
                msg.format(
                    missing,
                    repo_name(repo),
                )
            )
    return True
