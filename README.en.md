# WAP Probe

**Rootless, local, read-only WML/WMLC tools for AI Agents.**

[简体中文](README.md) | English

JSON CLI, local MCP stdio, and a separate bounded WSP/WDP lab. Read public WML, extract tested WMLC/WBXML code page 0 content, switch cards offline, and explicitly follow verified same-origin links.

## Install

Python 3.10+, `curl`, and a full checkout or Git source archive including `vendor/r5/` are required. No privileged service is needed.

```sh
python3 -m venv .venv
. .venv/bin/activate
python -m pip install -e .
python scripts/smoke_clean_install.py
```

A standalone wheel without the R5 source archive is not a complete distribution. The smoke test uses synthetic data and no external network.

## Use

```sh
wap-agent --help
wap-mcp --help
wap-wsp-lab --help
```

Replace the placeholder `wap.example.org` with a public anonymous WML page you are authorized to access:

```sh
wap-agent open 'http://wap.example.org/' --out evidence/session-01 --execute
wap-agent read --session evidence/session-01
# Use only an actual returned links[].index:
wap-agent follow --session evidence/session-01 --link 0 --execute
wap-agent back --session evidence/session-01
```

Use `card --session ... --index ...` for offline card selection. Eligible no-input do/go GET navigation uses the separate `go` command. Form previews and GET plans never submit forms.

Launch `wap-mcp` as a stdio subprocess. Network tools also require the startup flag `--allow-network` and an explicit `execute: true`. See [AGENT.md](AGENT.md) for all eight tools.

## Boundaries

- At most one explicit public HTTP(S) GET per navigation step, public DNS/IP validation and pinning, TLS checks, no automatic redirects, credentials, or cookies.
- Semantic WML/WMLC text extraction, not graphical rendering or complete WML/WBXML conformance.
- No HTML renderer, WMLScript, variable evaluation, form submission, authenticated sessions, or automated crawling.
- The separate connectionless WSP/WDP lab is endpoint-constrained and opt-in. No general carrier gateway, WTP, WTLS, or physical-handset compatibility is claimed.
- Historical live checks do not guarantee present-day site or gateway availability.
- Raw local evidence can include response bodies and Set-Cookie headers; never commit capture directories.

## Verification and provenance

```sh
python3 -m zipfile -e vendor/r5/R5_Public_Runtime_Test_Sources.zip .r5_unpacked
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
 python3 -m unittest discover -s tests -v
```

The workflow also runs the R5 probe/discovery/integrations suites. Seven cases requiring omitted private historical evidence explicitly skip; they are not passes.

Original external response bodies and full research archives remain in private preservation. [R5 provenance](docs/R5_SOURCE.md) · [Third-party notices](THIRD_PARTY_NOTICES.md) · [Research findings](docs/FINAL_FINDINGS_20261029.md).

Owner-controlled project sources are licensed under [MIT](LICENSE), copyright Blueteemo (千岚之夏). Third-party material retains its own terms and is outside the project MIT grant.

See [publication status](docs/PUBLICATION_STATUS.md) for verified remote results and the remaining blocker.
