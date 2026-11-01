# Third-party sources and scope

The project MIT license applies only to material the owner has authority to license. It does not grant rights to external websites, standards or third-party code. The root LICENSE must be read together with these scope exclusions and retained upstream notices.

## Lowband / WAP Labs fixtures

`tests/fixtures/lowband_wml13_reference.json` and `lowband_wsp_reference.json` derive from pinned reference material in `dills122/wap-labs`, commit `9cd7ab97dc6752fc1616feb3505a58603f6a45df`. Preserve [the complete upstream MIT copyright and license](tests/fixtures/LOWBAND_LICENSE.txt), copyright 2026 Dylan Steele. Do not replace that attribution with the project copyright.

## WML/WBXML standards and kXML reference

The R5 WBXML parser identifies WML specifications and Android kXML `Wml.java` as token-table references. Its implementation remains the original Python parser; referencing protocol-assigned numbers is not a claim that the project owns the standard or the upstream implementation.

- WML specification reference: https://www.wapforum.org/what/technical/spec-wml-19990616.pdf
- Android kXML WML token-table reference: https://android.googlesource.com/platform/dalvik.git/+/f6c387128427e121477c1b32ad35cdcaa5101ba3/libcore/xml/src/main/java/org/kxml2/wap/wml/Wml.java
- Full retained kXML reference notice: [KXML_REFERENCE_LICENSE.txt](tests/fixtures/KXML_REFERENCE_LICENSE.txt)
- kXML2 license reference: https://github.com/kobjects/kxml2/blob/master/license.txt

`official_wml12_spec_example.wmlc` is a specification reference vector, not an external live website capture or a claim of project ownership over the specification. Preserve its provenance. Any upstream protected implementation expression found during source review must retain the applicable original copyright and license; this notice does not substitute for it.

## Private historical material

The original full R5 ZIP and captured third-party WML/HTML/XHTML responses are excluded from the sanitized source distribution. Public accessibility of a website is not a redistribution grant. The project's MIT grant does not cover these privately preserved bodies.

## Historical compatibility comparisons

References to WaveNav, WAP Labs/Lowband, kXML or gateways describe research and comparison sources. They do not imply endorsement, complete compatibility, physical-device validation, or inclusion of those projects' implementations in this repository.
