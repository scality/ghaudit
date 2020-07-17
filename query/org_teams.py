
from ghaudit.query.sub_query_common import SubQuery2Common


class OrgTeamsQuery(SubQuery2Common):
    FRAG_ORG_TEAM_FIELDS = """
fragment teamFields on Team {
  id
  name
  description
  privacy
}
"""

    FRAG_ORG_TEAM = """
fragment teams on Query {
  root: organization(login: $organisation) {
    teams(first: $teamsMax{% if page_infos %}, after: $teamsCursor{% endif %}) {
      pageInfo {
        ...pageInfoFields
      }
      edges {
        node {
          ...teamFields
        }
      }
    }
  }
}
"""

    def __init__(self):
        SubQuery2Common.__init__(
            self,
            [OrgTeamsQuery.FRAG_ORG_TEAM_FIELDS, OrgTeamsQuery.FRAG_ORG_TEAM],
            'teams',
            {'organisation': 'String!', 'teamsMax': 'Int!'}
        )

    def update_page_info(self, response):
        if 'root' in response and 'teams' in response['root']:
            if not self._page_info:
                self._params['teamsCursor'] = 'String!'
            self._page_info = response['root']['teams']['pageInfo']
            self._values['teamsCursor'] = self._page_info['endCursor']
            self._count += 1
