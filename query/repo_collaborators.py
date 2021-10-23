
from ghaudit.query.sub_query_common import SubQueryCommon


class RepoCollaboratorQuery(SubQueryCommon):
    FRAG_REPO_USER_EDGE = """
fragment repo{{ num }}CollaboratorFields on Repository {
  id
  collaborators(first: $repoCollaboratorMax{% if page_infos %}, after: $repo{{ num }}CollaboratorCursor{% endif %}) {
    pageInfo {
      ...pageInfoFields
    }
    edges {
      permission
      node {
        id
        login
      }
    }
  }
}
"""

    FRAG_REPO_USER_ENTRY = """
fragment repoCollaborator{{ num }} on Query {
  repo{{ num }} : organization(login: $organisation) {
    repository(name: "{{ repository }}") {
      ...repo{{ num }}CollaboratorFields
    }
  }
}
"""

    def __init__(self, repository, num, max_):
        SubQueryCommon.__init__(
            self,
            [RepoCollaboratorQuery.FRAG_REPO_USER_EDGE,
             RepoCollaboratorQuery.FRAG_REPO_USER_ENTRY],
            'repoCollaborator{}'.format(num),
            {'organisation': 'String!', 'repoCollaboratorMax': 'Int!'}
        )
        self._repository = repository
        self._num = num
        self._values['repoCollaboratorMax'] = max_

    def update_page_info(self, response):
        root = 'repo{}'.format(self._num)
        cursor_name = 'repo{}CollaboratorCursor'.format(self._num)
        if root in response and 'repository' in response[root]:
            if not self._page_info:
                self._params[cursor_name] = 'String!'
            if response[root]['repository']['collaborators']:
                page_info = response[root]['repository']['collaborators']['pageInfo']
            else:
                # collaborators can have the value None
                page_info = {'hasNextPage': False, 'endCursor': None}
            self._page_info = page_info
            self._values[cursor_name] = self._page_info['endCursor']
            self._count += 1

    def render(self, args):
        args['num'] = self._num
        args['repository'] = self._repository
        return SubQueryCommon.render(self, args)

    def __repr__(self):
        return '{}({}, {}): {}'.format(
            self._entry, self._count, self._repository, repr(self._page_info)
        )
