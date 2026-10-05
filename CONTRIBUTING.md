# Contributing to the OEP specification

[日本語](CONTRIBUTING.ja.md)

## Where the specification lives

This repository is the source of truth for OEP. The specification is the normative text in `docs/` (`oep-core.md`,
`oep-if-*.md`, `target-console-dmseq.md`) and the number registry `registry/oep-v1.toml`. Implementations follow it; they do
not define it. What an implementation must do to conform, and how to check it, is listed in [conformance](docs/conformance.md).

A change to the specification is made in one of two ways: the maintainers edit this repository directly, or anyone opens a
pull request to it. Errors can be reported as an issue or fixed in a pull request.

The English text is normative and the Japanese text is a translation. A change edits both languages in the same commit. Where
they differ, the English wins and the Japanese is corrected.

## Two kinds of change

- **Wording change**: what a probe or host does stays the same. Clearer sentences, typos, translation fixes, comments,
  examples, links and status lines. Wording changes may go in directly.
- **Rule change**: what an implementation must do changes, or any value in the registry changes (op, tag, enum, timing,
  limit, name, revision). The pull request states the rule, the reason, and which implementations must follow, and is
  reviewed by implementers before it is merged. Implementations are changed after the specification.

Normative text must be implementable from the text alone: numbers are values, not guidelines, and every branch of a
procedure is written. Chip, board and product names, measurements, dates and anecdotes go to record documents, which the
normative text may link to.

## Adding an `oep.` name or a registry value

`oep.` names and every number in the registry are assigned only by merging a pull request that changes
`registry/oep-v1.toml` and the text that defines the new name or value, together. In that pull request:

1. edit `registry/oep-v1.toml` and the normative text (both languages);
2. run `python3 tools/oepgen1.py`, then `python3 tools/oepgen1.py --check`, and commit `generated/`;
3. run `python3 tools/oepvectors1.py --check` (when a rule a vector covers changes, run `python3 tools/oepvectors1.py` and commit `tests/vectors/`);
4. run `cd tests && uv run pytest registry_v1 vectors`.

Until it is merged, try the idea under your own reverse-DNS name, or with the experimental op range 0xF0 to 0xFF
(core §2.5), which shipping probes do not use.

## Third-party interfaces

An interface that is not part of the standard uses a reverse-DNS name (for example `io.github.<owner>.<name>`,
core §13). It needs no registration and no pull request here: its own definition assigns its ops, tags and values.

## Errata after the freeze

After the v1 freeze, errata go through the same pull-request process. An erratum that only fixes wording is a wording
change; one that changes behaviour is a rule change and follows the revision rules of core §2.7.

## License

Contributions are made under the [MIT License](LICENSE) of this repository.
