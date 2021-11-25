from os import environ
from pathlib import Path
from functools import reduce, wraps
import logging

from typing import Any
from typing import Collection
from typing import Optional
from typing import Iterable
from typing import List
from typing import Mapping
from typing import Set
from typing_extensions import TypedDict

Team = TypedDict("Team", {"name": str, "members": List[str], "children": List[str]})
Organisation = TypedDict(
    "Organisation", {"name": str, "owners": List[str], "teams": List[Team]}
)
Config = TypedDict("Config", {"organisation": Organisation, "cache": Mapping[str, Any]})
RawConfig = TypedDict(
    "Config", {"organisation": Organisation, "cache": Mapping[str, Any]}
)


def get_teams(config: Config) -> Collection[Team]:
    return config["organisation"]["teams"]


def load(data: RawConfig) -> Config:
    data["cache"] = {
        "team_by_name": {},
        "team_parents": {},
        "user_teams": {},
        "team_ancestors": {},
        "effective_members": {},
    }
    return data


def cache(name: str, keys: Iterable):
    def hash_key(key, *args):
        return key[1](args[key[0]])

    def inner(func):
        @wraps(func)
        def wrapper(config: Config, *args):
            entry = hash(tuple(hash_key(x, *args) for x in keys))
            if entry in config["cache"][name] and config["cache"][name][entry]:
                logging.debug(
                    "config cache hit %s %s %s: %s",
                    func.__name__,
                    name,
                    entry,
                    config["cache"][name][entry],
                )
                return config["cache"][name][entry]
            result = func(config, *args)
            logging.debug(
                "config cache miss %s %s %s: %s", func.__name__, name, entry, result
            )
            config["cache"][name][entry] = result
            return result

        return wrapper

    return inner


@cache("team_by_name", [(0, lambda x: x)])
def get_team(config: Config, name: str) -> Optional[Team]:
    elems = [x for x in get_teams(config) if x["name"] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def _get_team_exists(config: Config, name: str) -> Team:
    team = get_team(config, name)
    if not team:
        raise RuntimeError("team {} not found".format(name))
    return team


def team_name(team: Team) -> str:
    return team["name"]


# direct members of a team, not taking members of descendants teams into
# account
def team_direct_members(team: Team) -> Collection[str]:
    if team["members"]:
        return team["members"]
    return []


# effective members of a team (direct members + members of descendants teams)
# @cache("effective_members", [(0, team_name)])
def team_effective_members(config: Config, team: Team) -> Set[str]:
    return reduce(
        lambda acc, child: acc | set(team_direct_members(child)),
        [_get_team_exists(config, x) for x in team_descendants(config, team)],
        set(team_direct_members(team)),
    )


def team_children(team: Team) -> Collection[str]:
    if "children" in team:
        return team["children"]
    return []


def team_descendants(config: Config, team: Team) -> Set[str]:
    def reduce_function(acc: Set[str], child_name: str) -> Set[str]:
        child_team = _get_team_exists(config, child_name)
        return acc | team_descendants(config, child_team) | {child_name}

    if "children" in team:
        return reduce(reduce_function, set(team_children(team)), set())
    return set()


@cache("team_parents", [(0, team_name)])
def team_parents(config: Config, team: Team) -> Collection[Team]:
    def is_parent(entry: Team, team: Team) -> bool:
        return team_name(team) in team_children(entry)

    return [x for x in get_teams(config) if is_parent(x, team)]


def team_parent(config: Config, team: Team) -> Optional[Team]:
    elems = team_parents(config, team)
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


@cache("team_ancestors", [(0, team_name)])
def team_ancestors(config: Config, team: Team) -> Set[str]:
    ancestors = set()
    parents = team_parents(config, team)
    for team in parents:
        ancestors.update(team_ancestors(config, team))
    ancestors.update(map(team_name, parents))
    return ancestors


@cache("user_teams", [(0, lambda x: x)])
def user_teams(config: Config, email: str) -> Collection[Team]:
    elems = [x for x in get_teams(config) if email in team_direct_members(x)]
    return elems


def is_owner(config: Config, email: str) -> bool:
    return email in config["organisation"]["owners"]


def default_dir() -> Path:
    def parent_dir() -> Path:
        xdg_home = environ.get("XDG_CONFIG_HOME")
        if xdg_home:
            return Path(xdg_home)
        home = environ.get("HOME")
        if home:
            return Path(home) / ".config"
        return Path("/")

    return parent_dir() / "ghaudit"
