from os import environ
from os import makedirs
from os import path
import json
from pathlib import Path

from ghaudit import schema
from ghaudit.query.compound_query import CompoundQuery
from ghaudit.query.org_teams import OrgTeamsQuery
from ghaudit.query.org_members import OrgMembersQuery
from ghaudit.query.org_repositories import OrgRepoQuery
from ghaudit.query.team_permission import TeamRepoQuery
from ghaudit.query.user_role import TeamMemberQuery
from ghaudit.query.repo_collaborators import RepoCollaboratorQuery


def _file_path():
    def parent_dir():
        if environ.get('XDG_DATA_HOME'):
            return Path(environ.get('XDG_DATA_HOME'))
        if environ.get('HOME'):
            return Path(environ.get('HOME')) / '.local' / 'share'
        return Path('/')
    return parent_dir() / 'ghaudit' / 'compliance' / 'cache2.json'


def graphql_query_file_path():
    return Path(__file__).parent / 'queries' / 'compliance'


def load():
    with open(_file_path()) as cache_file:
        return json.load(cache_file)


def store(data):
    with open(_file_path(), mode='w') as cache_file:
        return json.dump(data, cache_file)


def refresh(config, auth_driver):
    ofilepath = _file_path()
    if not path.exists(ofilepath.parent):
        makedirs(ofilepath.parent)
    data = _sync(config, auth_driver)
    store(data)


FRAG_PAGEINFO_FIELDS = """
fragment pageInfoFields on PageInfo {
  endCursor
  hasNextPage
}
"""

MAX_PARALLEL_QUERIES = 40


def _sync_progress(data, query):
    print('>>>>>>>>>>>>>>>>>>>>>>>>>>>>')
    print(query.stats())
    print('teams: {}'.format(len(schema.org_teams(data))))
    print('users: {}'.format(len(schema.org_repositories(data))))
    print('repositories: {}'.format(len(schema.org_members(data))))
    print('<<<<<<<<<<<<<<<<<<<<<<<<<<<<')


def _sync(config, auth_driver):
    data = schema.empty()
    found = {'teams': [], 'repositories': []}
    workaround2 = {'team': 0, 'repo': 0}
    query = CompoundQuery(MAX_PARALLEL_QUERIES)
    demo_params = {
        'organisation': config['organisation']['name'],
        'teamsMax': 40,
        'membersWithRoleMax': 40,
        'repositoriesMax': 40,
    }

    query.add_frag(FRAG_PAGEINFO_FIELDS)
    query.append(OrgTeamsQuery())
    query.append(OrgMembersQuery())
    query.append(OrgRepoQuery())
    while not query.finished():
        result = query.run(auth_driver, demo_params)

        for item in result['data'].values():
            data = schema.merge(data, {'data': {'organization': item}})

        new_teams = [x for x in schema.org_teams(data) if schema.team_name(x) not in found['teams']]
        new_repos = [x for x in schema.org_repositories(data) \
                     if schema.repo_name(x) not in found['repositories']]

        for team in new_teams:
            name = schema.team_name(team)
            query.append(TeamRepoQuery(name, workaround2['team'], 40))
            workaround2['team'] += 1
            query.append(TeamMemberQuery(name, workaround2['team'], 40))
            workaround2['team'] += 1
            found['teams'].append(name)

        for repo in new_repos:
            name = schema.repo_name(repo)
            query.append(RepoCollaboratorQuery(name, workaround2['repo'], 40))
            workaround2['repo'] += 1
            found['repositories'].append(name)

        _sync_progress(data, query)

        # TODO resolve all users referenced by collaborators
        # TODO cache validation:
        # * all repos referenced by teams should be known
        # * all users referenced by teams should be known
        # * all users referenced by repos should be known
    return data
