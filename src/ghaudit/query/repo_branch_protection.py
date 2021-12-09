from ghaudit.query.sub_query_common import SubQueryCommon


class RepoBranchProtectionQuery(SubQueryCommon):

    FRAG_REPO_BRANCH_PROTECTION_EDGE = """
fragment repo{{ num }}BranchProtectionRulesFields on Repository {
  id
  branchProtectionRules(first: $branchProtectionMax{% if page_infos %}, after: $repo{{num}}BranchprotectionCursor{% endif %}) {
    pageInfo {
      ...pageInfoFields
    }
    nodes {
      id
      allowsDeletions
      allowsForcePushes
      creator {
        login
      }
      dismissesStaleReviews
      isAdminEnforced
      pattern
      requiredApprovingReviewCount
      requiredStatusCheckContexts
      requiresApprovingReviews
      requiresCodeOwnerReviews
      requiresCommitSignatures
      requiresLinearHistory
      requiresStatusChecks
      requiresStrictStatusChecks
      restrictsPushes
      restrictsReviewDismissals
    }
  }
}
"""

    FRAG_REPO_BRANCH_PROTECTION_ENTRY = """
fragment repoBranchProtectionRules{{ num }} on Query {
  repo{{ num }}: organization(login: $organisation) {
    repository(name: "{{ repository }}") {
      ...repo{{ num }}BranchProtectionRulesFields
    }
  }
}
"""

    def __init__(self, repository, num, max_):
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

    def update_page_info(self, response):
        root = "repo{}".format(self._num)
        cursor_name = "repo{}BranchprotectionCursor".format(self._num)
        if root in response and "repository" in response[root]:
            if not self._page_info:
                self._params[cursor_name] = "String!"
            if response[root]["repository"]["branchProtectionRules"]:
                page_info = response[root]["repository"][
                    "branchProtectionRules"
                ]["pageInfo"]
            else:
                page_info = {"hasNextPage": False, "endCursor": None}
            self._page_info = page_info
            self._values[cursor_name] = self._page_info["endCursor"]
            self._count += 1

    def render(self, args):
        args["num"] = self._num
        args["repository"] = self._repository
        return SubQueryCommon.render(self, args)
