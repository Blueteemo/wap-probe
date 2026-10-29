# WAP Probe 公开发布审查 / Public Repository Readiness

**审查日期 / Reviewed: 2026-10-29**  
**目标 / Goal: prepare for an eventual public, usable WAP Probe source repository; keeping it private indefinitely is NOT a product requirement.**

## 核心判断 / Decision

**公开方向合理，但当前还不能把 `Blueteemo/wap-probe` 原地一键切成 Public。**

The project has no technical or security requirement to remain private forever. It is a good candidate for open source: historical WML/WMLC reading, Agent integration and reproducible WAP interoperability have clear research and community value. However, publication of a full repository is also **redistribution of its bundled archived source and its visible Git history**.

The existing private GitHub repository has **no root LICENSE**. The R5 source archive has no independently located LICENSE/COPYING/NOTICE file inside the zip or its examined nested zip entries. **Lack of a license file does not prove the R5 code is third-party or unpublishable**, but it does mean we have not established who may grant reuse and redistribution rights for the contained sources.

## 实际审查发现 / Automated evidence

The permanent offline CI includes `scripts/audit_publication.py` and uses `git fetch-depth: 0`. Run record: [#40896484977](https://github.com/Blueteemo/wap-probe/actions/runs/40896484977).

| Check | Observation / 检查结果 |
| --- | --- |
| Repository visibility | Private as of review |
| Root license file | **None** |
| Frozen R5 archive | `vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip` |
| Frozen R5 SHA-256 | `cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa` |
| Historical archive license filenames | **0** detected, including nested ZIPs inspected by script |
| Source-like files within R5 archive | **44** (`.py`, `.js`, `.c`, `.h`, `.rs`, `.java`) |
| Git history text blobs examined | **242**, including earlier modified revisions |
| Obvious credential pattern hits | **0** on the selected signature patterns |
| Lowband independently sourced WBXML/WSP fixtures | **MIT attribution already included** in `tests/fixtures/LOWBAND_LICENSE.txt` |
| Automated publication decision | **REVIEW_REQUIRED**, not a license determination |

Secret-pattern scanning is not equivalent to a manual review of historical commit bodies, old Actions logs, private data, provenance or copyright. The 44 source-like files are a count of candidate source files, **not 44 proven third-party works**.

## 必须解决的三件事 / Release blockers

1. **R5 来源与使用权**：确认这份冻结源码和内层历史测试归档哪些由本项目独立完成、哪些引用/改编自第三方，以及所涉及的许可；需明确文件级归属和来源。WAP Labs/Lowband 在此项目中主要作为外部互操作对照资料，其 MIT 参考数据有独立许可声明，但这**不能自动替 R5 的全部内容授予 MIT 许可**。
2. **确定顶层许可证**：仅针对有权授权的原创代码选择 LICENSE（例如 MIT 或其他用户指定的方案），明确第三方材料的例外与归属。不能仅补一个 MIT 文件就断言无来源记录的旧 ZIP 全部 MIT。
3. **发布历史和日志审查**：GitHub 从 Private 切为 Public 会公开代码、Git 提交历史的可访问内容、Actions 历史和日志。最新提交删除文件不会从 Git 历史中删除它。完成检查后才能决定是否直接公开现有仓库。

Official GitHub docs:
- [Setting repository visibility](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/managing-repository-settings/setting-repository-visibility)
- [Licensing a repository](https://docs.github.com/en/repositories/managing-your-repositorys-settings-and-features/customizing-your-repository/licensing-a-repository)
- [Removing sensitive data from repository history](https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/removing-sensitive-data-from-a-repository)

## 推荐公开路径 / Recommended publication route

**优先 A：确认 R5 是原创/有许可的源码，然后将当前项目公开。** 这条路径能保留真实开发历史和 CI 记录，无须为了显得“干净”而另建空壳。审查结束、确定许可证与第三方声明后，再对现有仓库作正式可见性变更。

**备选 B：如果 R5 的部分源码不能合法再分发，建立具有独立、干净历史的公开项目版本**，只放入确认可分发的代码、资料与经允许的测试样本；旧归档仍留在私有研究库。公开版本必须能通过独立的阅读/解析测试，不能删除 R5 却保留无法运行的“完整工具”宣传。可能需要替换该解析组件或把它改造成可选、用户自行合法取得的依赖。

当前**没有**擅自将仓库改为公开、没有添加来源未确认的统一 MIT 许可证、没有删除不可恢复的历史、没有更换冻结 R5，也没有对私有研究材料进行公开上传。

## 与 v0.9.0 交付相关的并行进度

The same CI run [#40896484977](https://github.com/Blueteemo/wap-probe/actions/runs/40896484977) also passed a **clean editable install on a GitHub-hosted macOS 15 runner with Python 3.12**, using the three installed entrypoints and offline HTTP/WML + WSP/WMLC + MCP smoke tests. This **does not** certify the user's actual Apple Silicon Mac, macOS-specific UI, or hardware WAP protocols. Ubuntu Python 3.10/3.12 tests and the full frozen R5 suite remain in place.

**Private v0.9.0 remains usable without a public release.** Public visibility is the next publication decision, not a technical prerequisite for finishing the Agent's read-only MVP.
