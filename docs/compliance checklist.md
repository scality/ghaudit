
errors:

(repositories in scope: not excluded, not archived, not forks)

 * teams not referenced in config with access to a repository in the scope of the policy
 * repositories that should be in scope but not referenced by the policy
 * team in the policy with access to a good repo, but with incorrect access rights
 * team in the policy with access to a good repo it should not be given access to
 * team members that should not be in the team
 * missing team member in github according to ghaudit configuration
 * organisation member that is not mapped in the usermap
 * user mapped un the usermap, but not present in the organisation
 * user with an access to a repository it should not be given access to
 * user with an access to a repository it should be given access to, but with different access rights
 * missing team in github according to the configuration
 * missing repository in github according to the configuration

the difference is made between access level too low or too high

warnings:

 * teams not referenced in config but without access to any repository in scope
 * repository referenced in policy but marked as either among: archived, forks
