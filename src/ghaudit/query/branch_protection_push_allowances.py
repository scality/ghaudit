from typing import Any, Mapping

from ghaudit.query.sub_query import ValidValueType
from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class BranchProtectionPushAllowances(SubQueryCommon):

    FRAGMENTS = ["frag_branch_protection_push_allowances.j2"]

    def __init__(self, bp_id: str, num: int, max_: int) -> None:
        SubQueryCommon.__init__(
            self,
            self.FRAGMENTS,
            "branchProtection{}".format(num),
            {"pushAllowancesMax": "Int!"},
        )
        self._bp_id = bp_id
        self._num = num
        self._values["pushAllowancesMax"] = max_

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        root = "branch_protection{}".format(self._num)
        cursor_name = "bp{}pushAllowanceCursor".format(self._num)
        if root in response and "pushAllowances" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            page_info = response[root]["pushAllowances"][
                "pageInfo"
            ]  # type: PageInfo
            self._iterate(page_info, cursor_name)

    def render(self, args: Mapping[str, ValidValueType]) -> str:
        return SubQueryCommon.render(
            self, {**args, "num": self._num, "bp_id": self._bp_id}
        )
