from typing import Any, Mapping

from ghaudit.query.sub_query import ValidValueType
from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class TeamRepoQuery(SubQueryCommon):
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

    def __init__(self, team: str, num: int, max_: int) -> None:
        SubQueryCommon.__init__(
            self,
            [
                TeamRepoQuery.FRAG_TEAM_REPO_EDGE,
                TeamRepoQuery.FRAG_TEAM_REPO_ENTRY,
            ],
            "teamRepo{}".format(num),
            {"organisation": "String!", "teamRepoMax": "Int!"},
        )
        self._team = team
        self._num = num
        self._values["teamRepoMax"] = max_

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        root = "team{}".format(self._num)
        cursor_name = "team{}RepoCursor".format(self._num)
        if root in response and "teams" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            page_info = response[root]["teams"]["edges"][0]["node"][
                "repositories"
            ][
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
