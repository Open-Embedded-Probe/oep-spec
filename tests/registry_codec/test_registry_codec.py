"""OEP v0 generated codec: C (via the host sketch) and Python agree with the registry vectors."""

import json
import re
import subprocess
import sys
from pathlib import Path

HERE = Path(__file__).resolve().parent
ROOT = HERE.parent.parent
sys.path.insert(0, str(ROOT / "generated" / "oep-v0-py"))

import oep_v0  # noqa: E402


def _vectors():
    return json.loads((ROOT / "generated" / "oep-v0-vectors.json").read_text(encoding="utf-8"))["vectors"]


def test_generated_is_up_to_date():
    result = subprocess.run(["uv", "run", "tools/oepgen.py", "--check"], cwd=ROOT, capture_output=True, text=True)
    assert result.returncode == 0, result.stdout + result.stderr


def test_python_codec_matches_vectors():
    for vec in _vectors():
        data = bytes.fromhex(vec["bytes"])
        if vec["kind"] in ("header", "header_reject"):
            cls = oep_v0.HEADER_CLASSES[vec["role"]]
        else:
            cls = oep_v0.PAYLOAD_CLASSES[(vec["definition"], vec["operation"], vec["direction"])]
        if vec["kind"].endswith("reject"):
            try:
                cls.unpack(data)
            except ValueError:
                continue
            raise AssertionError(f"{vec['name']}: expected rejection")
        value = cls.unpack(data)
        assert value.pack() == data, vec["name"]
        for name, expected in vec["fields"].items():
            actual = getattr(value, name)
            if isinstance(actual, list):  # array of structs
                assert [item.__dict__ for item in actual] == expected, vec["name"]
            elif isinstance(actual, (bytes, bytearray)):
                assert actual == bytes(expected), vec["name"]
            else:
                assert actual == expected, vec["name"]


def test_c_codec_matches_vectors(dut):
    match = dut.expect(re.compile(rb"TEST done (\d+)/(\d+)"), timeout=60)
    passed, total = int(match.group(1)), int(match.group(2))
    assert total > 0
    assert passed == total
