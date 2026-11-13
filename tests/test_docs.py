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


def test_english_pages_are_placeholders_until_the_freeze():
    """Until OEP v1 is frozen the Japanese text is the only maintained one (docs/versioning): an English page holds a
    title, a link to its Japanese version and the placeholder sentence, never a translation that could go stale."""
    wrong = []
    for directory in ("docs", "interfaces", "registry", "generated", "tools", "tests"):
        for path in sorted((ROOT / directory).rglob("*.md")):
            if path.name.endswith(".ja.md") or any(part.startswith(".") for part in path.relative_to(ROOT).parts):
                continue
            text = path.read_text(encoding="utf-8")
            ja = path.name[:-3] + ".ja.md"
            if PLACEHOLDER not in text or f"]({ja})" not in text or len(text.splitlines()) > 6:
                wrong.append(path.relative_to(ROOT))
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
