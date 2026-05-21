from __future__ import annotations

import argparse
import json
import sys
from pathlib import Path
from urllib.error import URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parents[1]
REQUIRED_FILES = [
    "docs/release/00_operator_release_candidate.md",
    "docs/release/01_install_and_run.md",
    "docs/release/02_operator_walkthrough.md",
    "docs/release/03_safety_boundaries.md",
    "docs/release/04_demo_script.md",
    "docs/release/05_clean_install_vps_validation.md",
    "docs/release/06_release_fix_log.md",
    ".env.example",
]
RELEASE_ENDPOINTS = [
    ("GET", "/v1/release/health"),
    ("GET", "/v1/release/readiness-report"),
    ("POST", "/v1/release/demo-seed"),
    ("POST", "/v1/release/operator-smoke"),
    ("GET", "/v1/release/safety-boundaries"),
    ("GET", "/demo"),
]


def _request(base_url: str, method: str, path: str, timeout: float) -> tuple[bool, str]:
    url = base_url.rstrip("/") + path
    data = b"{}" if method == "POST" else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            body = response.read(4000).decode("utf-8", errors="replace")
            return 200 <= response.status < 300, f"{response.status} {body[:160]}"
    except URLError as exc:
        return False, str(exc)


def check_files() -> list[dict[str, str | bool]]:
    results = []
    for relative in REQUIRED_FILES:
        path = ROOT / relative
        results.append(
            {
                "name": relative,
                "passed": path.exists(),
                "detail": "present" if path.exists() else "missing",
            }
        )
    return results


def check_http(base_url: str, timeout: float) -> list[dict[str, str | bool]]:
    results = []
    for method, path in RELEASE_ENDPOINTS:
        passed, detail = _request(base_url, method, path, timeout)
        results.append({"name": f"{method} {path}", "passed": passed, "detail": detail})
    return results


def main() -> int:
    parser = argparse.ArgumentParser(description="Check ERPGuard release install files and release endpoints.")
    parser.add_argument("--base-url", default=None, help="Running API base URL, for example http://127.0.0.1:8000.")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    checks = check_files()
    if args.base_url:
        checks.extend(check_http(args.base_url, args.timeout))

    passed = sum(1 for check in checks if check["passed"])
    result = {
        "status": "passed" if passed == len(checks) else "failed",
        "checks_passed": passed,
        "checks_total": len(checks),
        "checks": checks,
    }

    if args.json:
        print(json.dumps(result, indent=2))
    else:
        print(f"ERPGuard release install check: {result['status']} ({passed}/{len(checks)})")
        for check in checks:
            marker = "PASS" if check["passed"] else "FAIL"
            print(f"[{marker}] {check['name']}: {check['detail']}")

    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
