from os import environ
from pathlib import Path
from functools import reduce

from typing import Collection
from typing import Optional
from typing import List
from typing import Set
from typing_extensions import TypedDict

Team = TypedDict('Team', {'name': str, 'members': List[str], 'children': List[str]})
Organisation = TypedDict('Organisation', {'name': str, 'owners': List[str], 'teams': List[Team]})
Config = TypedDict('Config', {'organisation': Organisation})


def get_teams(config: Config) -> Collection[Team]:
    return config['organisation']['teams']


def get_team(config: Config, name: str) -> Optional[Team]:
    elems = [x for x in get_teams(config) if x['name'] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def team_name(team: Team) -> str:
    return team['name']


# direct members of a team, not taking members of descendants teams into
# account
def team_direct_members(team: Team) -> Collection[str]:
    if team['members']:
        return team['members']
    return []


# effective members of a team (direct members + members of descendants teams)
def team_effective_members(config: Config, team: Team) -> Set[str]:
    return reduce(
        lambda acc, child: acc | set(team_direct_members(child)),
        [get_team(config, x) for x in team_descendants(config, team)],
        set(team_direct_members(team))
    )


def team_children(team: Team) -> Collection[str]:
    if 'children' in team:
        return team['children']
    return []


def team_descendants(config: Config, team: Team) -> Set[str]:
    def reduce_function(acc, child_name):
        child_team = get_team(config, child_name)
        return acc | set(team_descendants(config, child_team)) | {child_name}
    if 'children' in team:
        return reduce(reduce_function, set(team_children(team)), set())
    return set()


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


def team_ancestors(config: Config, team: Team) -> Set[str]:
    ancestors = set()
    parents = team_parents(config, team)
    for team in parents:
        ancestors.update(team_ancestors(config, team))
    ancestors.update(map(team_name, parents))
    return ancestors


def user_teams(config: Config, email: str) -> Collection[Team]:
    elems = [x for x in get_teams(config) if email in team_direct_members(x)]
    return elems


def is_owner(config: Config, email: str) -> bool:
    return email in config['organisation']['owners']


def default_dir() -> Path:
    def parent_dir() -> Path:
        xdg_home = environ.get('XDG_CONFIG_HOME')
        if xdg_home:
            return Path(xdg_home)
        home = environ.get('HOME')
        if home:
            return Path(home) / '.config'
        return Path('/')
    return parent_dir() / 'ghaudit'
