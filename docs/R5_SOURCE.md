# Frozen R5 source and R6 integration

The original, full R5 archive is tracked at:

`vendor/r5/WAP_Probe_WAP_Labs_Interop_R5_20261028.zip`

Expected SHA-256:

`cb98d2cc060cfe775a8adf99162160c7651c306a534f3770bbb7c356034b31fa`

This is intentionally **unmodified** so the 2026-10-28 frozen source, binary WMLC fixtures, nested historical test archive, and 139 original test cases remain reproducible. The GitHub Actions job verifies SHA-256 before extracting into ignored `.r5_unpacked/`. Do not edit or silently regenerate the frozen ZIP.

The new `src/wap_probe/r5_adapter.py` directly imports the real R5 parser (`probe/wap_probe.py` / `probe/wap_wbxml.py`), analyzes previously captured bytes, and produces a normalized `r6-r5-export-v1` for R6 bridge. Links with R5's `requires_inputs` flag are excluded from automatic GET candidates.

The tests under `tests/test_r5_adapter.py` run against the actual frozen R5 parser. `tests/test_r5_bridge_integration.py` feeds **synthetic, labeled** HTTP captures through R6 evidence gate, actual R5 parser, then R6 bridge. They are not proof of a live Chinese WML origin, nor native WSP/WDP or physical handset compatibility.

Current design: R6 safely traverses reachable WML `#card` references to plan one same-origin GET. The Agent reader exposes bounded decoded WMLC card text from the frozen R5 parser, with raw-response SHA-256 provenance. R5 is unchanged. No WMLScript, form POST, native WSP/WDP, or physical handset support is implied. Never substitute R5's historical crawler for the no-redirect, pinned-public-IP R6 collector.

Local tests:
```sh
PYTHONPATH=src R5_PROBE_DIR=.r5_unpacked/wap-probe-live-discovery-r5/probe \
python3 -m unittest discover -s tests -v
```
