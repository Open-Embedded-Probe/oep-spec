"""Independent fixed layouts followed by a valid unknown TLV, including empty fixed layouts."""
import json
from pathlib import Path
import struct

import pytest

DATA = json.loads((Path(__file__).parent / 'core_extensions.json').read_text())
CASES = DATA['cases']
REQUEST_CASES = DATA['request_cases']


def tail(data):
    rows = []
    while data:
        assert len(data) >= 3
        tag, size = struct.unpack_from('<BH', data)
        assert 1 <= tag <= 127 and len(data) >= 3 + size
        rows.append((tag, data[3:3 + size]))
        data = data[3 + size:]
    return rows


@pytest.mark.parametrize('case', CASES, ids=lambda case: case['name'])
def test_empty_and_nonempty_result_layouts_allow_response_tlvs(case):
    req, ans = bytes.fromhex(case['request_hex']), bytes.fromhex(case['answer_hex'])
    assert req[0] == 1 and ans[0] == 2
    assert req[1:3] == ans[1:3] and req[3:5] == b'\0\0'
    fixed = 0 if ans[3] == 0 else {'open': 8, 'keepalive': 0, 'end': 0, 'clock': 12}[case['operation']]
    assert fixed == case['fixed_answer_bytes']
    assert tail(ans[5 + fixed:]) == [(127, bytes([15]) + b'io.example.note' + b'x')]   # a named extension (core §2.2)
    if ans[3] == 1 and case['operation'] == 'open':
        assert struct.unpack_from('<II', ans, 5) == (3000, 0x12345678)
    if ans[3] == 1 and case['operation'] == 'clock':
        assert struct.unpack_from('<IQ', ans, 5) == (0x12345678, 100)
    with pytest.raises(AssertionError):
        tail(ans[5 + fixed:-1])


@pytest.mark.parametrize('case', REQUEST_CASES, ids=lambda case: case['name'])
def test_a_named_extension_in_a_request(case):
    """core §2.2: an unknown name is ignored, or refused unsupported naming the tag as received when critical; a name_len
    past the value is malformed, critical or not."""
    req, ans = bytes.fromhex(case['request_hex']), bytes.fromhex(case['answer_hex'])
    assert req[1:3] == ans[1:3] and req[3:5] == b'\0\0' and req[6:10] == b'\0\0\0\0'   # fn 0, session 0 (clock)
    ((tag, value),) = tail(req[10:]) if req[10] & 0x80 == 0 else [(req[10] & 0x7F, req[13:])]
    assert tag == 127
    broken = value[0] + 1 > len(value)
    if broken:
        assert ans[3:5] == b'\0\3' and len(ans) == 5                                        # rejected malformed
    elif req[10] & 0x80:
        assert ans[3:5] == b'\0\x0b' and ans[5:] == bytes([req[10]])                        # unsupported, 0xFF
    else:
        assert ans[3:5] == b'\1\0' and struct.unpack_from('<IQ', ans, 5) == (0x12345678, 100)
