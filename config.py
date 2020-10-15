from os import environ
from pathlib import Path


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


def team_members(team):
    if team['members']:
        return team['members']
    return []


def team_children(team):
    if 'children' in team:
        return team['children']
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
    elems = [x for x in get_teams(config) if email in team_members(x)]
    return elems


def default_dir():
    def parent_dir():
        if environ.get('XDG_CONFIG_HOME'):
            return Path(environ.get('XDG_CONFIG_HOME'))
        if environ.get('HOME'):
            return Path(environ.get('HOME')) / '.config'
        return Path('/')
    return parent_dir() / 'ghaudit'
