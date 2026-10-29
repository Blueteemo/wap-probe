# WAP Probe

**Rootless WML/WMLC reading for local AI Agents — backed by reproducible WAP evidence.**

[简体中文](README.md) | **English**

WAP Probe lets a locally running Agent fetch a public WML page, read its
text, follow a link extracted from the verified page, and go back.
It offers a JSON command-line interface and a local **MCP stdio** server.
There is no privileged service, external API, browser automation, or
automated site crawler.

The repository also preserves the frozen R5 WML/WBXML parser and the
2026 Chinese WAP website survey.

> **Status:** private development repository, not yet approved for public
> redistribution. License/provenance of the bundled historical R5 archive
> has not been finalized; **do not assume this repository is open source**.

## What works today

| Capability | Status |
| --- | --- |
| Public HTTP/HTTPS GET, strict DNS/IP validation, no redirects | Supported |
| WML text (UTF-8, GB2312/GBK, Big5) | Supported |
| Read-only WML/WMLC form inspection | Inputs, select options, GET/POST actions, postfields and variable markers |
| Offline GET form request planning | Validated/redacted dry-run only; no GET/POST submission |
| WMLC/WBXML card text decoded via frozen R5 parser | Supported for tested WML code page 0 |
| Safe, same-origin, GET-only link navigation | Supported; one request per step |
| Multi-card WML/WMLC views and local `#card` navigation | Supported; current card only |
| Offline read/back and session history | Supported; up to 8 fetched pages, 64 history actions |
| JSON CLI and local MCP stdio tools | Supported |
| WMLScript, POST/forms, cookies/auth, HTML rendering | Not supported |
| Native WSP/WDP carrier gateway and physical Nokia compatibility | Not supported / not tested |

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
`links`, `form_preview`, `form_submission_supported`, `sha256`, `cursor` and
`page_count`. Non-WML responses and errors are reported, not treated as
valid content. Raw evidence in local sessions may include **Set-Cookie**;
keep the entire session folder private and never commit it.

## MCP stdio integration

Configure your MCP-capable Agent to spawn a **local subprocess**:

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
call must also set `execute: true`. Remove the flag for offline-only use.
Five tools are exposed: `wap_open`, `wap_follow`, `wap_read`,
`wap_back`, and `wap_card`. `wap_card` is offline-only: it selects an existing verified deck card using `session_id` and `index`. MCP sessions are ephemeral and referenced by opaque
`session_id` values (never arbitrary filesystem paths).

The local, dependency-free server implements the tested MCP **2025-11-25
stdio JSON-RPC tool subset**, not Streamable HTTP or every optional MCP
capability. Each stdout line is a protocol message; no listening port or
remote transport is opened.

## Reproduce offline tests

```bash
python3 -m zipfile -e vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip .r5_unpacked
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
