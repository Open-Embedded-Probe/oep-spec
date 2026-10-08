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


def test_normative_and_guide_copies_are_japanese_only():
    stale_copies = [
        path.relative_to(ROOT)
        for directory in (ROOT / "docs", ROOT / "interfaces")
        for path in directory.glob("*.md")
        if not path.name.endswith(".ja.md")
    ]
    assert stale_copies == []


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
