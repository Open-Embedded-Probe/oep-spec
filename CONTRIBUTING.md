# Contributing to the OEP specification

[日本語](CONTRIBUTING.ja.md) - until OEP v1.0.0 the Japanese text is authoritative.

## Where to change

The authoritative OEP specification is the normative documents (`docs/oep-core.ja.md`, `docs/oep-transports.ja.md`, `interfaces/*.ja.md`) and `registry/oep-v1.toml`. The Japanese and English documents are changed together in the same change (until the freeze the Japanese text is authoritative, [versioning](docs/versioning.md) §2). When an implementation's behaviour is adopted as specification, it is written into this repository's normative documents first.

What belongs in this repository and what belongs in the implementations follows [repository boundaries](docs/repository-boundaries.md). Dated proposals, meeting notes, review answers and copies of older specifications are not added. An adopted conclusion goes straight into the normative documents or the guides, with only the reason it needs kept next to it. Rejected ideas and the order of discussion stay in the Git history or in issues.

## Wording changes and rule changes

- A **wording change** does not change what a probe or a host must do. Ambiguities, typos, links, examples and guides may be fixed.
- A **rule change** changes what an implementation must do, a shape on the wire, a registry value, a name or a revision. The pull request states the reason, the effect on compatibility and the implementations that must follow, and implementers review it.

A normative document must be enough on its own to build interoperable implementations. Required branches, boundary values, errors and lifetimes are written out; "usually", "etc." and "implementation-defined" do not leave required behaviour vague. Hardware names, product names, performance measurements and implementation workarounds belong in the implementation repository that owns them.

## The registry and generated files

`oep.` names and numbers on the wire are assigned only when the normative document that defines them and `registry/oep-v1.toml` are updated in the same change. Generated files are not edited by hand; run the following and commit the result.

```sh
python3 tools/oepgen1.py
python3 tools/oepgen1.py --check
python3 tools/oepvectors1.py --check
cd tests && uv run pytest
```

When a rule the vectors cover changes, update them with `python3 tools/oepvectors1.py` before the checks.

A third-party interface uses a reverse-DNS name (for example `io.github.owner.name`) and needs no registration in this registry. Only what uses the `oep.` namespace is reviewed in this repository.

## After the freeze

Compatibility and revisions after the freeze follow [versioning](docs/versioning.md). English is normative and Japanese the translation, both updated in the same change.

Contributions are made under the [MIT License](LICENSE).
