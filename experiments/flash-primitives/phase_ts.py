"""Run a command, timestamp its ndjson progress lines, print first/last line of each phase."""
import json, subprocess, sys, time
t0 = time.perf_counter()
p = subprocess.Popen(sys.argv[1:], stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, bufsize=1)
seen = {}
for line in p.stdout:
    t = time.perf_counter() - t0
    try:
        d = json.loads(line)
    except ValueError:
        print(f"{t:6.3f} {line.rstrip()}"); continue
    key = d.get("phase") or d.get("name") or d.get("ev")
    first = seen.setdefault(key, [t, t, line.strip()])
    first[1] = t; first[2] = line.strip()
p.wait()
for k, (a, b, last) in seen.items():
    print(f"phase {k:10} {a:6.3f} .. {b:6.3f}  ({b - a:.3f} s)  last: {last[:90]}")
print(f"total {time.perf_counter() - t0:.3f} s, rc {p.returncode}")
