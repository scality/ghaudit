from ghaudit.query.sub_query_common import SubQueryCommon


class OrgMembersQuery(SubQueryCommon):
    FRAG_ORG_MEMBERS_FIELDS = """
fragment userFields on User {
  id
  login
  name
  email
  company
}
"""

    FRAG_ORG_MEMBERS = """
fragment membersWithRole on Query {
  root: organization(login: $organisation) {
    membersWithRole(first: $membersWithRoleMax{% if page_infos %}, after: $membersWithRoleCursor{% endif %}) {
      pageInfo {
        ...pageInfoFields
      }
      edges {
        role
        node {
          ...userFields
        }
      }
    }
  }
}
"""

    def __init__(self):
        SubQueryCommon.__init__(
            self,
            [
                OrgMembersQuery.FRAG_ORG_MEMBERS_FIELDS,
                OrgMembersQuery.FRAG_ORG_MEMBERS,
            ],
            "membersWithRole",
            {"organisation": "String!", "membersWithRoleMax": "Int!"},
        )

    def update_page_info(self, response):
        if "root" in response and "membersWithRole" in response["root"]:
            if not self._page_info:
                self._params["membersWithRoleCursor"] = "String!"
            self._page_info = response["root"]["membersWithRole"]["pageInfo"]
            self._values["membersWithRoleCursor"] = self._page_info[
                "endCursor"
            ]
            self._count += 1
