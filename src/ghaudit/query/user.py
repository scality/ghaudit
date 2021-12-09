from ghaudit.query.sub_query_common import SubQueryCommon


class UserQuery(SubQueryCommon):

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
        SubQueryCommon.__init__(
            self, [UserQuery.FRAG_USER], "user{}".format(num), {}
        )
        self._login = login
        self._num = num

    def update_page_info(self, response):
        self._page_info = {"hasNextPage": False, "endCursor": None}

    def render(self, args):
        args["login"] = self._login
        args["num"] = self._num
        return SubQueryCommon.render(self, args)
