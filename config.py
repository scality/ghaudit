from os import environ
from pathlib import Path
from functools import reduce


def get_team_in_config(config, name):
    teams = config['organisation']['teams']
    elems = [x for x in teams if x['name'] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def get_teams(config):
    return config['organisation']['teams']


def get_team(config, name):
    elems = [x for x in get_teams(config) if x['name'] == name]
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def team_name(team):
    return team['name']


# direct members of a team, not taking members of descendants teams into
# account
def team_direct_members(team):
    if team['members']:
        return team['members']
    return []


# effective members of a team (direct members + members of descendants teams)
def team_effective_members(config, team):
    return reduce(
        lambda acc, child_name: acc | set(team_direct_members(child_name)),
        [get_team_in_config(config, x) for x in team_descendants(config, team)],
        set(team_direct_members(team))
    )


def team_children(team):
    if 'children' in team:
        return team['children']
    return []


def team_descendants(config, team):
    def reduce_function(acc, child_name):
        child_team = get_team_in_config(config, child_name)
        return acc | set(team_descendants(config, child_team)) | {child_name}
    if 'children' in team:
        return reduce(reduce_function, set(team_children(team)), set())
    return []


def team_parents(config, team):
    def is_parent(entry, team):
        return team_name(team) in team_children(entry)

    return [x for x in get_teams(config) if is_parent(x, team)]


def team_parent(config, team):
    elems = team_parents(config, team)
    assert len(elems) <= 1
    if elems:
        return elems[0]
    return None


def team_ancestors(config, team):
    ancestors = set()
    parents = team_parents(config, team)
    for team in parents:
        ancestors.update(team_ancestors(config, team))
    ancestors.update(map(team_name, parents))
    return ancestors


def user_teams(config, email):
    elems = [x for x in get_teams(config) if email in team_direct_members(x)]
    return elems


def default_dir():
    def parent_dir():
        if environ.get('XDG_CONFIG_HOME'):
            return Path(environ.get('XDG_CONFIG_HOME'))
        if environ.get('HOME'):
            return Path(environ.get('HOME')) / '.config'
        return Path('/')
    return parent_dir() / 'ghaudit'
