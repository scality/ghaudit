from typing import Any, Mapping

from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class OrgTeamsQuery(SubQueryCommon):
    FRAG_ORG_TEAM_FIELDS = """
fragment teamFields on Team {
  id
  name
  slug
  description
  privacy
  parentTeam {
    id
  }
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

    def __init__(self) -> None:
        SubQueryCommon.__init__(
            self,
            [OrgTeamsQuery.FRAG_ORG_TEAM_FIELDS, OrgTeamsQuery.FRAG_ORG_TEAM],
            "teams",
            {"organisation": "String!", "teamsMax": "Int!"},
        )

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        if (
            "root" in response
            and response["root"]
            and "teams" in response["root"]
        ):
            if not self._page_info:
                self._params["teamsCursor"] = "String!"
            self._page_info = response["root"]["teams"][
                "pageInfo"
            ]  # type: PageInfo
            self._values["teamsCursor"] = self._page_info["endCursor"]
            self._count += 1
