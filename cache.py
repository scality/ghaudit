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


GITHUB_GRAPHQL_ENDPOINT = 'https://api.github.com/graphql'


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


def _sync(config, auth_driver):
    data = schema.empty()

    workaround = {'teamRepo': [], 'teamMember': [], 'collaborators': []}
    workaround2 = {'team': 0, 'repo': 0}
    iterations = 0
    query = CompoundQuery(MAX_PARALLEL_QUERIES)
    query.add_frag(FRAG_PAGEINFO_FIELDS)
    query.append(OrgTeamsQuery())
    query.append(OrgMembersQuery())
    query.append(OrgRepoQuery())
    while not query.finished():
        demo_params = {
            'organisation': config['organisation']['name'],
            'teamsMax': 40,
            'membersWithRoleMax': 40,
            'repositoriesMax': 40,
        }
        iterations += 1
        result = query.run(auth_driver, demo_params)

        for item in result['data'].values():
            data = schema.merge(data, {'data': {'organization': item}})
        print('>>>>>>>>>>>>>>>>>>>>>>>>>>>> {}'.format(iterations))
        print(query.stats())
        print('teams: {}'.format(len(schema.org_teams(data))))
        print('users: {}'.format(len(schema.org_repositories(data))))
        print('repositories: {}'.format(len(schema.org_members(data))))
        print('{} <<<<<<<<<<<<<<<<<<<<<<<<<<<<'.format(iterations))

        for count, team in enumerate(schema.org_teams(data)):
            name = schema.team_name(team)
            if name not in workaround['teamRepo']:
                query.append(TeamRepoQuery(name, workaround2['team'], 40))
                workaround['teamRepo'].append(name)
                workaround2['team'] += 1

            if name not in workaround['teamMember']:
                query.append(TeamMemberQuery(name, workaround2['team'], 40))
                workaround['teamMember'].append(name)
                workaround2['team'] += 1

        for count, repo in enumerate(schema.org_repositories(data)):
            name = schema.repo_name(repo)
            if name not in workaround['collaborators']:
                query.append(RepoCollaboratorQuery(name, workaround2['repo'], 40))
                workaround['collaborators'].append(name)
                workaround2['repo'] += 1
        # TODO resolve all users referenced by collaborators
        # TODO cache validation:
        # * all repos referenced by teams should be known
        # * all users referenced by teams should be known
        # * all users referenced by repos should be known
    return data
