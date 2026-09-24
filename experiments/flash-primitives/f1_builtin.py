"""F1: time the v0 built-in target.flash on a full random image (no reset: random code does not run)."""
import json, sys
from pathlib import Path
from oep_client.v0.__main__ import open_client
from oep_client.v0.flash_image import Target, program_image

client = open_client(sys.argv[1], 10.0)
out = program_image(Target(client), Path(sys.argv[2]).read_bytes(), verify=True, reset=False)
print(json.dumps(out.as_dict(), indent=1))
