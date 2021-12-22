from typing import Any, Mapping

from ghaudit.query.sub_query import ValidValueType
from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class RepoBranchProtectionQuery(SubQueryCommon):
    FRAG_REPO_BRANCH_PROTECTION_EDGE = "frag_repo_branch_protection_edge.j2"
    FRAG_REPO_BRANCH_PROTECTION_ENTRY = "frag_repo_branch_protection_entry.j2"


    def __init__(self, repository: str, num: int, max_: int) -> None:
        SubQueryCommon.__init__(
            self,
            [
                RepoBranchProtectionQuery.FRAG_REPO_BRANCH_PROTECTION_EDGE,
                RepoBranchProtectionQuery.FRAG_REPO_BRANCH_PROTECTION_ENTRY,
            ],
            "repoBranchProtectionRules{}".format(num),
            {"organisation": "String!", "branchProtectionMax": "Int!"},
        )
        self._repository = repository
        self._num = num
        self._values["branchProtectionMax"] = max_

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        root = "repo{}".format(self._num)
        cursor_name = "repo{}BranchprotectionCursor".format(self._num)
        if root in response and "repository" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            if response[root]["repository"]["branchProtectionRules"]:
                page_info = response[root]["repository"][
                    "branchProtectionRules"
                ][
                    "pageInfo"
                ]  # type: PageInfo
            else:
                page_info = {"hasNextPage": False, "endCursor": None}
            self._page_info = page_info
            self._values[cursor_name] = self._page_info["endCursor"]
            self._count += 1

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        return SubQueryCommon.render(
            self,
            {**args, **{"num": self._num, "repository": self._repository}},
        )
