import re


def test_uart_framing_comparison(dut):
    dut.expect("COMPARISON explicit-max=39 derived-max=37", timeout=30)
    dut.expect("COMPARISON bootstrap-roundtrip explicit=52 derived=44", timeout=10)
    match = dut.expect(re.compile(rb"TEST done (\d+)/(\d+)"), timeout=10)
    assert int(match.group(1)) == int(match.group(2))
