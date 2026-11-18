# OEP responsibilities between repositories

[日本語](repository-boundaries.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). These are the storage rules that keep the sources of truth for the specification and for implementations from mixing.

## Responsibilities

| Repository | What it holds as authoritative | What it does not hold |
|---|---|---|
| `oep-spec` | Normative protocol text, standard interfaces, the registry of wire numbers, generated files, shared test vectors, conformance requirements, compatibility policy | Implementation code, platform-specific values, how to use products, hardware test results, investigation logs, applied proposals |
| `oep-probe-arduino` | The Arduino probe implementation, supported boards and profiles, pin, memory and timing constraints, firmware build, unit tests and releases, the terms of use of the project VID:PID | The OEP normative text itself, the specifications of hosts and of applications that use OEP |
| `oep-client-python` | The Python host library and CLI, the virtual bench, target-specific processing, integration tests on hardware and their results, compatibility of the Python API | The OEP normative text itself, the implementation conditions of probe firmware |
| `oep-client-js` | The JavaScript host library, connection handling for browser / Node, the JS API and its tests | The OEP normative text itself, the design of clients in other languages |
| `wireskein` | Applications for acquisition, analysis and recording, the WireSkein file format, capture workflows that use OEP | The normative text of the OEP capture interface |
| `wireskein-web` | The WireSkein browser UI and web library | The source of truth for OEP and the WireSkein file format |
| `pytest-embedded-wireskein` | Integration with pytest, how test runs are saved and compared | The specifications of OEP, probes and WireSkein |

Other consumers follow the same principle: how they use OEP goes in their own repository, and only common contracts go in `oep-spec`.

## Flow of changes

1. If an interoperability contract needs to change, change the normative text, registry and vectors of `oep-spec` first.
2. Make conformance tests from the clauses of the specification, and settle the contracts in the order core → common interface parts → OEP-interface-specific. A checker does not make expected values from the current behaviour of an implementation.
3. Each implementation follows once the contract is settled, stating the commit or tag of the specification it follows.
4. If a constraint found in an implementation does not change a common contract, record it only in that implementation's documents.
5. Only when it has become mandatory behaviour common to several implementations, bring it back to `oep-spec` as a rule without product names or measurement history.

## When to keep reasons

Keep a reason only when the rule alone does not show the boundary of the choice, and a future change would bring the same problem back. The reason directly explains the choice adopted now; it does not list compared alternatives, dates, people or commits.

Undecided matters are not mixed into normative documents. They are managed in issues, and only the final form is reflected in the documents after the decision. Proposals before they are applied and review replies after they are applied are not kept in the current tree. The Git history remains for audit.
