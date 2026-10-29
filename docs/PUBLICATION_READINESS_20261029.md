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

---

## 2026-10-30 复核：R5 文件级来源清单与公开决策 / Source-level review

This section supersedes the earlier **raw 44-source-candidate count** for rights triage. It does not rewrite the immutable original archive or assert a license grant.

### 重新核对的统计口径 / Corrected inventory

- Outer R5 ZIP: **83 archive entries**. Nested `probe/research/deepseek_review_original.zip`: **268 entries**, including AppleDouble metadata.
- The original 44 source-like filenames split into **24 primary R5 Python files + 10 nested historical Python files + 10 non-source `__MACOSX/._*.py` AppleDouble entries**.
- The **34 genuine Python file instances represent 33 distinct SHA-256 contents**. The primary and nested `test_http_integration.py` are byte-identical. The other nested `probe/` files are *historical versions*, not proof of new, independent third-party projects.
- The upgraded publication-audit job scanned **436 small Git-history blobs and one historical ZIP** (including the ZIP's nested archive); its selected credential patterns found **zero hits**. This does not clear every form of sensitive data, Action log, or copyright issue.
- Exact outer R5 ZIP SHA-256 is still `cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa`; the 139 original R5 regression cases are preserved.

### 文件清单 / File-level provenance triage

Each file below is **present in the frozen research archive**, with no individual license grant found. Classification is functional provenance evidence, **not confirmed legal authorship**. The project-recorded archive entered Git in commit [`8cd230e`](https://github.com/Blueteemo/wap-probe/commit/8cd230ef22f8b002f88cc850fe3f8143fd4a347e), authored by 千岚之夏; a Git commit author alone does not establish the copyright chain for every earlier generated or imported file.

| R5 primary path(s), relative to `wap-probe-live-discovery-r5/` | Function and source clues | Rights disposition |
| --- | --- | --- |
| `probe/wap_probe.py`, `probe/wap_wbxml.py` | Core original project parsing pipeline; WBXML token tables cite standards/Android kXML as references | **Critical.** Confirm independently implemented code and token-table provenance before A |
| `probe/wap_browser.py`, `probe/wap_capture.py`, `probe/wap_compare.py`, `probe/wap_replay.py` | Historical WML navigation, capture, comparison and replay tools | Project-created code indicated by archive structure and research notes; rights confirmation outstanding |
| `probe/test_browser.py`, `probe/test_capture.py`, `probe/test_compare.py`, `probe/test_external_replay.py`, `probe/test_http_integration.py`, `probe/test_probe.py`, `probe/test_transport_fake_ip.py`, `probe/test_wbxml.py` | 8 R5 local fixtures and regression test modules; `test_http_integration.py` also exists byte-identically in nested history | Project test suite, not evidence of copied external library; rights confirmation outstanding |
| `discovery/discover_links.py`, `discovery/plan_current_probes.py` | Project discovery and candidate planning | Project-specific scripts; rights confirmation outstanding |
| `discovery/test_discover.py`, `discovery/test_plan.py` | Discovery regression tests | Project tests; rights confirmation outstanding |
| `integrations/wap_labs_import.py`, `integrations/run_wapcurl.py`, `integrations/compare_evidence.py` | Project Python interop wrappers; **references/executes** separately provided WAP Labs `wapcurl` rather than bundling Lowband Rust source | Confirm no copied code in wrappers; external command and protocol compatibility do not by themselves impose MIT on wrappers |
| `integrations/test_wap_labs_import.py`, `integrations/test_run_wapcurl.py`, `integrations/test_compare_evidence.py` | Interop tests with synthetic samples | Project tests; rights confirmation outstanding |
| Nested `deepseek_review/probe/wap_probe.py`, `wap_wbxml.py`, `wap_browser.py` | Older historical code snapshots of the same named parser/browser components | Confirm historical origin once, not separate unrelated licensors by default |
| Nested `deepseek_review/probe/test_probe.py`, `test_wbxml.py`, `test_browser.py`, `test_http_integration.py` | Historical project tests; last file is identical to primary copy | Project snapshots; one exact duplicate; rights confirmation outstanding |
| Nested `deepseek_review/diff/make_samples.py`, `diff_wbxml.py`, `roundtrip_lib.py` | Historical differential test tools cite W3C/OMA, Android kXML and **external libwbxml**, rather than containing a libwbxml library distribution | Confirm independent test implementation and any borrowed expression; reference use alone is not source-code relicensing |

There are **no C/Rust/Java/JS source files** among the 34 real entries. Do not count `__MACOSX/` AppleDouble records as code. Do not delete them from the immutable private archive merely to improve the count.

### 第三方边界 / Third-party materials and what they do *not* imply

1. **WAP Labs / Lowband**: independent `tests/fixtures/lowband_*_reference.json` fixtures and `LOWBAND_LICENSE.txt` have MIT attribution and can be managed under that notice. The private R5 archive mentions and uses the separate `wapcurl` tooling for experiments; that does not license the entire R5 tree under MIT. Upstream: [WAP Labs](https://github.com/dills122/wap-labs).
2. **libwbxml**: named in the nested differential testing scripts as an external oracle/CLI, not vendored as a library. Upstream code is LGPL-family licensed; do not reclassify our own Python tests as libwbxml simply because they execute/compare its results. [Upstream](https://github.com/libwbxml/libwbxml).
3. **WML/WBXML standards / Android kXML `Wml.java`**: externally documented token values and format parameters are referenced by `wap_wbxml.py` and `make_samples.py`. Numerical protocol constants and citations are not themselves proof of source copying; compare the actual table implementation and any inherited explanatory text if granting a broad MIT license.
4. **External-site captures**, WML response bodies, historical fixtures and research notes have separate content/provenance/privacy considerations. A legitimate anonymous GET is not automatically permission to republish all captured third-party content. Assess these separately before exposing full Git history.
5. **Archived review pack**: old locally generated `__MACOSX` AppleDouble/quarantine metadata is not source code. Keep in frozen R5 privately for provenance; review any human-sensitive metadata before a public release.

### Publication decision and next gates

**Preferred path: A (same GitHub repository, full history)**, provided the owner can substantiate rights to the R5/earlier agent-generated Python files and decide a top-level license with explicit third-party exceptions; the remaining archive response data and Actions/history are also cleared. We found **no confirmed third-party source-code bundle among the enumerated Python entries**, but also **no documentary license grant for the R5 archive**. Neither outcome supports an automatic switch to Public today.

**Fallback B (clean, usable public version)** is for a *specific* irreducible rights or historical-data problem, not for the mere absence of a LICENSE. The R5 parser remains runtime-critical. Any clean release must ship a confirmed licensable parser or a properly engineered equivalent and prove the same offline WMLC tests; never publish a broken shell.

Before changing visibility: (1) owner confirms authorship/rights chain for historic generated parser and research scripts, especially `wap_wbxml.py` token-table provenance; (2) determine LICENSE and separate third-party notices; (3) manually review historical logs/embedded third-party responses and prior commits for confidential or non-redistributable content; (4) confirm source-only checkout install vs publishable build artifact; (5) present final visibility-change plan to owner for explicit confirmation. **No visibility change, history rewrite, frozen-R5 edit or public Release is authorized by this technical audit.**
