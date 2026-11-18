import re
from pathlib import Path


ROOT = Path(__file__).resolve().parents[1]
MARKDOWN_LINK = re.compile(r"\[[^]]+\]\(([^)]+)\)")


def maintained_markdown():
    yield ROOT / "README.ja.md"
    yield ROOT / "README.md"
    yield ROOT / "CONTRIBUTING.ja.md"
    yield ROOT / "CONTRIBUTING.md"
    yield ROOT / "CHANGELOG.md"
    for directory in ("docs", "interfaces", "registry", "generated", "tools", "tests"):
        yield from sorted((ROOT / directory).rglob("*.ja.md"))


PLACEHOLDER = "The English text of this document is not written yet."


def test_every_japanese_document_has_its_english_url():
    """Each X.ja.md has an X.md, so English links can point at a fixed URL before the translation."""
    missing = [path.relative_to(ROOT) for path in maintained_markdown()
               if path.name.endswith(".ja.md") and not path.with_name(path.name[:-6] + ".md").exists()]
    assert missing == []


def test_every_japanese_page_has_its_english_translation():
    """docs/versioning §2: every Japanese document has an English one, maintained together; until the freeze the Japanese
    text is authoritative and the English page says so on its third line, after its title."""
    wrong = []
    for path in sorted(ROOT.rglob("*.ja.md")):
        if any(part.startswith(".") for part in path.relative_to(ROOT).parts):
            continue
        en = path.with_name(path.name[:-6] + ".md")
        if not en.exists():
            wrong.append((path.relative_to(ROOT), "no English page"))
            continue
        lines = en.read_text(encoding="utf-8").splitlines()
        notice = f"[日本語]({path.name}) - until OEP v1.0.0 the Japanese text is authoritative."
        if len(lines) < 4 or not lines[0].startswith("# ") or lines[1] or lines[2] != notice or PLACEHOLDER in "\n".join(lines):
            wrong.append((en.relative_to(ROOT), "not a translation with the notice"))
    assert wrong == []


def test_local_document_links_exist():
    missing = []
    for source in maintained_markdown():
        for raw_target in MARKDOWN_LINK.findall(source.read_text(encoding="utf-8")):
            target = raw_target.split("#", 1)[0]
            if not target or "://" in target or target.startswith("mailto:"):
                continue
            # Type notation such as pos[C](u8) is not a Markdown file link.
            if not target.endswith((".md", ".toml")):
                continue
            if not (source.parent / target).exists():
                missing.append((source.relative_to(ROOT), target))
    assert missing == []


def test_documented_operation_tables_match_registry():
    """Keep op tables distinct from TLV and enum tables when renumbering."""
    import tomllib
    registry = tomllib.loads((ROOT / 'registry/oep-v1.toml').read_text())
    interfaces = {i['name']: i for i in registry['interface']}
    single = {
        'oep-if-plan.ja.md': 'oep.probe.plan',
        'oep-if-restart.ja.md': 'oep.probe.restart',
        'oep-if-link.ja.md': 'oep.probe.link',
        'oep-if-memo.ja.md': 'oep.probe.memo',
        'oep-if-console.ja.md': 'oep.target.console',
    }
    count = 0
    for path in (ROOT / 'interfaces').glob('oep-if-*.ja.md'):
        current = single.get(path.name)
        in_ops = False
        for line in path.read_text().splitlines():
            if line.startswith(('## ', '### ')):
                names = re.findall(r'`(oep\.[a-z0-9.-]+)`', line)
                if names and names[0] in interfaces:
                    current = names[0]
                if path.name == 'oep-if-capture.ja.md' and line.startswith('## 3.'):
                    current = 'oep.fixture.logic'
                if path.name == 'oep-if-capture.ja.md' and line.startswith('## 4.'):
                    current = 'oep.fixture.capture-group'
            if line.startswith('| op |'):
                in_ops = True
            elif not line.startswith('|'):
                in_ops = False
            match = re.match(r'\| (0x[0-9A-Fa-f]+) \| ([a-z_]+) \|', line)
            if in_ops and match:
                assert current, path.name
                interface = 'oep.fixture.analog' if match[2] == 'calibration' else current
                codes = {o['name']: o['code'] for o in interfaces[interface]['op']}
                assert match[2] in codes, (path.name, interface, match[2])
                expected = codes[match[2]]
                assert int(match[1], 16) == expected, (path.name, interface, match[2])
                count += 1
    assert count > 70
