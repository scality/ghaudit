from typing import Any, Mapping

from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class OrgRepoQuery(SubQueryCommon):
    FRAG_ORG_REPO_FIELDS = "frag_org_repo_fields.j2"
    FRAG_ORG_REPO = "frag_org_repo.j2"


    def __init__(self) -> None:
        SubQueryCommon.__init__(
            self,
            [OrgRepoQuery.FRAG_ORG_REPO_FIELDS, OrgRepoQuery.FRAG_ORG_REPO],
            "repositories",
            {"organisation": "String!", "repositoriesMax": "Int!"},
        )

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        if "root" in response and "repositories" in response["root"]:
            if not self._page_info:
                self._params["repositoriesCursor"] = "String!"
            self._page_info = response["root"]["repositories"][
                "pageInfo"
            ]  # type: PageInfo
            self._values["repositoriesCursor"] = self._page_info["endCursor"]
            self._count += 1
