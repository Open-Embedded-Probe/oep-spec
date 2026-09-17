import re


def test_uart_sequence_characterization(dut):
    dut.expect("CHARACTERIZATION ordered delivery=2", timeout=30)
    dut.expect("CHARACTERIZATION reordered delivery=3", timeout=10)
    match = dut.expect(re.compile(rb"TEST done (\d+)/(\d+)"), timeout=10)
    assert int(match.group(1)) == int(match.group(2))
