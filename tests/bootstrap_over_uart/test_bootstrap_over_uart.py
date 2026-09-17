import re


def test_bootstrap_over_uart(dut):
    match = dut.expect(re.compile(rb"TEST done (\d+)/(\d+)"), timeout=30)
    passed = int(match.group(1))
    total = int(match.group(2))
    assert total > 0
    assert passed == total
