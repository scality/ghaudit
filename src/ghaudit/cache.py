"""Github remote state synchronisation with a local storage (hence cache)."""

from __future__ import annotations

import json
import tempfile
from os import environ, fsync, makedirs, path, rename
from pathlib import Path
from typing import Dict, List

from ghaudit import auth, schema
from ghaudit.config import Config
from ghaudit.query.branch_protection_push_allowances import (
    BranchProtectionPushAllowances,
)
from ghaudit.query.compound_query import CompoundQuery
from ghaudit.query.org_members import OrgMembersQuery
from ghaudit.query.org_repositories import OrgRepoQuery
from ghaudit.query.org_teams import OrgTeamsQuery
from ghaudit.query.repo_branch_protection import RepoBranchProtectionQuery
from ghaudit.query.repo_collaborators import RepoCollaboratorQuery
from ghaudit.query.team_children import TeamChildrenQuery
from ghaudit.query.team_permission import TeamRepoQuery
from ghaudit.query.user import UserQuery
from ghaudit.query.user_role import TeamMemberQuery
from ghaudit.ui import ProgressCB


def file_path() -> Path:
    def parent_dir() -> Path:
        xdg_data_home = environ.get("XDG_DATA_HOME")
        if xdg_data_home:
            return Path(xdg_data_home)
        home = environ.get("HOME")
        if home:
            return Path(home) / ".local" / "share"
        return Path("/")

    return parent_dir() / "ghaudit" / "compliance" / "cache.json"


def load() -> schema.Rstate:
    """Load remote state from cache file."""
    with open(file_path(), encoding="UTF-8") as cache_file:
        rstate = json.load(cache_file)
        schema.validate(rstate)
        return rstate


def store(data: schema.Rstate) -> None:
    """Store remote state to file."""
    ofilepath = file_path()
    if not path.exists(ofilepath.parent):
        makedirs(ofilepath.parent)
    temp_path = None
    with tempfile.NamedTemporaryFile(
        mode="w+t", dir=ofilepath.parent, delete=False
    ) as output:
        json.dump(data, output)
        temp_path = output.name
    rename(temp_path, ofilepath)
    with open(ofilepath, encoding="UTF-8") as cache_file:
        fsync(cache_file.fileno())


def refresh(
    config: Config, auth_driver: auth.AuthDriver, progress: ProgressCB
) -> None:
    """Refresh the remote state from github to a local file."""
    data = _sync(config, auth_driver, progress)
    print("validating cache")
    if schema.validate(data):
        print("persisting cache")
        store(data)


FRAG_PAGEINFO_FIELDS = """
fragment pageInfoFields on PageInfo {
  endCursor
  hasNextPage
}
"""

MAX_PARALLEL_QUERIES = 40
ORG_TEAMS_MAX = 90
ORG_MEMBERS_MAX = 90
ORG_REPOSITORIES_MAX = 90


def _sync_progress(data, query, found, progress: ProgressCB):
    stats = query.stats()
    progress(
        [
            ("total HTTP roundtrips", stats["iterations"]),
            ("graphQL queries", stats["done"], stats["queries"]),
            ("teams", len(schema.org_teams(data)), len(found["teams"])),
            (
                "repositories",
                len(schema.org_repositories(data)),
                len(found["repositories"]),
            ),
            ("org members", len(schema.org_members(data))),
            ("users", len(schema.users(data))),
            (
                "branch protection rules",
                len(schema.all_bp_rules(data)),
                len(found["bprules"]),
            ),
        ]
    )


def _sync(config: Config, auth_driver, progress: ProgressCB):
    data = schema.empty()
    found = {
        "teams": [],
        "repositories": [],
        "collaborators": [],
        "bprules": [],
    }  # type: Dict[str, List[str]]
    workaround2 = {"team": 0, "repo": 0, "user": 0, "bprules": 0}
    query = CompoundQuery(MAX_PARALLEL_QUERIES)
    demo_params = {
        "organisation": config["organisation"]["name"],
        "teamsMax": ORG_TEAMS_MAX,
        "membersWithRoleMax": ORG_MEMBERS_MAX,
        "repositoriesMax": ORG_REPOSITORIES_MAX,
    }  # type: Dict[str, str | int]

    query.add_frag(FRAG_PAGEINFO_FIELDS)
    query.append(OrgTeamsQuery())
    query.append(OrgMembersQuery())
    query.append(OrgRepoQuery())
    while not query.finished():
        result = query.run(auth_driver, demo_params)

        for key, value in result["data"].items():
            data = schema.merge(data, key, {"data": {"organization": value}})

        new_teams = [
            x
            for x in schema.org_teams(data)
            if schema.team_name(x) not in found["teams"]
        ]
        new_repos = [
            x
            for x in schema.org_repositories(data)
            if schema.repo_name(x) not in found["repositories"]
        ]
        new_collaborators = [
            y
            for x in schema.org_repositories(data)
            for y in schema.missing_collaborators(data, x)
            if y not in found["collaborators"]
        ]
        new_bp_rules = [
            x for x in schema.all_bp_rules(data) if x not in found["bprules"]
        ]

        for team in new_teams:
            name = schema.team_name(team)
            query.append(TeamRepoQuery(name, workaround2["team"], 40))
            workaround2["team"] += 1
            query.append(
                TeamMemberQuery(team["node"]["slug"], workaround2["team"], 40)
            )
            workaround2["team"] += 1
            found["teams"].append(name)
            query.append(TeamChildrenQuery(name, workaround2["team"], 40))
            workaround2["team"] += 1
            found["teams"].append(name)

        for repo in new_repos:
            name = schema.repo_name(repo)
            query.append(RepoCollaboratorQuery(name, workaround2["repo"], 40))
            workaround2["repo"] += 1
            query.append(
                RepoBranchProtectionQuery(name, workaround2["repo"], 40)
            )
            workaround2["repo"] += 1
            found["repositories"].append(name)

        for login in new_collaborators:
            query.append(UserQuery(login, workaround2["user"]))
            workaround2["user"] += 1
            found["collaborators"].append(login)

        for rule_id in new_bp_rules:
            query.append(
                BranchProtectionPushAllowances(
                    str(rule_id), workaround2["bprules"], 10
                )
            )
            workaround2["bprules"] += 1
            found["bprules"].append(str(rule_id))

        _sync_progress(data, query, found, progress)

    return data
