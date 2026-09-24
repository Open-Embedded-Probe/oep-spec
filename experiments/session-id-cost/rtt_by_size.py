"""Round trip of the v0 core ping by payload size: the fixed cost per request and the cost per byte.

The ping echoes its data, so n payload bytes cross the link twice. Reports median / p90 per size and a
least-squares line over the medians (fixed us + us per payload byte, both directions together).

  usage: rtt_by_size.py PORT [REPS]
"""
import json
import statistics
import sys
import time

from oep_client.v0.__main__ import open_client

port = sys.argv[1]
reps = int(sys.argv[2]) if len(sys.argv) > 2 else 50
client = open_client(port, 5.0)
limit = client.limits.max_frame - 16
sizes = [s for s in (0, 4, 8, 16, 32, 60, 64, 128, 256, 480, 900) if s <= limit]

rows = {}
for n in sizes:
    data = bytes(range(256)) * (n // 256 + 1)
    data = data[:n]
    samples = []
    for _ in range(reps):
        t0 = time.perf_counter()
        back = client.ping(data)
        samples.append((time.perf_counter() - t0) * 1e6)
        if back != data:
            raise SystemExit(f"ping of {n} bytes came back different")
    samples.sort()
    rows[n] = {"median_us": round(statistics.median(samples)), "p90_us": round(samples[int(0.9 * len(samples)) - 1])}

xs, ys = list(rows), [rows[n]["median_us"] for n in rows]
mx, my = statistics.mean(xs), statistics.mean(ys)
slope = sum((x - mx) * (y - my) for x, y in zip(xs, ys)) / sum((x - mx) ** 2 for x in xs)
print(json.dumps({"port": port, "limits": client.limits.__dict__, "reps": reps, "by_size": rows,
                  "fit": {"fixed_us": round(my - slope * mx), "us_per_payload_byte": round(slope, 2)}}, indent=1))
