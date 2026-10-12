"""Independent fixed layouts followed by a valid unknown TLV, including empty fixed layouts."""
import json
from pathlib import Path
import struct

import pytest

CASES = json.loads((Path(__file__).parent / 'core_extensions.json').read_text())['cases']


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
    assert tail(ans[5 + fixed:]) == [(127, b'x')]
    if ans[3] == 1 and case['operation'] == 'open':
        assert struct.unpack_from('<II', ans, 5) == (3000, 0x12345678)
    if ans[3] == 1 and case['operation'] == 'clock':
        assert struct.unpack_from('<IQ', ans, 5) == (0x12345678, 100)
    with pytest.raises(AssertionError):
        tail(ans[5 + fixed:-1])
