# .github

Organization profile and shared GitHub metadata for FSW-AppTeam.

## Profile README repository sync

The workflow at `.github/workflows/sync-profile-readme-repos.yml`
updates `profile/README.md` from the GitHub API.
To include private organization repositories in that table, configure the `ORG_REPO_READ_TOKEN`
secret with organization-level read access (`read:org` and repository read permissions).