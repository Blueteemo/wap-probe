# WAP Probe 公开发布审查 / Public Repository Readiness

**审查日期 / Reviewed: 2026-10-29**  
**目标 / Goal: prepare for an eventual public, usable WAP Probe source repository; keeping it private indefinitely is NOT a product requirement.**

## 最新公开路线决定 / Active publication plan (2026-10-30)

**只维护现有一个仓库：直接在 `Blueteemo/wap-probe` 原地公开。** 项目所有者明确不希望为了公开再维护两个仓库。本报告后文关于“方案 B / 干净独立公开版本”的历史试验属于保留的技术研究记录，**现已不再作为正式开源执行路线**；其构建脚本可留作内部维护辅助，不创建第二个 GitHub 仓库。原始 R5 ZIP、提交历史和研究证据继续保留，不擅自删除或重写。

**当前技术验收：** [CI #40948393537](https://github.com/Blueteemo/wap-probe/actions/runs/40948393537) 6/6 Job 全绿；完整仓库 395/395 离线回归，原有便携候选技术验证 79/79。托管 macOS 安装已通过；个人 Mac 实测有价值但**不是自动阻止开源的新增硬性门槛**。

**历史归档实际内容（直接检测解压数据，而非仅凭路径猜测）：**
- 原始 R5 内层研究 ZIP 含 **27 份保存的在线响应文件，去重后 15 种内容**：12 份 HTML、9 份 WML、6 份其他/二进制或非直接标识的响应。数字为归档文件实例数，**不是独立网页站点数**。
- 此前的 **35 项在线取证候选**包含了原始响应以外的 JSON 报告和访问记录，不能与 27 份正文混为一谈。另有两份外部 Kannel WML 参考文档。
- 当前有边界的字节扫描：对上述 27 份响应未发现匹配的电子邮箱样式、HTTP Cookie/Authorization 头或已知凭据模式；**两份重复 HTML 响应包含表单标记**，仅表明页面有表单结构，未发现实际提交的账号凭据。历史代码唯一剩余个人路径信号来自故意构造的脱敏测试样本。
- 本项扫描**不能证明完全无敏感信息，也不代表网页内容获得再分发许可**。公共网站内容可能仍受版权保护；完整 Git 历史与保留的 Actions 日志一旦公开，都将成为第三方可访问资料。

**现在只剩两项真正决定发布的事情：**（1）由所有者确认对项目 Python / AI 辅助源码可授权，并选择适当的开源许可证和需要保留的第三方通知；（2）明确接受并处理历史 15 种归档响应和两份外部 WML 文档的再分发边界。若无法使历史材料具备可公开依据，不能靠删除当前 `main` 中的 ZIP 解决 Git 历史问题；任何历史重写须单独明确授权。

**状态：REVIEW_REQUIRED。** 已确认“一仓库直接公开”的路线，**尚未确认公开操作本身、没有授予 MIT 或其他许可证，也没有创建 Release 或修改可见性**。后续不以重复增添测试、第二仓库或不断追加准备轮次替代这两项发布决定。

---

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

---

## 2026-10-30 第三轮：证据链与历史日志复核 / Provenance and history review

The archive's original `README_R5.md`, `R5_PROGRESS.md`, `RESEARCH_PROGRESS.md` and inner `deepseek_review/README.md` / `REVIEW.md` document the project progression. Earlier project development records attribute the initial `probe/wap_probe.py`, `probe/wap_wbxml.py` and navigator to the user's ChatGPT-assisted v0.3/v0.3.2 work, with a later **separate local DeepSeek research copy and patches**. The frozen v0.3.3/R5 package integrated those changes and was committed to this repository by 千岚之夏 in `8cd230e`. This is a substantially stronger **project-origin explanation** than an unattributed third-party source import, but chat histories and commit metadata are not a signed copyright assignment or an exhaustive code-similarity audit.

The currently applicable [OpenAI Terms of Use](https://openai.com/policies/terms-of-use/) allocate Output rights as between OpenAI and the user, subject to applicable law and third-party rights. This **does not grant rights to external code, original third-party WML webpages, independent model providers' outputs, or other people's contributions**. The local DeepSeek review needs the owner's confirmation that no protected third-party implementation was pasted into that derivative.

**Code-reference boundary (checked against upstream documentation)**:
- `wap_wbxml.py` / nested `make_samples.py` refer to WML/WBXML specifications and Android kXML `Wml.java` token definitions; Android's published [KXML notice](https://android.googlesource.com/platform/prebuilts/fullsdk/platforms/android-30/+/refs/heads/main/data/NOTICE.txt) includes a permissive copyright notice for KXML. Merely referring to public token numbers is not proof of verbatim KXML source copying. **If** a substantial implementation from it was reused, carry the original attribution/notice.
- The nested differential test scripts invoke **separately supplied** `libwbxml` tools; no libwbxml C source file appears in the enumerated 34 historical Python instances. See its [upstream license files](https://github.com/libwbxml/libwbxml). Tool use alone does not relicense our Python code.
- The R5 integration `run_wapcurl.py` calls a separately installed `wapcurl`, while the current independent Lowband fixtures retain `LOWBAND_LICENSE.txt`. See [WAP Labs](https://github.com/dills122/wap-labs) for its MIT license; neither citation nor byte comparisons convey a blanket license for the whole R5 ZIP.

**Archived captured material: separate from parser code**:
- The nested `deepseek_review/evidence/live_walk_*/`, `online_international/`, `online_candidates/` and `wapit/` contain historical responses and reports. `deepseek_review/diff/sources/kannel_*.wml` are external-origin test documents. These are research/interop evidence, **not automatically user-authored WML content**; determine which are first-party/synthetic, redistributable references, or externally captured copyrighted material.
- The outer `probe/fixtures/`, `probe/reports/`, `reports/`, candidate inventories and the nested archive must remain frozen for internal reproducibility. Their names and recorded capture provenance are not equivalent to publication permission.
- None of the above was discarded, rewritten, or independently uploaded as a public artifact.

**Git commit metadata:** at this check, all **77** reachable commits show GitHub noreply email addresses, authored as 千岚之夏 or Blueteemo. There was no personal author email identified in those commit metadata fields. This does not replace commit-body or archived-content review.

**Historical Actions:** on the initial 2026-10-30 inventory there were **103 workflow runs**, including transient research jobs that would become visible on publication. A focused read of **28 non-offline research/manual-source job logs and one representative offline job** (manual public-origin samples, WAP Labs WSP, HTTP/WML, historical differential replay and diagnostics) found **no matches** for the selected GitHub/OpenAI/AWS token patterns, PEM private keys, actual HTTP authorization headers, captured Cookie headers or non-example/non-noreply email addresses. The local-path matches in these job logs corresponded to hosted GitHub runner paths. **These are scoped pattern checks, not a complete manual review of all run bodies or all 103 runs.** Additional runs created after the inventory increase the total.

The expanded *repository* scanner added cookie/authorization headers, sensitive query URLs and absolute personal-home indicators without displaying any matched values. Its first privacy hints were traced to a deliberate fake path in `tests/test_delivery_contract.py` and relative `.../home/...bin` evidence paths in prior READMEs/one-shot workflows. The latter are **not** actual `/home/<user>` directories; the detection has been narrowed to absolute paths. A surviving synthetic test sentinel is not a confirmed privacy exposure.

### Public-readiness gate / 实际剩余决策

| Gate | Current assessment | Needed before Public |
| --- | --- | --- |
| Project Python code origin | ChatGPT-assisted project baseline + local DeepSeek derivative history substantially identified; no vendor libwbxml C/Rust or WAP Labs Rust source found in R5 inventory | Owner attests that the historical edits are their authorized outputs and that no third-party code was pasted without a compatible license |
| Third-party token-table references | Standards/kXML references located; no clear evidence of a copied third-party implementation | Resolve whether attribution is required for verbatim expression, if any; keep third-party notices where applicable |
| Archived external response bytes | Several origin-capture evidence families located | Review copyright and confidentiality of actual response content before publishing whole historical ZIP |
| Credentials/history | Updated automated scan and the focused non-offline job-log checks found no concrete token/header values | Finish targeted review of any unexamined Actions/commit material, not indiscriminate removal |
| Root license | **Not granted** | Owner selects a license for material they can authorize (MIT is a pragmatic option), with explicit third-party exceptions |
| Runtime/install | Full source checkout + R5 immutable ZIP works on Ubuntu and hosted macOS; runtime now extracts only two modules | Personal Mac smoke; source archive/release build acceptance if distributing anything other than full clone |

**Decision:** keep **A (publicize this repository in place)** as the preferred route. Today's provenance evidence meaningfully narrows the rights question, and no concrete proprietary-source-code import has been confirmed. Nonetheless **full historical captured-content clearance and owner licensing authorization remain genuine blockers**. Do not automatically add MIT, publish a release, rewrite Git history or change visibility. If captured third-party files cannot be openly redistributed and remain in this repo's history, a separate **functional** clean public source tree (B) may be necessary; merely deleting them from `main` would not protect historical data.
 
### Source-only release gate passed (2026-10-30)

[GitHub Actions run #40923216137](https://github.com/Blueteemo/wap-probe/actions/runs/40923216137) passed **all six jobs**, including the new source-archive installation job. That job extracted a **fresh `git archive HEAD`**, installed from this copy with Python 3.12 and verified the real `wap-agent`, `wap-mcp` and `wap-wsp-lab` entrypoints and offline WML/WMLC/WSP/MCP smoke. The main regression suite passed **252 current tests + 139 frozen R5 = 391 tests**; Python 3.10/3.12 and macOS 15 clean-install checks remain green.

The selected original **28 non-offline research/manual-source workflow jobs** from the initial 103-run history snapshot have now been reviewed via their retained job logs. No signatures for the selected token/private-key, authorization-header, cookie-header or non-example email categories were found. Earlier "personal home" indicators were traced to either GitHub-runner system paths or relative `/home/` paths in web evidence fixtures; the updated source audit now reports only the deliberate fake-path redaction test. This is still not an assertion that every ordinary historical CI log and third-party captured response is redistributable.

**No tag, Release, top-level license, public visibility change or R5 replacement has been made.** A full source archive is technically viable; publishing it is still conditional on the rights checks described above.


---

## 2026-10-30 第六轮：外部页面原始内容与备选发布包

[CI #40932453885](https://github.com/Blueteemo/wap-probe/actions/runs/40932453885) 已完成整个冻结 R5 ZIP 及其内层研究包的路径级清单，不输出抓取正文：

| 内容类别（保守候选分类） | 文件实例 | 解压后字节 | 不同 SHA-256 内容 |
| --- | ---: | ---: | ---: |
| 内层在线网页响应及取证报告 | **35** | **162,163** | **23** |
| 内层外部 Kannel WML 参考文档 | **2** | **1,334** | 2 |
| 差异测试生成的结果 | 8 | 3,274 | 待逐项认定 |
| 其他历史报告及取证材料 | 14 | 38,829 | 待逐项认定 |
| 参考样本及测试 fixtures | 34 | 5,589 | 待逐项认定 |
| 其他归档数据 | 2 | 4,994 | 待逐项认定 |

以上 **35 项不是 35 份第三方代码、独立网站或独立网页**，其中既有响应正文，也有工具生成的报告，且存在重复。原始来源集中在内层 deepseek_review/evidence 下的 live_walk_bs0dd、live_walk_kannel、online_candidates、online_international、wapit 及 wmlc_guesses 系列。另有 deepseek_review/diff/sources/kannel_main.wml 与 kannel_news.wml 两个单独的外部参考 WML。抓取数据的 SHA-256 证明本地完整性，不代表获得网页内容再分发许可。

**方案 A 的具体未决问题**是原始外站内容随 Git 历史一起公开。根目录补充 MIT 许可证也不能自动为独立第三方网页授权。当前没有足够证据认定所有历史响应均可公开传播，故仍不得一键转 Public。代码来源、外部页面文字和自动生成的取证记录应分开判断。

### 可运行的私有干净源码预演 / Functional private fallback

已新增 scripts/build_clean_source_candidate.py，仅在新目录中构建用于内部验证的候选版本，不修改任何冻结原件或仓库历史。构建时完整 R5 ZIP 仍须验证已固定的 SHA-256，随后只复制两个真正执行的解析器模块及一份合成 WMLC 回归样本，生成独立小 ZIP、校验和与 SOURCE_CANDIDATE_MANIFEST.json；同时保留当前正式 Python 源码、安装描述及 CLI/MCP 离线冒烟程序。原始外站响应、嵌套 DeepSeek 审查包和完整 139 项历史 R5 测试不随候选包输出。

在已授权访问的私有完整仓库中，可执行：

    python scripts/build_clean_source_candidate.py --out /path/to/new-private-candidate

此命令拒绝覆盖已有目录，生成的 manifest 明确标识 publication_authorized=false；**生成技术样本绝非取得公开许可**。解析器、WBXML token 表、合成样本的权利链与本项目顶层许可证仍需明确。

[CI #40933042366](https://github.com/Blueteemo/wap-probe/actions/runs/40933042366) 已在现有 source-archive job 里，从干净候选目录全新安装 Python 包并实际执行三项 CLI 及 MCP 离线端到端冒烟。**6/6 Job 全绿**，现有项目 **255 项测试加冻结 R5 的 139 项测试，共 394/394 通过**。候选小 ZIP 的可复现 SHA-256 为 b9bfde58cf4e41887b9d9cceadd0f222baf0060bd50db438b1cf05f608d43860。

KXML 的 WML token 表可在 Android 历史源文件中核对，其参考的数值表与项目中 Python token 表之间的具体表达、许可和署名要求需做独立判断，不应把标准代码点的对应关系本身当成源代码拷贝的证明。来源：https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/wml/Wml.java

**当前推荐**：方案 A 保留原仓库历史优先，但必须解决其历史外站取证资料分发权；方案 B 已从理论备选变成已通过真实安装测试的内部候选，如果 A 无法合理清理权利障碍，则可继续按 B 准备真正可运行的独立公开项目。两种方案在正式公开前均需项目所有者确定可授权的源码范围及许可证。没有实施可见性变更、LICENSE 授权、Release、Tag、版本号变更、历史重写或 R5 修改。


### 独立便携测试矩阵与最终发布放行事项（2026-10-30）

上轮仅对精简源码候选执行 CLI/MCP 冒烟。现在构建器已纳入以下五份**不依赖私有网页响应**的本地与合成数据回归测试：

- test_agent_browser.py：冻结解析器只读装载、离线页面和权限检查
- test_collector.py：URL/DNS/IP/HTTP 请求安全规则、目录权限
- test_delivery_contract.py：CLI 与 8 项 MCP 工具契约、敏感错误脱敏
- test_navigation.py：同源安全导航、链接选择和校验
- test_security_regressions.py：恶意链接、证据篡改与禁止操作

这些文件在候选清单中显式列出。新增 test_clean_source_candidate.py 只在完整私有仓库的回归集里运行，验证候选的三个 R5 ZIP 成员、每个成员的 SHA-256、便携测试名单、私有发布标记及拒绝覆盖已有目录。该构建器测试不会混入独立候选。

[CI #40934175269](https://github.com/Blueteemo/wap-probe/actions/runs/40934175269) 的 **6 个 Job 全部通过**，候选环境中的 **79/79 项便携回归测试通过**。这不等于完整研究测试集，也不是对任意真实网站或个人 Mac 的实测。完整仓库继续运行其自身测试及冻结 R5 的 139 项原始测试。

**最终人工放行仍需分别处理：**

1. **原创项目代码与历史 R5 解析器权属**：由项目所有者确认其对相关 AI 辅助代码、本地 DeepSeek 修改、所用 WBXML token 表及合成测试样本具备可开放的权利。发现实质第三方拷贝则应履行原始许可证或替换。
2. **历史外站取证资料**：对方案 A 中嵌入 Git 历史的第三方网页响应与 WML 参考文档，取得合理的可分发依据；如无法确认，不能仅从 main 删除后就宣称历史已净化。
3. **许可证与通知**：仅对有授权权利的项目代码选择许可证（例如 MIT），并对经确认需保留的第三方材料分开署名或附原许可；未经所有者确认不能自动创建顶层 LICENSE。
4. **公开路线**：A 适合权属齐备并可公开完整历史时；B 已具备真正可安装和可单独回归的技术基础，但仍需处理代码本身授权，不自动升级为 Public。
5. **个人设备验收**：托管 macOS 15 / Python 3.12 已通过；用户个人 Apple Silicon Mac 尚未复现，发布说明必须区分这两种验证。

结论仍为 REVIEW_REQUIRED。完整仓库、精简候选均尚未获准发布；本次没有添加 LICENSE、发布 Tag/Release、公开仓库或重写历史。


### 2026-10-30 最小源码候选的来源证据补强

直接读取原始 R5 ZIP 内的 `probe/RESEARCH_LOG.md` 后，得到两条此前尚未充分引用的第一手记录：其一，原研究者明确称 `wap_wbxml.py` 是依据公开 WBXML/WML 语义、OMA 标识和 Android kXML token 表编写的 strict subset decoder；其二，自行构造了 **86 字节两卡片 WMLC 样本**。候选保留的 `binary_portal.wmlc` 为 86 字节，构建器现在也检查这一与日志一致的大小。

对照来源包括 [WAP WBXML 规范](https://www.w3.org/1999/06/NOTE-wbxml-19990624/)、[WML token 规范](https://www.wapforum.org/what/technical/spec-wml-19990616.pdf) 与 [Android kXML `Wml.java`](https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/wml/Wml.java)。kXML2 具有宽松许可证及原作者署名要求；项目复用规范编号本身并非代码拷贝的证据，但有表达性复用时仍需保留正确许可证/署名。这是来源证据更充分，**不是**自动确认所有权。

精简候选现在附有独立的 `THIRD_PARTY_REFERENCES.md`，明确说明上述来源、未随包分发的 WAP Labs / libwbxml / 原始网站取证材料，以及尚需所有者授权的部分。此文件不会代替顶层 LICENSE。方案 B 由此具有可供接手者直接阅读的权属审查记录；方案 A 的历史第三方网页内容障碍不受此改进影响。
