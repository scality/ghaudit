from typing import Any, Mapping

from ghaudit.query.sub_query_common import SubQueryCommon
from ghaudit.query.utils import PageInfo


class OrgMembersQuery(SubQueryCommon):
    FRAG_ORG_MEMBERS_FIELDS = "frag_org_members_fields.j2"
    FRAG_ORG_MEMBERS = "frag_org_members.j2"


    def __init__(self) -> None:
        SubQueryCommon.__init__(
            self,
            [
                OrgMembersQuery.FRAG_ORG_MEMBERS_FIELDS,
                OrgMembersQuery.FRAG_ORG_MEMBERS,
            ],
            "membersWithRole",
            {"organisation": "String!", "membersWithRoleMax": "Int!"},
        )

    def update_page_info(self, response: Mapping[str, Any]) -> None:
        if "root" in response and "membersWithRole" in response["root"]:
            if not self._page_info:
                self._params["membersWithRoleCursor"] = "String!"
            self._page_info = response["root"]["membersWithRole"][
                "pageInfo"
            ]  # type: PageInfo
            self._values["membersWithRoleCursor"] = self._page_info[
                "endCursor"
            ]
            self._count += 1
