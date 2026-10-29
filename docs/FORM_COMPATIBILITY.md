# WML Form Compatibility Matrix / WML 表单兼容性核验

**2026-10-29 · v0.6.1 · offline regression suite only**

## Objective / 目标

Test the restricted, **non-executing** WML GET form planner against legacy syntax and security-sensitive corner cases. These are synthetic or captured-fixture tests, **not** claims that arbitrary WAP services can accept requests or that native WSP/WDP is supported. The original frozen R5 decoder remains unchanged.

## Compatibility results / 兼容性结果

| Case / 场景 | Plan result / 规划结果 | Rationale / 原因 |
| --- | --- | --- |
| Literal same-origin GET with 1–8 simple `postfield` variable references | Accepted **offline** | Explicit values, exact control binding and query-encoding checks |
| UTF-8 Chinese input, space and ampersand | Accepted **offline** | Query encoding and hash verified; no value echo |
| Single select with unique declared option values | Accepted **offline** | Exact option membership required |
| GB2312 XML, explicit `accept-charset="utf-8"` | Accepted **offline** | Supported UTF-8 submission declared by page |
| GB2312 XML, omitted `accept-charset` | Rejected | Cannot assume device's original-charset behavior matches UTF-8 |
| Duplicate WML control names | Rejected | Ambiguous variable binding |
| `<onevent>`, `<timer>`, `<refresh>`, `<prev>`, `<setvar>` in active card | Rejected | Device-level state/variable side effects not emulated |
| Input `format` / `emptyok` constraints | Rejected when required for a planned field | WML masks and empty-value semantics not implemented |
| `<select multiple="true">` | Rejected | WML multi-select GET submits multiple name/value pairs |
| Duplicate `<option>` values / option `onpick` | Rejected | Ambiguous selection or navigation event |
| Unsupported input type, invalid `maxlength` | Rejected | Avoid silently ignoring input validation |
| Dynamic `href`, nonliteral URI query, fragment or other variable syntax | Rejected | Target must remain static; no guessing |
| POST, cross-origin, secret field, sensitive target path, mutation-looking route | Rejected | Refuse potentially unsafe or authenticated operation |
| Captured-body SHA mismatch | Rejected | Source-bound R5 evidence required |

## Execution gate decision / 执行接口决定

**Do not enable GET form submission yet.** A correct request encoding is **not** evidence of an idempotent or side-effect-free endpoint. The parser's syntax rules cannot prove whether the server treats GET as a search, registration, deletion, or payment action. An Agent-provided `execute: true` boolean would be insufficient protection.

Prior to any future execution feature, require all of the following: (1) specific operator-approved public test origin and a documented read-only search endpoint; (2) per-action review of destination and exact parameter semantics, rather than a generic user flag; (3) no cookies, authentication, credentials, automatic retries, redirects, or post requests; (4) strict connection/IP validation identical to the existing collector; (5) bounded request frequency, no scanning/crawling; (6) a tested kill switch and exact-request audit record with a privacy assessment. Until those conditions can be independently demonstrated, the CLI and MCP remain **dry-run only**.

## Evidence and test boundaries / 证据边界

- `tests/test_form_plan.py`: v0.6.0 validation plus 12 v0.6.1 cases for ambiguity, events, character encoding and unimplemented controls.
- The original R5 archive is SHA-256 checked in CI and its original 139 tests still run.
- The WMLC read/decode path has an existing binary fixture; **this round does not establish that GET form planning handles every WMLC dialect or real-world server**.
- No live third-party form request was sent during this round.

References: [WAP-238-WML 11 September 2001](https://www.wapforum.org/tech/documents/WAP-238-WML-20010911-a.pdf) (GET postfield query rules, multiple-selection treatment).
