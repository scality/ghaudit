from typing import Any, Mapping

from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class OrgTeamsQuery(SubQueryCommon):

    FRAGMENTS = ["frag_org_team_fields.j2", "frag_org_team.j2"]

    def __init__(self) -> None:
        SubQueryCommon.__init__(
            self,
            self.FRAGMENTS,
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
