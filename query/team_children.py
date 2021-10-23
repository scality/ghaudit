
from ghaudit.query.sub_query_common import SubQueryCommon


class TeamChildrenQuery(SubQueryCommon):
    FRAG_TEAM_CHILDREN_EDGE = """
fragment team{{ num }}Children on Team {
  id
  childTeams(first: $teamChildrenMax{% if page_infos %}, after: $team{{ num }}ChildrenCursor{% endif %}) {
    pageInfo {
      ...pageInfoFields
    }
    edges {
      node {
        id
      }
    }
  }
}
"""

    FRAG_TEAM_CHILDREN_ENTRY = """
fragment teamChildren{{ num }} on Query {
  team{{ num }} : organization(login: $organisation) {
    teams(first: 1, query: "{{ team }}") {
      edges {
        node {
          ...team{{ num }}Children
        }
      }
    }
  }
}
"""

    def __init__(self, team, num, max_):
        SubQueryCommon.__init__(
            self,
            [TeamChildrenQuery.FRAG_TEAM_CHILDREN_EDGE,
             TeamChildrenQuery.FRAG_TEAM_CHILDREN_ENTRY],
            'teamChildren{}'.format(num),
            {'organisation': 'String!', 'teamChildrenMax': 'Int!'}
        )
        self._team = team
        self._num = num
        self._values['teamChildrenMax'] = max_

    def update_page_info(self, response):
        root = 'team{}'.format(self._num)
        cursor_name = 'team{}ChildrenCursor'.format(self._num)
        if root in response and 'teams' in response[root]:
            if not self._page_info:
                self._params[cursor_name] = 'String!'
            page_info = response[root]['teams']['edges'][0]['node']['childTeams']['pageInfo']
            self._page_info = page_info
            self._values[cursor_name] = self._page_info['endCursor']
            self._count += 1

    def render(self, args):
        args['num'] = self._num
        args['team'] = self._team
        return SubQueryCommon.render(self, args)

    def __repr__(self):
        return '{}({}, {}): {}'.format(
            self._entry, self._count, self._team, repr(self._page_info)
        )
