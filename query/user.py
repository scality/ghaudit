from ghaudit.query.sub_query_common import SubQuery2Common


class UserQuery(SubQuery2Common):

    FRAG_USER = """
fragment user{{ num }} on Query {
  user{{ num }}: user(login: "{{ login }}") {
    id
    login
    name
    email
    company
  }
}
"""

    def __init__(self, login, num):
        SubQuery2Common.__init__(
            self,
            [UserQuery.FRAG_USER],
            'user{}'.format(num),
            {}
        )
        self._login = login
        self._num = num

    def update_page_info(self, response):
        self._page_info = {'hasNextPage': False, 'endCursor': None}

    def render(self, args):
        args['login'] = self._login
        args['num'] = self._num
        return SubQuery2Common.render(self, args)
