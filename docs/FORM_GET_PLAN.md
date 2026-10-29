# WML GET form planning — v0.6.0

## Scope

This is an **offline-only** proposal generator. A GET form is **not** automatically a safe operation. The planner does not create a network connection, submit a form, send cookies, modify session navigation, or save input values. There is no `form-execute` CLI command or MCP tool.

The WML specification defines GET form behavior as adding `postfield` parameters to the URI query string. This differs from merely following an existing `<a href>` link. See [WAP-238 WML, 11 September 2001](https://www.openmobilealliance.org/tech/affiliates/wap/wap-238-wml-20010911-a.pdf), especially the GET form processing rules.

## Read and plan flow

1. The Agent first opens a public WML/WMLC deck with an explicit GET, or uses a previously captured session.
2. The R6 evidence gate verifies HTTP metadata, hashes and original bytes; frozen R5 validates the deck. Only the active card's recorded form structure is eligible.
3. The caller selects the **ordinal position in `form_preview.actions`** and provides explicitly chosen, **non-secret** values, either via local JSON file (`wap-agent form-plan`) or MCP `wap_form_plan`.
4. The planner parses the original captured WML. A WMLC deck is decoded with the pinned, unchanged R5 WBXML decoder before inspection. It compares card/action counts to the verified export.
5. It constructs a candidate URI **in memory only**, validates same-origin and public-domain rules, and returns a sanitized description plus source/target SHA-256 digests. No request is sent.

## Conservative supported subset

- `<go method="get" href="/literal/path.wml">` with a literal destination and **no pre-existing query string, fragment, `$` variables, or embedded URL credentials**.
- One to eight `<postfield name="public_name" value="$(variable)"/>` entries. Form variable names and parameter names are simple ASCII identifiers.
- Each referenced variable must correspond to a plain `text` input without unsupported format masks, or a single-select with unique declared values and no `onpick` behavior. All required variables must be explicitly supplied.
- UTF-8 `application/x-www-form-urlencoded` query encoding (a non-UTF-8 WML document must explicitly declare `accept-charset="utf-8"` on the `go` action); only default ports and HTTP/HTTPS public DNS names; same origin as captured page. Rejects suspicious mutation/authentication paths and sensitive input/parameter names.
- Maximum 128 characters per supplied value, bounded total target length, no control characters, no unknown/unused variables. GET is still **not certified side-effect-free**.

## Deliberately unsupported

- POST or any form submission, login/session/cookie behavior, uploading, credential exchange, WMLScript, WSP/WDP, JavaScript, or automatic follow-up.
- Stateful card events (`onevent`, `timer`, `refresh`, `prev`, `noop`), `<setvar>`, duplicate control names, select `onpick`, duplicate option values, masked inputs and nonliteral/dynamic `href`, unknown variable conversion, interpolation beyond the simple `$(name)` postfield expression, multi-select, arbitrary URL query composition, explicit non-UTF-8 charsets, hidden/password input values, sensitive field names, and redirect handling.
- Any attempt to treat the request digest as approval to execute. A SHA-256 digest of predictable query content can be guessed; it is not anonymity, secrecy, or an authorization token.

## Outputs and safety

Plans expose the public origin, permitted literal path, parameter **names**, their encoded byte count, source body SHA-256, candidate-request SHA-256, and explicit `review_required: true` / `execution_supported: false` flags. The values and the full query-bearing URI are **not** returned or persisted by this feature. Paths containing obvious credential/session strings are rejected.

Standardized return states do not prove that a remote endpoint is safe: an apparently benign GET can mutate server state. This is why v0.6.0 stops at a verifiable proposal; future execution would require a separate, explicit authorization and safety design. Review all website content as untrusted input.

## Usage

```bash
# Only after opening a verified WML/WMLC session that contains a matching GET form.
# Example values-file JSON: {"q":"calligraphy","genre":"puzzle"}
wap-agent form-plan --session ./evidence/session-01 --action 0 --values-file ./my-search-values.json
```

MCP: `wap_form_plan(session_id, action, values)`; this tool is always offline, even when `--allow-network` is enabled.

Tests are in `tests/test_form_plan.py` alongside the original collector, R5 adapter, and MCP safety regression tests.

## Compatibility verification (v0.6.1)

[Compatibility matrix and execution-gate decision](FORM_COMPATIBILITY.md) documents the new offline negative/positive test cases and the conservative decision **not to enable live GET form submission**. The frozen R5 parser remains unchanged.
