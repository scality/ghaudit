from ghaudit.query.sub_query_common import SubQueryCommon


class BranchProtectionPushAllowances(SubQueryCommon):

    FRAG_BRANCH_PROTECTION_PUSH_ALLOWANCES = """
fragment branchProtection{{ num }} on Query {
  branch_protection{{ num }}: node(id: "{{ bp_id }}") {

    ... on BranchProtectionRule {
      pushAllowances(first: $pushAllowancesMax{% if page_infos %}, after: $bp{{num}}pushAllowanceCursor{% endif %}) {
        pageInfo {
          ...pageInfoFields
        }
        nodes {
          branchProtectionRule {
            id
            repository {
              id
            }
          }
          actor {
            ... on User {
              id
              __typename
            }
            ... on App {
              id
              __typename
              name
            }
            ... on Team {
              id
              __typename
              name
            }
          }
        }
      }
    }
  }
}
"""

    def __init__(self, bp_id, num, max_):
        SubQueryCommon.__init__(
            self,
            [
                BranchProtectionPushAllowances.FRAG_BRANCH_PROTECTION_PUSH_ALLOWANCES,
            ],
            "branchProtection{}".format(num),
            {"pushAllowancesMax": "Int!"},
        )
        self._bp_id = bp_id
        self._num = num
        self._values["pushAllowancesMax"] = max_

    def update_page_info(self, response):
        root = "branch_protection{}".format(self._num)
        cursor_name = "bp{}pushAllowanceCursor".format(self._num)
        if root in response and "pushAllowances" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            page_info = response[root]["pushAllowances"]["pageInfo"]
            self._page_info = page_info
            self._values[cursor_name] = self._page_info["endCursor"]
            self._count += 1

    def render(self, args):
        args["num"] = self._num
        args["bp_id"] = self._bp_id
        return SubQueryCommon.render(self, args)
