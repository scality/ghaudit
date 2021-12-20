from typing import Any, Mapping

from ghaudit.query.sub_query import ValidValueType
from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class TeamMemberQuery(SubQueryCommon):
    FRAG_TEAM_MEMBER_EDGE = """
fragment team{{ num }}MemberRole on Team {
  id
  members(first: $teamMemberMax{% if page_infos %}, after: $team{{ num }}MemberCursor{% endif %}) {
    pageInfo {
      ...pageInfoFields
    }
    edges {
      role
      node {
        id
      }
    }
  }
}
"""

    FRAG_TEAM_MEMBER_ENTRY = """
fragment teamMember{{ num }} on Query {
  team{{ num }} : organization(login: $organisation) {
    team(slug: "{{ team }}") {
      ...team{{ num }}MemberRole
    }
  }
}
"""

    def __init__(self, team: str, num: int, max_: int) -> None:
        SubQueryCommon.__init__(
            self,
            [
                TeamMemberQuery.FRAG_TEAM_MEMBER_EDGE,
                TeamMemberQuery.FRAG_TEAM_MEMBER_ENTRY,
            ],
            "teamMember{}".format(num),
            {"organisation": "String!", "teamMemberMax": "Int!"},
        )
        self._team = team
        self._num = num
        self._values["teamMemberMax"] = max_

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        root = "team{}".format(self._num)
        cursor_name = "team{}MemberCursor".format(self._num)
        if root in response and "team" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            page_info = response[root]["team"]["members"][
                "pageInfo"
            ]  # type: PageInfo
            self._page_info = page_info
            self._values[cursor_name] = self._page_info["endCursor"]
            self._count += 1

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        return SubQueryCommon.render(
            self, {**args, **{"num": self._num, "team": self._team}}
        )

    def __repr__(self) -> str:
        return "{}({}, {}): {}".format(
            self._entry, self._count, self._team, repr(self._page_info)
        )
