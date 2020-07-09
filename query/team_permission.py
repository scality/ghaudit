
from ghaudit.query.sub_query_common import SubQuery2Common


class TeamRepoQuery(SubQuery2Common):
    FRAG_TEAM_REPO_EDGE = """
fragment team{{ num }}RepoPermissions on Team {
  id
  repositories(first: $teamRepoMax{% if page_infos %}, after: $team{{ num }}RepoCursor{% endif %}) {
    pageInfo {
      ...pageInfoFields
    }
    edges {
      permission
      node {
        id
      }
    }
  }
}
"""

    FRAG_TEAM_REPO_ENTRY = """
fragment teamRepo{{ num }} on Query {
  team{{ num }} : organization(login: $organisation) {
    teams(first: 1, query: "{{ team }}") {
      edges {
        node {
          ...team{{ num }}RepoPermissions
        }
      }
    }
  }
}
"""

    def __init__(self, team, num, max_):
        SubQuery2Common.__init__(
            self,
            [TeamRepoQuery.FRAG_TEAM_REPO_EDGE, TeamRepoQuery.FRAG_TEAM_REPO_ENTRY],
            'teamRepo{}'.format(num),
            {'organisation': 'String!', 'teamRepoMax': 'Int!'}
        )
        self._team = team
        self._num = num
        self._values['teamRepoMax'] = max_

    def update_page_info(self, response):
        root = 'team{}'.format(self._num)
        cursor_name = 'team{}RepoCursor'.format(self._num)
        if root in response and 'teams' in response[root]:
            if not self._page_info:
                self._params[cursor_name] = 'String!'
            page_info = response[root]['teams']['edges'][0]['node']['repositories']['pageInfo']
            self._page_info = page_info
            self._values[cursor_name] = self._page_info['endCursor']
            self._count += 1

    def render(self, args):
        args['num'] = self._num
        args['team'] = self._team
        return SubQuery2Common.render(self, args)

    def __repr__(self):
        return '{}({}, {}): {}'.format(
            self._entry, self._count, self._team, repr(self._page_info)
        )
