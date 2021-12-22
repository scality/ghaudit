from typing import Any, Mapping

from ghaudit.query.sub_query import ValidValueType
from ghaudit.query.sub_query_common import SubQueryCommon


class UserQuery(SubQueryCommon):
    FRAG_USER = "frag_user.j2" 


    def __init__(self, login: str, num: int) -> None:
        SubQueryCommon.__init__(
            self, [UserQuery.FRAG_USER], "user{}".format(num), {}
        )
        self._login = login
        self._num = num

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        self._page_info = {"hasNextPage": False, "endCursor": None}

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        return SubQueryCommon.render(
            self, {**args, **{"login": self._login, "num": self._num}}
        )
