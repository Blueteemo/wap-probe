# Publication status — 2026-11-01

The existing `Blueteemo/wap-probe` repository remains private. Sources are prepared as version 1.0.0 with the owner-authorized MIT license for owner-controlled material, preserving third-party exclusions. No public visibility change, v1.0 tag or release has been issued.

## Completed verification

The approved targeted rewrite was applied to remote main at `6c26b13a74309fe40b558f81496a2d710b9a4e67`, retaining 98 commits. A fresh GitHub clone passed history/file checks. Main and the retained PR #1 head exclude the original R5 ZIP from their reachable histories. Complete original and immediately-before-update backups remain private.

[History update run](https://github.com/Blueteemo/wap-probe/actions/runs/41301180109) succeeded. [The cleaned revision CI](https://github.com/Blueteemo/wap-probe/actions/runs/41301203014) passed all six jobs: offline tests, source/publication triage, Linux Python 3.10 and 3.12 editable installs, macOS Python 3.12 install, and Git source archive install. Offline regression totals are 387 passed, 7 explicitly skipped, zero failed. Skips require deliberately omitted private historical website evidence.

## Remaining publication blocker

After the rewrite, an authenticated GitHub contents lookup using the old main SHA `5def42ce484d2cbaff3e4f87d8d749c244796bd5` still returned the original R5 ZIP (blob `815970e84330421a6ca761fa4b0aa6b28cd4125c`). This is a residual old-object access result while the repository is private; it does not establish that the archive has been publicly accessible.

Do not treat branch-history cleanup as server-side object erasure. Resolve or explicitly assess this residual access before changing visibility. GitHub's [history-removal guidance](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository) describes cached views and pull-request reference limitations; support removal is not guaranteed for non-sensitive material.

## Release preparation

Chinese/English README, Agent guidance, source boundaries and third-party notices are complete. Version identifiers and the delivery contract are synchronized to 1.0.0. The root MIT license applies only to sources the owner can license, preserving upstream notices. Public visibility and release publication remain blocked by residual old-object access.

The five temporary Actions full-backup artifacts have been deleted and their run artifact lists verified empty. Private preservation copies remain intact. Support request #4935819 was submitted on 2026-11-01; GitHub closed it because this account currently has self-service support only. No server-side removal was performed. Do not misclassify the third-party website bodies as leaked credentials to obtain a different support route. Do not delete/recreate this repository to work around the blocker.
