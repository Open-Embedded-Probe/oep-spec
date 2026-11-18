# OEP v1 review guide

[日本語](review-guide.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

Status: **guide** (not normative). It is the entry point for reviewing the current specification, not a record of past discussions.

## Scope

The normative text is complete with these three:

1. [OEP core](oep-core.md) and [transport](oep-transports.md)
2. Each `.md` referenced from the [standard interfaces](../interfaces/README.md)
3. The [registry](../registry/oep-v1.toml)

Guides, generated files, test vectors and the implementations support and check the normative text, but add no rules. Repository responsibilities follow [responsibilities between repositories](repository-boundaries.md).

A specification review proceeds in this order: the core; the interface common contract that applies to all extensions, and the optional common parts; the contracts specific to the standard OEP interfaces.
After the specification decisions are settled, review the checks based on those clauses, and reflect them in the implementations. Problems found in implementations go back into the specification before the official freeze.
Completion of the specification review, completion of the checks, conformance of implementations and the official freeze are decided separately. For the scope and check conditions of the 3 stages, see [conformance checks](conformance.md).

For the format of definitions when applying this to your own functions, and examples that start from a small function, see the [extension development guide](extension-development-guide.md).

## What to check

- Can independent implementations of probe and host be built from the normative text alone? Are mandatory behaviour, boundary values, results on failure and resource lifetimes unique?
- Do fixed parts, TLVs, ops, enums, timing and limits match the registry?
- Does the behaviour for unknown values, unknown TLVs and unsupported ops not contradict the core's extension rules?
- Is the state unique at each boundary of resending, duplicate execution, ordering, timeout, reconnection and restart?
- Are the owners and release conditions of session, plan, connection, stream and capture segment clear?
- Are the capabilities a probe declares and its state at that moment kept apart?
- Has target-specific knowledge or product-specific constraint crept into the common specification?
- For operations that affect safety or security, is it stated whether they apply partially on failure or are atomic?
- Can large declarations, different sample formats, other wires and so on be added without breaking existing shapes and meanings?
- Are the state, retained amount and tests on the side that adopts an optional function not excessive? Are repackings or new formats for saving bytes not being added?
- Does a guide add obligations the normative text does not have?

## Machine checks

```sh
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

Passing machine checks does not guarantee semantic completeness. For a changed interface, check not only the normal cases but also malformed, unsupported, locked, no_session, no_resource, failed / partial and resending.

## Reflecting review results

Adopted findings are reflected directly in the normative text, registry, vectors and conformance requirements. If the reason for adoption is needed for future compatibility decisions, keep it briefly right after the rule or in [versions and stability](versioning.md). Review reply tables and dated proposals are not added.

## Deciding the freeze

The last check before the freeze is narrowed to the changed contracts and the common rules those contracts depend on.

- Even when stopping, failure, resending and resource release combine, are the answer and the next state unique? Are unsent notifications and partial external effects never mistaken for success?
- For the minimal configuration and for representative configurations that adopt optional functions, can it be implemented with finite retained amounts and processing time? Check the frame limit of declarations and the result limit at execution separately. Implementing optional functions that are not adopted is not required.
- Fix the commits of the specification, registry and vectors to be frozen, and can the remaining specification decisions, the checked scope and the scope not yet checked on the implementation side be told apart? The language switch and the tag follow [versions and stability](versioning.md).

Self-consistency of the vectors alone does not prove implementability or interoperability. Use implementation reviews and execution results of representative configurations as separate evidence, and state the test scope for matters that can only be known on hardware.
If no new contradictions or concrete implementation problems appear, repeating comparisons of unadopted alternatives or across-the-board feature cuts is not made a condition of the freeze.
