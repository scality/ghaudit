from os import environ
from os import makedirs
from os import path
import json
from pathlib import Path
import functools

import requests
import jinja2
from . import schema


GITHUB_GRAPHQL_ENDPOINT = 'https://api.github.com/graphql'


def file_path():
    def parent_dir():
        if environ.get('XDG_DATA_HOME'):
            return Path(environ.get('XDG_DATA_HOME'))
        if environ.get('HOME'):
            return Path(environ.get('HOME')) / '.local' / 'share'
        return Path('/')
    return parent_dir() / 'ghaudit' / 'compliance' / 'cache.json'


def graphql_query_file_path():
    return Path(__file__).parent / 'queries' / 'compliance'


def load():
    with open(file_path()) as cache_file:
        return json.load(cache_file)


def store(data):
    with open(file_path(), mode='w') as cache_file:
        return json.dump(data, cache_file)


def graphql_github_fragment_pageInfo_fields():
    return """
fragment pageInfoFields on PageInfo {
  endCursor
  hasNextPage
}
"""


def graphql_github_fragment_repository_fields():
    return """
fragment repositoryFields on Repository {
  id
  name
  description
  isFork
  isArchived
  isLocked
  isMirror
  isPrivate
  isTemplate
}
"""


def graphql_github_fragment_team_fields():
    return """
fragment teamFields on Team {
  id
  name
  privacy
}
"""


def graphql_github_fragment_user_fields():
    return """
fragment userFields on User {
  id
  login
  name
  email
  company
}
"""


def graphql_github_metafragment_in_org(name, fragment, page_infos, edge_fields=None):
    template = """
fragment {{ name }} on Query {
  root: organization(login: $organisation) {
    {{ name }}(first: ${{ name }}Max
    {%- if page_infos %}, after: ${{ name }}Cursor{% endif %}) {
      pageInfo {
        ...pageInfoFields
      }
      edges {
        {%- for field in edge_fields %}
        {{ field }}
        {%- endfor %}
        node {
          ...{{ fragment }}
        }
      }
    }
  }
}
"""
    return {
        'template': template,
        'data': {
            'name': name,
            'fragment': fragment,
            'edge_fields': edge_fields if edge_fields else [],
            'page_infos': page_infos
        }
    }


def graphql_github_metafragment_depth2(fragment_name, name, type_name, child_fragment, params):
    template = """
fragment {{ fragment_name }} on Query {
  {{ name }} : organization(login: $organisation) {
    {{ type }}({% for param in params %}{% if not loop.first %}, {% endif %}{{ param }}{% endfor %}) {
      edges {
        node {
          ...{{ child_fragment }}
        }
      }
    }
  }
}
"""
    return {
        'template': template,
        'data': {
            'fragment_name': fragment_name,
            'name': name,
            'type': type_name,
            'child_fragment': child_fragment,
            'params': params
        }
    }

def graphql_github_metafragment_depth2b(fragment_name, name, type_name, child_fragment, params):
    template = """
fragment {{ fragment_name }} on Query {
  {{ name }} : organization(login: $organisation) {
    {{ type }}({% for param in params %}{% if not loop.first %}, {% endif %}{{ param }}{% endfor %}) {
      ...{{ child_fragment }}
    }
  }
}
"""
    return {
        'template': template,
        'data': {
            'fragment_name': fragment_name,
            'name': name,
            'type': type_name,
            'child_fragment': child_fragment,
            'params': params
        }
    }


def graphql_github_metafragment_sub_fields(
        fragment_name,
        parent_type,
        connection,
        params,
        edge_fields):
    template = """
fragment {{ fragment_name }} on {{ parent_type }} {
  id
  {{ connection }}({% for param in params %}{% if not loop.first %}, {% endif %}{{ param }}{% endfor %}) {
    pageInfo {
      ...pageInfoFields
    }
    edges {
      {%- for field in edge_fields %}
      {{ field }}
      {%- endfor %}
      node {
        id
      }
    }
  }
}
"""
    return {
        'template': template,
        'data': {
            'fragment_name': fragment_name,
            'parent_type': parent_type,
            'connection': connection,
            'params': params,
            'edge_fields': edge_fields
        }
    }


def render(infos):
    return jinja2.Template(infos['template']).render(infos['data'])


def page_info_continue(page_infos):
    if not page_infos or page_infos['hasNextPage']:
        return True
    return False


def graphql_github_buildquery(page_infos, teams_repos_queue,
                              teams_members_queue, repos_collaborators_queue):
    fragments = graphql_github_fragment_pageInfo_fields()
    fragment_names = []
    query_args = []
    if page_info_continue(page_infos['repos']):
        fragments += graphql_github_fragment_repository_fields()
        fragments += render(graphql_github_metafragment_in_org(
            'repositories',
            'repositoryFields',
            page_infos['repos']
        ))
        fragment_names.append('repositories')
        query_args.append('$repositoriesMax: Int!')
        if page_infos['repos'] and page_infos['repos']['endCursor']:
            query_args.append('$repositoriesCursor: String!')
    if page_info_continue(page_infos['teams']):
        fragments += graphql_github_fragment_team_fields()
        fragments += render(graphql_github_metafragment_in_org(
            'teams',
            'teamFields',
            page_infos['teams']
        ))
        fragment_names.append('teams')
        query_args.append('$teamsMax: Int!')
        if page_infos['teams'] and page_infos['teams']['endCursor']:
            query_args.append('$teamsCursor: String!')
    if page_info_continue(page_infos['members']):
        fragments += graphql_github_fragment_user_fields()
        fragments += render(graphql_github_metafragment_in_org(
            'membersWithRole',
            'userFields',
            page_infos['members'],
            ['role']
        ))
        fragment_names.append('membersWithRole')
        query_args.append('$membersWithRoleMax: Int!')
        if page_infos['members'] and page_infos['members']['endCursor']:
            query_args.append('$membersWithRoleCursor: String!')
    if teams_repos_queue:
        fragments += render(graphql_github_metafragment_sub_fields(
            'repoTeamsFields',
            'Team',
            'repositories',
            ['first: $teamReposMax'],
            ['permission']
        ))
        query_args.append('$teamReposMax: Int!')
    if teams_members_queue:
        fragments += render(graphql_github_metafragment_sub_fields(
            'memberTeamsFields',
            'Team',
            'members',
            ['first: $teamMembersMax'],
            ['role']
        ))
        query_args.append('$teamMembersMax: Int!')
    if repos_collaborators_queue:
        fragments += render(graphql_github_metafragment_sub_fields(
            'collaboratorReposFields',
            'Repository',
            'collaborators',
            ['first: $collaboratorsReposMax'],
            ['permission']
        ))
        query_args.append('$collaboratorsReposMax: Int!')
    i = 0
    for team in teams_repos_queue:
        fragments += render(graphql_github_metafragment_depth2(
            'repoTeams{}'.format(i),
            'team{}'.format(i),
            'teams',
            'repoTeamsFields',
            ['first: 1', 'query: "' + team + '"']
        ))
        fragment_names.append('repoTeams{}'.format(i))
        i += 1
    i = 0
    for team in teams_members_queue:
        fragments += render(graphql_github_metafragment_depth2(
            'memberTeams{}'.format(i),
            'team{}'.format(i),
            'teams',
            'memberTeamsFields',
            ['first: 1', 'query: "' + team + '"']
        ))
        fragment_names.append('memberTeams{}'.format(i))
        i += 1
    i = 0
    for repo in repos_collaborators_queue:
        fragments += render(graphql_github_metafragment_depth2b(
            'collaboratorRepos{}'.format(i),
            'repo{}'.format(i),
            'repository',
            'collaboratorReposFields',
            ['name: "' + repo + '"']
        ))
        fragment_names.append('collaboratorRepos{}'.format(i))
        i += 1
    query = 'query org_infos($organisation: String!'
    for arg in query_args:
        query += ', {}'.format(arg)
    query += ') {\n'
    for name in fragment_names:
        query += '  ...{}\n'.format(name)
    query += '}'
    return fragments + '\n\n' + query


def update_page_infos(result):
    org = result['data']['root']
    repos_page_infos = org['repositories']['pageInfo'] if 'repositories' in org else {'hasNextPage': False}
    teams_page_infos = org['teams']['pageInfo'] if 'teams' in org else {'hasNextPage': False}
    members_page_infos = org['membersWithRole']['pageInfo'] if 'membersWithRole' in org else {'hasNextPage': False}
    return {
        'repos': repos_page_infos,
        'teams': teams_page_infos,
        'members': members_page_infos
    }


def node_query_generator():
    def plop_fragment():
        return 'fragment plop on Query { content }'
    return {
        'fragment': plop_fragment,
        'fragment_name': 'plop',
        'args': [{'name': 'name', type: 'String!'}]
    }


# pseudo code for a more generic method:
# def paginate(config, auth_driver, result = None):
#     query = ''             # the query string
#     fragments = []         # list of fragment names to call from the query
#     args = []              # list of args to declare in the query
#     params = []            # parameters passed in json along the query
#     params['organisation'] = config['organisation']['name']
#     nodes = {}
#     data = schema.empty()
#     # register nodes for 'repositories', 'teams', and 'membersWithRole'
#     while funcools.reduce(lambda x, y: x or page_info_continue(y), [page_info_get(x) in nodes], False):
#         # step 1 render query
#         for node in nodes:
#             name = node['name']
#             page_info = page_info_get(name, result)
#             if page_info_continue(page_info):
#                 query += node['render'](page_info_args(name))
#                 fragments.append(node['fragment_name']())
#                 args += page_info_args(name)
#                 params += page_info_params(name)
#                 render_main_query(fragments, args) # combine all fragments in one query
#         # step 2 send query
#         result = github_graphql_call(query, auth_driver, params)
#         # step 3 process result
#         # check for 'errors' in result
#         new_nodes = node['process_result'](result)
#         for elem in result['data'].values():
#             data = schema.merge(data, {'data': {'organisation': result}})
#     store(data)


def gather_org_infos(config, auth_driver):
    page_infos = {
        'repos': None,
        'teams': None,
        'members': None
    }
    params = {
        'organisation': config['organisation']['name'],
        'repositoriesMax': 15,
        'teamsMax': 15,
        'membersWithRoleMax': 30,
        'teamReposMax': 30,
        'teamMembersMax': 50,
        'collaboratorsReposMax': 50
    }
    teams_repos_queue = []
    teams_members_queue = []
    repos_collaborators_queue = []
    data = schema.empty()
    while functools.reduce(lambda x, y: x or page_info_continue(y), page_infos.values(), False):
        query = graphql_github_buildquery(
            page_infos, teams_repos_queue, teams_members_queue, repos_collaborators_queue
        )
        if page_infos['repos'] and page_infos['repos']['hasNextPage']:
            params['repositoriesCursor'] = page_infos['repos']['endCursor']
        if page_infos['teams'] and page_infos['teams']['hasNextPage']:
            params['teamsCursor'] = page_infos['teams']['endCursor']
        if page_infos['members'] and page_infos['members']['hasNextPage']:
            params['membersWithRoleCursor'] = page_infos['members']['endCursor']
        print(query)
        print(params)
        result = github_graphql_call(query, auth_driver, params)
        print(json.dumps(result))
        print('')
        print('')
        print('')
        page_infos = update_page_infos(result)
        print(page_infos)
        if 'repositoriesCursor' in params:
            params.pop('repositoriesCursor')
        if 'teamsCursor' in params:
            params.pop('teamsCursor')
        if 'membersWithRoleCursor' in params:
            params.pop('membersWithRoleCursor')
        # TODO paginate in queues as well
        teams_repos_queue = []
        teams_members_queue = []
        repos_collaborators_queue = []
        for item in result['data'].values():
            data = schema.merge(data, {'data': {'organization': item}})
        if 'teams' in result['data']['root']:
            for team in result['data']['root']['teams']['edges']:
                teams_repos_queue.append(team['node']['name'])
                teams_members_queue.append(team['node']['name'])
        if 'repositories' in result['data']['root']:
            for repo in result['data']['root']['repositories']['edges']:
                repos_collaborators_queue.append(repo['node']['name'])
    store(data)


def refresh(config, auth_driver):
    ofilepath = file_path()
    if not path.exists(ofilepath.parent):
        makedirs(ofilepath.parent)
    gather_org_infos(config, auth_driver)
    # in organisation: gather all repositories, all members, all teams
    # in each repositories: gather all collaborators
    # in each teams: gather all members and repositories access


def github_graphql_call(call_str, auth_driver, variables):
    result = requests.post(
        GITHUB_GRAPHQL_ENDPOINT,
        json={'query': call_str, 'variables': json.dumps(variables)},
        headers=auth_driver()
    )
    if result.status_code != 200:
        error_fmt = (
            'Call failed to run by returning code of {}.'
            'Error message: {}.'
            'Query: {}'
        )
        raise Exception(error_fmt.format(
            result.status_code,
            result.text,
            call_str
        ))
    return result.json()
