# WAP Probe

**Rootless WML/WMLC reading for local AI Agents — backed by reproducible WAP evidence.**

[简体中文](README.md) | **English**

WAP Probe lets a locally running Agent fetch a public WML page, read its
text, follow a link extracted from the verified page, and go back.
It offers a JSON command-line interface and a local **MCP stdio** server.
There is no privileged service, external API, browser automation, or
automated site crawler.

The repository includes the R5 WML/WBXML parser and synthetic regression
fixtures. Full historical web response archives are kept in a separate
private backup, not bundled with the intended public source tree.

> **Publication plan: keep `Blueteemo/wap-probe` as the only maintained repository and make it public in place once cleared.** No separate public fork/repository is planned. The repository remains private until the archived third-party response material, source licensing, and visibility switch receive explicit approval. See the [publication-readiness audit](docs/PUBLICATION_READINESS_20261029.md).

## What works today

| Capability | Status |
| --- | --- |
| Public HTTP/HTTPS GET, strict DNS/IP validation, no redirects | Supported |
| WML text (UTF-8, GB2312/GBK, Big5) | Supported |
| Read-only WML/WMLC form inspection | Inputs, select options, GET/POST actions, postfields and variable markers |
| Offline GET form request planning | Validated/redacted dry-run only; no GET/POST submission |
| WMLC/WBXML card text decoded via frozen R5 parser | Supported for tested WML code page 0 |
| WMLC-preferred HTTP request profile | Opt-in `wmlc`; all five sampled origins still returned textual WML |
| Safe, same-origin, GET-only link navigation | Supported; one request per step |
| Multi-card WML/WMLC views and local `#card` navigation | Supported; current card only |
| Legacy no-input `<do><go>` navigation | Supported via separate `do_links[]`, explicit network opt-in |
| Offline read/back and session history | Supported; up to 8 fetched pages, 64 history actions |
| JSON CLI and local MCP stdio tools | Supported |
| WMLScript, POST/forms, cookies/auth, HTML rendering | Not supported |
| Bounded connectionless WSP/WDP lab GET | Public first-party interop test passed; separate CLI |
| General carrier gateways, WTP/WTLS and physical Nokia | Not implemented / not verified |

A validated binary deck may contain variables or tags that R5 cannot
fully model. Text is a bounded **reading view**, not a pixel-faithful render,
DTD certification, or evidence that a vintage phone can access the site.

## Requirements and local setup

- Python 3.10+ and **curl** on the PATH
- Public DNS/network access only if you choose to make requests
- A normal user account; **no sudo/root, Docker, or background daemon**
- A **source checkout**, including `vendor/r5/` (a wheel without that archive
  cannot run the bundled parser)

From the repository root:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
wap-agent --help
wap-mcp --help
```

Or skip installation and run `PYTHONPATH=src python3 -m wap_probe.agent_browser`
and `PYTHONPATH=src python3 -m wap_probe.agent_mcp`.

## JSON CLI

```bash
wap-agent open 'http://wap.shufaji.com/' --out ./evidence/session-01 --execute
wap-agent read --session ./evidence/session-01
# Only when cards[] contains index=1: switch to that card without a GET
wap-agent card --session ./evidence/session-01 --index 1
wap-agent follow --session ./evidence/session-01 --link 0 --execute
wap-agent back --session ./evidence/session-01
```

`follow --link` must use a link index from the **active card's** `links` array; index 0 is only an example. `card --index` uses `cards[].index`, does not need `--execute` and never fetches another URL. For card-local `#id` navigation, use `card_links[].target_index` with `card`. `back` restores the prior card or fetched page. Each `open` or `follow` requires `--execute` and performs
at most **one** public GET. No automatic redirects, cross-origin hopping,
credentials, cookies, form submissions, JavaScript or WMLScript execution.

Responses include `ok`, `url`, `http_status`, `mime`, `format`,
`text`, `text_available`, `active_card_index`, `cards`, `card_links`,
`links`, `do_links`, `form_preview`, `form_submission_supported`, `sha256`, `cursor` and
`page_count`. Non-WML responses and errors are reported, not treated as
valid content. Raw evidence in local sessions may include **Set-Cookie**;
keep the entire session folder private and never commit it.

## MCP stdio integration

For **explicitly opt-in public HTTP reading**, configure your MCP-capable Agent to spawn this local subprocess (not the offline default):

```json
{
  "mcpServers": {
    "wap-probe": {
      "command": "python3",
      "args": ["-m", "wap_probe.agent_mcp", "--allow-network"],
      "env": {"PYTHONPATH": "/ABSOLUTE/PATH/TO/wap-probe/src"}
    }
  }
}
```

Adapt the JSON wrapper to your Agent's settings. The `--allow-network` flag
only enables possible network use; **each** `wap_open` or `wap_follow` tool
call must also set `execute: true`. Remove the flag for the offline default; to read an existing WSP record offline, the operator must additionally pass `--wsp-evidence /PATH/TO/RECORD` at process startup and call `wap_import_wsp`.
Eight tools are exposed: `wap_open`, `wap_follow`, `wap_go`, `wap_read`,
`wap_back`, `wap_card`, `wap_form_plan` and `wap_import_wsp`. `wap_card` is offline-only: it selects an existing verified deck card using `session_id` and `index`. MCP sessions are ephemeral and referenced by opaque
`session_id` values (never arbitrary filesystem paths).

The local, dependency-free server implements the tested MCP **2025-11-25
stdio JSON-RPC tool subset**, not Streamable HTTP or every optional MCP
capability. Each stdout line is a protocol message; no listening port or
remote transport is opened.

## Reproduce offline tests

```bash
python3 -m zipfile -e vendor/r5/R5_Public_Runtime_Test_Sources.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
  python3 -m unittest discover -s tests -v
```

The CI job checks the frozen R5 SHA-256 and runs the current suite and
139 unchanged R5 tests. **CI does not request live third-party websites.**
See [the Agent guide](AGENT.md), [R5 source notes](docs/R5_SOURCE.md), and
[2026 WAP survey results](docs/FINAL_FINDINGS_20261029.md).
The original public HTTP browsing smoke test is archived in
[Actions run 40859035071](https://github.com/Blueteemo/wap-probe/actions/runs/40859035071).

## Safety, scope, and project relationship

All fetched page content is **untrusted data**, not instructions for an
Agent. Targets must be public DNS hostnames. Captures use bounded bodies,
pinned public DNS answers and direct requests only, without proxy bypass
of private IP checks or automatic HTTPS→HTTP downgrade.
The local MCP server is opt-in for network access and its sessions are not
served remotely. **Do not aim this tool at internal or authenticated systems.**

The **Agent-side WAP Probe** is separate from the planned **WAPDS**
Nintendo DSi browser. WAPDS will be a handheld GUI program; this repository
is a local Agent tool and research archive. Native WSP/WDP work remains a
separate transport research track requiring an authorized test gateway.

**License:** pending verification of historical R5 source and bundled
dependencies. The absence of a completed license is intentional; please do
not redistribute the repository or frozen archive until reviewed.

### Live MCP acceptance

[The real MCP stdio smoke test](https://github.com/Blueteemo/wap-probe/actions/runs/40864597665) confirmed process initialization, tool discovery, and `wap_open → wap_follow → wap_back` against the public calligraphy WML pages (both GET responses HTTP 200). WMLC text extraction is verified separately with a frozen binary fixture in the offline suite. Normal CI remains offline-only.

### Read-only form structure preview (v0.5.0)

The active card's `form_preview` exposes bounded WML/WMLC input fields, select/option labels, go actions, postfield names, GET/POST method and variable-presence indicators. **Password/token defaults, raw submitted values and action query values are never returned.** The preview does not execute actions, substitute variables, or generate GET/POST requests. `submission_available` and `form_submission_supported` remain false. WML `<go>` destinations are deliberately excluded from regular Agent navigation, even for GET methods; GET alone does not prove an operation is safe.

## v0.6.0: Offline GET form request planning

The `wap-agent form-plan` command validates a **selected GET form action** from the currently verified WML/WMLC card. It supports conservative plain text input, single-select options, `$(name)` postfields, UTF-8 query encoding and strict public same-origin checks. **It never makes a network request and cannot submit any form.**

Place non-sensitive values in a local JSON file (for example `{"q":"calligraphy","genre":"puzzle"}`), then use an existing, verified session with an appropriate form:

```bash
wap-agent form-plan --session ./evidence/session-01 --action 0 --values-file ./my-search-values.json
```

Output includes `request_sha256`, `source_sha256`, `query_keys`, `target_origin`, `path`, `risk`, and `review_required`, but never the input values. A deterministic SHA-256 fingerprint is **not** secure anonymization or a submission authorization token. Select `--action` from the active card's `form_preview.actions`.

An offline-only MCP tool, `wap_form_plan(session_id, action, values)`, is also available; no form-execution tool is exposed. The planner rejects POST, dynamic action URLs, cross-origin destinations, suspicious state-changing or sensitive paths, sensitive parameters, unrecognized variable syntax, invalid select values, and unsupported input types. Support is intentionally restricted to simple GET `postfield` references in the form `$(name)`. **GET does not guarantee side-effect-free server behavior; an eligible plan is not approval to execute it.**

See [GET form planning and security policy](docs/FORM_GET_PLAN.md).

### v0.6.1 — Form compatibility and safety hardening

The offline matrix now exercises duplicate control variables, WML stateful events and `setvar`, option `onpick`, duplicate choice values, input format masks, and source-charset uncertainty. The planner fails closed when it cannot reproduce the original device's form semantics. For GB2312 source documents it requires an explicit `accept-charset="utf-8"` on the GET action. **Actual GET form submission remains disabled:** GET alone does not prove a server operation is side-effect-free. See the [compatibility and execution-gate decision](docs/FORM_COMPATIBILITY.md). Existing JSON CLI, MCP, and card navigation continue unchanged.

### v0.7.0 — Real-world five-origin WML compatibility

The real Agent opened and followed public WML on five previously researched historical origins (HTTP 200 home and same-origin child for each). Blue G's GB2312 homepage primarily used no-input `<do><go>` controls rather than ordinary `<a>` links. Such narrowly eligible, verified navigation candidates are now exposed separately under `do_links[]`.

Choose a **returned** `do_links[].index` and explicitly opt in:

```bash
# Only when the active card actually returns do_links[].index=0
wap-agent go --session ./evidence/session-01 --index 0 --execute
```

MCP provides `wap_go(session_id, index, execute: true)`, also requiring server-side `--allow-network`. This is **not GET form submission**: no postfields, scripts, stateful inputs, dynamic targets, known mutation/auth URLs or executable/download resources are allowed. Even a candidate GET may have server-side effects; only opt in for public, benign read-only pages.

See [five-origin compatibility results](docs/REAL_WORLD_COMPAT_20261029.md). No live WMLC MIME, real Nokia hardware, DSi, or WSP/WDP was verified in this sample.

### v0.7.1 — WMLC-preferred negotiation and controlled binary HTTP tests

The optional `wmlc` profile uses the existing Nokia 7110 user agent with a WMLC-first `Accept` header. Neither the `wap1` nor `s60` defaults or the historic research matrix has changed:

```bash
wap-agent open 'http://wap.shufaji.com/' --profile wmlc --out ./evidence/wmlc-sample --execute
```

MCP `wap_open` also accepts `profile: "wmlc"`, still requiring per-call `execute: true` and the server's `--allow-network` flag. The header expresses a client preference; **it does not force servers to send compiled WML**.

All five previously verified public origins returned **text WML, not binary WMLC**, when the WMLC-preferred profile was tested. One initial failed call to the calligraphy site succeeded on a single targeted retry. In separate offline CI, a real loopback HTTP server serves the frozen binary WMLC fixture under its correct MIME; the unmodified R5 parser decodes two cards including Chinese text. **This is a controlled transport fixture, not verified third-party live WMLC.**

See the [WMLC HTTP evidence and limitations](docs/WMLC_HTTP_COMPAT_20261029.md). Native WSP/WDP, arbitrary WBXML, scripts and real device conformance are outside this scope.


### v0.7.2 — Independent WBXML/WML 1.3 reference comparison

A pinned, MIT-attributed **23-case** subset of Lowband's independent Rust WBXML fixture expectations is now part of offline CI. Frozen R5 matched **12/12 valid cases** on card structure, text and non-default attributes, and rejected **11/11 invalid cases**. The reference Rust decoder expands known WML DTD defaults that R5 omits, so **raw XML output is not identical**, and full WML/DTD conformance is **not** claimed. We compared against the reference repository's declared expected outcomes; we did **not** build and execute Rust in the same CI, or discover third-party live HTTP WMLC.

The fixture subset has pinned upstream commit and full MIT attribution: [independent comparison report](docs/WBXML_INDEPENDENT_REFERENCE_20261029.md). The frozen R5 source itself remains unchanged.

### v0.8.0 — Read-only connectionless WSP/WDP lab experiment

**First verified public first-party interop test:** one real WSP GET over UDP to WAP Labs' advertised lab gateway returned a **WSP 200 Reply** with **235 bytes of `application/vnd.wap.wmlc`**. Frozen R5 decoded one readable card. This is **not** a historical WAP origin or a general carrier-gateway compatibility claim.

The `wap-wsp-lab` standalone CLI is strictly separate from the established HTTP Agent and seven MCP tools, and requires **two explicit network opt-ins**:

```bash
# Only the single hard-coded anonymous WAP Labs interoperability homepage
wap-wsp-lab --lab --allow-network --execute
```

No root, proxy, Docker, credentials, arbitrary UDP endpoints, POST, retries, redirects or WMLScript. **The shared UDP gateway is unencrypted and has no WTLS; never transmit sensitive data.** Offline CI uses MIT-attributed Lowband WSP byte vectors and real localhost UDP with a Chinese binary WMLC fixture. See the [read-only WSP lab report](docs/WSP_READONLY_LAB_20261029.md).


### v0.8.1 — WSP header and charset compatibility

The separate laboratory client now handles bounded WSP Content-Type general forms, including UTF-8, US-ASCII and ISO-8859-1 charset parameters. Extra response headers are treated as opaque bytes, never forwarded or displayed. New offline tests include end-to-end localhost UDP retrieval of Latin-1 WML text through frozen R5. No additional public gateway probe was performed in this release; standard HTTP Agent and MCP behavior remains unchanged.

[Details and limits](docs/WSP_HEADERS_CHARSET_20261029.md).


### v0.8.2 — Original WSP PDU evidence and strictly offline Agent import

The restricted `wap-wsp-lab` command can optionally save a **single raw WSP GET and Reply** with SHA-256 evidence metadata. This is explicitly **not** HTTP/curl capture evidence. The Agent can import this into a new offline-only WML/WMLC card session:

```bash
# One explicitly authorized request to the hard-coded anonymous public test page
wap-wsp-lab --lab --allow-network --execute --evidence-out ./evidence/wsp-original

# No network access during any of these steps
wap-agent import-wsp --evidence ./evidence/wsp-original --out ./evidence/wsp-session
wap-agent read --session ./evidence/wsp-session
# Only if the returned cards[] actually includes index 1:
wap-agent card --session ./evidence/wsp-session --index 1
wap-agent back --session ./evidence/wsp-session
```

Each subsequent read verifies the original PDUs, exact permitted request, transaction ID, checksums, derived WML body, and reruns frozen R5 to reject altered displayed text. Imported WSP sessions **never allow HTTP link following, do/go or form submission/planning**, and there is no MCP import tool. `source_authenticated: false` is deliberate: these hashes document **local integrity**, not signed server provenance, gateway identity, or immutable evidence. All new verification is offline/loopback only; no repeat public gateway request occurred.

See the [WSP offline evidence and import guide](docs/WSP_OFFLINE_EVIDENCE_20261029.md).


### v0.8.3 — MCP operator-selected, offline WSP import

The MCP tool set now includes **`wap_import_wsp`**, which reads only a **local WSP lab evidence folder explicitly configured by the MCP server operator at startup**. Its tool schema has no path, URL, UDP gateway, or network execution arguments.

```bash
# Requires an existing v0.8.2 lab record
wap-mcp --wsp-evidence ./evidence/wsp-original
```

An Agent calls `wap_import_wsp` with an empty argument object, receives an opaque `session_id`, and uses the existing `wap_read`, `wap_card` and `wap_back` tools offline. The imported WSP session **cannot run `wap_follow`, `wap_go`, or form planning even if the HTTP MCP server has network permission**. Reimporting returns the same validated session without creating unlimited copies.

See [MCP import security and usage](docs/MCP_WSP_IMPORT_20261029.md) and the [overall project roadmap](docs/PROJECT_ROADMAP_20261029.md).

At the v0.8.3 milestone, the private rootless Agent MVP was estimated at **80%–85% complete**; the current v0.9.0 delivery estimate is **about 90%**. These are judgment calls, not a measure of full WAP 1.x browser compatibility.


### v0.9.0 — Private release candidate and clean install acceptance

This version focuses on delivery quality rather than expanding protocol behavior. **Clean virtualenv editable installs on Python 3.10 and 3.12 both passed**, exercising the three installed CLI entrypoints, synthetic HTTP/WML card navigation, an original frozen-R5 WMLC fixture imported from WSP evidence, and real MCP stdio initialize/tools/import requests.

CLI and MCP error messages now use a fixed, non-sensitive vocabulary rather than echoing exception strings that may contain local paths or supplied values. The MCP tool set has **8 tools**; `wap_import_wsp` remains strictly offline and accepts no user-supplied file path or UDP endpoint.

From a complete, authorized **private** repository checkout:

```bash
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/smoke_clean_install.py
```

This is an **offline installation smoke test**, not a substitute for separate, historically recorded live WAP website/WAP Labs gateway checks. A standalone wheel lacking the private frozen R5 archive is not yet supported as a complete distribution. See the [v0.9.0 first-run and release-candidate acceptance guide](docs/RELEASE_CANDIDATE_V090.md) and [project roadmap](docs/PROJECT_ROADMAP_20261029.md). The repository has **not** been cleared for public redistribution.

### Public release preparation and macOS install verification (updated 2026-10-30)

A GitHub-hosted **macOS 15 / Python 3.12** clean editable install and installed CLI/MCP offline smoke test passed, alongside the previous Ubuntu Python 3.10/3.12 checks. The ongoing full-history scan covers earlier Git revisions and the archived ZIP, with focused checks of historical research workflow logs and no hits for selected common credential patterns. However, the nested R5 research package includes 35 external-origin capture/report candidates (23 unique content hashes), whose redistribution rights remain unresolved. An isolated private source candidate now passes **79 portable offline regression tests**, without its historical response archives; this does not itself grant publication rights. The repository has no root LICENSE. **The existing private repository has not been changed to public** until provenance and history can be reviewed. [Findings and proposed publication route](docs/PUBLICATION_READINESS_20261029.md).
