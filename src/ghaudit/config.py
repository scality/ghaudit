"""Configuration describing the github organisation to audit.

The configuration contains team hierarchy, team members, and organisation
owners.
"""

from __future__ import annotations

from functools import reduce
from os import environ
from pathlib import Path
from typing import (
    Any,
    Collection,
    Dict,
    Iterable,
    List,
    Mapping,
    NamedTuple,
    NoReturn,
    Set,
    TypedDict,
)

import ghaudit.user_map
from ghaudit.user_map import UserMap
from ghaudit.utils import find_duplicates


class Description(NamedTuple):
    sequence_short: str
    sequence: str
    element: str
    element_short: str


class Team(TypedDict):
    name: str
    members: List[str]
    children: List[str]
    parents: Set[str]
    ancestors: Set[str]
    descendants: Set[str]


class Config(NamedTuple):
    organisation: str
    owners: frozenset[str]
    teams: Mapping[str, Team]
    by_member: Mapping[str, Set[str]]
    effective_members: Mapping[str, set[str]]


class RawTeamBase1(TypedDict):
    name: str


RawTeamBase2 = TypedDict(
    "RawTeamBase2", {"members": List[str], "children": List[str]}, total=False
)


class RawTeam(RawTeamBase1, RawTeamBase2):
    pass


def _has_members(team) -> bool:
    return "members" in team and team["members"]


def _has_children(team) -> bool:
    return "children" in team and team["children"]


def _check_users(
    users: Any, usermap: UserMap, description: Description
) -> List[str]:
    if not isinstance(users, Iterable):
        message = "{} should be iterable (e.g. a list)."
        return [message.format(description.sequence.capitalize())]

    # wrong_type = filter(partial(isinstance, classinfo=str), users)
    wrong_type = list(filter(lambda x: not isinstance(x, str), users))
    if wrong_type:
        message = 'Invalid type for {}. {} should be specified as string. "{{}}" found instead for {{}}'.format(  # noqa: E501 pylint: disable=line-too-long
            description.element, description.sequence_short
        )
        return [message.format(type(x), repr(x)) for x in wrong_type]

    duplicates = find_duplicates(users)
    if duplicates:
        message = 'Duplicate {} found in {}: "{{}}"'.format(
            description.element_short, description.sequence
        )
        return [message.format(x) for x in duplicates]

    not_found = list(
        filter(
            lambda x: x if not ghaudit.user_map.login(usermap, x) else None,
            users,
        )
    )

    if not_found:
        message = "{} not found in the user map: {{}}".format(
            description.element
        )
        return [message.format(str(x)) for x in not_found]
    return []


def _check_owners(owners: Any, usermap: UserMap) -> List[str]:
    return _check_users(
        owners,
        usermap,
        Description(
            sequence_short="owners",
            sequence="organisation owners",
            element="owner",
            element_short="owner",
        ),
    )


def _check_team_children(team, known_names) -> List[str]:
    children = team["children"]
    name = team["name"]

    duplicates = find_duplicates(children)
    if duplicates:
        return ['duplicate children definition for team "{}"'.format(name)]

    not_found = list(filter(lambda x: x not in known_names, children))
    if not_found:
        message = (
            'reference to child team "{{}}" in team "{}" not found'.format(
                name
            )
        )
        return [message.format(x) for x in children]

    return []


def _check_teams(teams: Any, usermap: UserMap) -> List[str]:

    if not isinstance(teams, Iterable):
        return ["Teams of the organisation should be iterable (e.g. a list)."]
    no_name = any(map(lambda x: "name" not in x, teams))
    if no_name:
        return ["All teams must have a name"]
    duplicates = find_duplicates(teams, lambda x: x["name"])
    if duplicates:
        return [
            "Team names must be unique. The following duplicates were found: {}".format(  # noqa: E501 pylint: disable=line-too-long
                duplicates
            )
        ]

    errors = []
    for team in filter(_has_members, teams):
        errors += _check_users(
            team["members"],
            usermap,
            Description(
                sequence_short="members",
                sequence='members of the team "{}"'.format(team["name"]),
                element='member of the team "{}"'.format(team["name"]),
                element_short="member",
            ),
        )

    known_names = {x["name"] for x in teams}
    for team in filter(_has_children, teams):
        errors += _check_team_children(team, known_names)

    return errors


def _check_config(raw: Mapping[str, Any], usermap: UserMap) -> None:
    error_separator = "\n * "

    def fail(msg: str) -> NoReturn:
        raise RuntimeError(
            "fatal error while loading the configuration: {}{}".format(
                error_separator, msg
            )
        )

    if "organisation" not in raw:
        fail("no organisation could be found in the configuration.")
    organisation = raw["organisation"]
    errors = []
    if "name" not in organisation:
        errors.append("No name specified for the organisation.")
    if not organisation["name"]:
        errors += "Empty organisation name."
    if "owners" not in organisation or not organisation["owners"]:
        errors.append("No owner specified for the organisation.")
    errors += _check_owners(organisation["owners"], usermap)
    if "teams" in organisation and organisation["teams"]:
        errors += _check_teams(organisation["teams"], usermap)

    if errors:
        fail(error_separator.join(errors))


def load(raw_config: Mapping[str, Any], usermap: UserMap):
    """Load the configuration from a Mapping.

    This is meant to be used to load configuration from a file.
    """

    def compute_parents(teams: Iterable[RawTeam]) -> Dict[str, Set[str]]:
        parents = {
            x["name"]: set() for x in teams
        }  # type: Dict[str, Set[str]]
        for team in filter(_has_children, teams):
            for child in team["children"]:
                parents[child].add(team["name"])
        return parents

    def compute_ancestors(
        teams: Iterable[RawTeam], parent_map: Dict[str, Set[str]]
    ) -> Dict[str, Set[str]]:
        def ancestors(
            team_name: str, parent_map: Dict[str, Set[str]]
        ) -> Set[str]:
            parents = parent_map[team_name]
            return reduce(
                lambda a, x: a | ancestors(x, parent_map), parents, parents
            )

        # todo: check circular ancestors
        return {x["name"]: ancestors(x["name"], parent_map) for x in teams}

    def compute_descendants(teams: Iterable[RawTeam]) -> Dict[str, Set[str]]:
        def descendants(
            index: Mapping[str, RawTeam], team: RawTeam
        ) -> Set[str]:
            # if team has children
            #   for each child
            #     return children + list of descendants for each children
            def add(acc: Set[str], child_name: str) -> Set[str]:
                child_team = index[child_name]
                return acc | {child_name} | descendants(index, child_team)

            if not _has_children(team):
                return set()
            return reduce(add, set(team["children"]), set())

        index = {x["name"]: x for x in teams}
        return {x["name"]: descendants(index, x) for x in teams}

    def index_members(teams: Iterable[RawTeam]) -> Dict[str, Set[str]]:
        index = {}  # type: Dict[str, Set[str]]
        for team in filter(_has_members, teams):
            for member in team["members"]:
                index[member] = index.get(member, set()) | {team["name"]}
        return index

    def compute_effective_members(
        teams: Iterable[RawTeam], descendants_map: Dict[str, Set[str]]
    ) -> Dict[str, Set[str]]:
        def find_team(name: str) -> RawTeam:
            return next(iter(filter(lambda x: x["name"] == name, teams)))

        def effective_members(team: RawTeam) -> Set[str]:
            descendants = (find_team(x) for x in descendants_map[team["name"]])
            return reduce(
                lambda acc, child: acc | set(child.get("members", []) or []),
                descendants,
                set(team.get("members", []) or []),
            )

        return {x["name"]: effective_members(x) for x in teams}

    _check_config(raw_config, usermap)

    teams = raw_config["organisation"]["teams"]
    parent_map = compute_parents(teams)
    ancestors_map = compute_ancestors(teams, parent_map)
    descendants_map = compute_descendants(teams)
    return Config(
        organisation=raw_config["organisation"]["name"],
        owners=frozenset(raw_config["organisation"]["owners"]),
        teams={
            x["name"]: {
                **x,  # type: ignore
                "parents": parent_map[x["name"]],
                "ancestors": ancestors_map[x["name"]],
                "descendants": descendants_map[x["name"]],
            }
            for x in teams
        },
        by_member=index_members(teams),
        effective_members=compute_effective_members(teams, descendants_map),
    )


def get_org_name(config: Config) -> str:
    """Return the name of the organisation to audit."""
    return config.organisation


def get_teams(config: Config) -> Collection[Team]:
    """Return all teams from the configuration."""
    return config.teams.values()


def get_team(config: Config, name: str) -> Team | None:
    """Return a team specified by name if it exists."""
    return config.teams.get(name)


def _get_team_exists(config: Config, name: str) -> Team:
    return config.teams[name]


def team_name(team: Team) -> str:
    """Return the name of a team."""
    return team["name"]


def team_direct_members(team: Team) -> List[str]:
    """Return the list of explicit members of a team."""
    return team["members"] if _has_members(team) else []


def team_effective_members(config: Config, team: Team) -> Set[str]:
    """Return the list of members with effective access to a team.

    Team inheritance is taken into account to compute effective access to a
    user.
    """
    return config.effective_members[team_name(team)]


def team_children(team: Team) -> List[str]:
    """Return all the direct children of a team."""
    if "children" in team:
        return team["children"]
    return []


def team_descendants(config: Config, team: Team) -> Set[str]:
    """Return all the descendants of a team."""
    del config
    return team["descendants"]


def team_parents(config: Config, team: Team) -> Iterable[Team]:
    """Return all the direct parent of a team."""
    return (_get_team_exists(config, x) for x in team["parents"])


def team_ancestors(config: Config, team: Team) -> Set[str]:
    """Return all the ancestors to a team."""
    del config
    return team["ancestors"]


def user_teams(config: Config, email: str) -> Iterable[Team]:
    """Return the teams a user member is expected to be a member of.

    Only the teams in which the user is a direct member are return. The
    ancestors of these teams are not returned.
    """
    names = config.by_member.get(email)
    if not names:
        return []
    return (_get_team_exists(config, x) for x in names)


def is_owner(config: Config, email: str) -> bool:
    """Return whether a given user should be an organisation owner."""
    return email in config.owners


def default_dir() -> Path:
    """Return the default configuration directory path."""

    def parent_dir() -> Path:
        xdg_home = environ.get("XDG_CONFIG_HOME")
        if xdg_home:
            return Path(xdg_home)
        home = environ.get("HOME")
        if home:
            return Path(home) / ".config"
        return Path("/")

    return parent_dir() / "ghaudit"
