from __future__ import annotations

import argparse
import json
import sys
from typing import Any
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


CHECKS = [
    ("GET", "/v1/release/health"),
    ("GET", "/v1/release/readiness-report"),
    ("GET", "/v1/release/safety-boundaries"),
    ("GET", "/demo"),
]


def _http_json_or_text(base_url: str, method: str, path: str, timeout: float) -> tuple[bool, int | None, Any]:
    url = base_url.rstrip("/") + path
    data = b"{}" if method == "POST" else None
    request = Request(url, data=data, method=method, headers={"Content-Type": "application/json"})
    try:
        with urlopen(request, timeout=timeout) as response:
            raw = response.read(8000).decode("utf-8", errors="replace")
            try:
                body: Any = json.loads(raw)
            except json.JSONDecodeError:
                body = raw[:240]
            return 200 <= response.status < 300, response.status, body
    except HTTPError as exc:
        raw = exc.read(8000).decode("utf-8", errors="replace")
        return False, exc.code, raw[:240]
    except URLError as exc:
        return False, None, str(exc)


def run_checks(base_url: str, timeout: float, include_smoke: bool) -> dict[str, Any]:
    checks: list[dict[str, Any]] = []
    for method, path in CHECKS:
        passed, status, body = _http_json_or_text(base_url, method, path, timeout)
        checks.append(
            {
                "name": f"{method} {path}",
                "passed": passed,
                "status": status,
                "detail": body,
            }
        )

    if include_smoke:
        passed, status, body = _http_json_or_text(base_url, "POST", "/v1/release/operator-smoke", timeout)
        checks.append(
            {
                "name": "POST /v1/release/operator-smoke",
                "passed": passed,
                "status": status,
                "detail": body,
            }
        )

    boundaries_check = next((check for check in checks if check["name"] == "GET /v1/release/safety-boundaries"), None)
    boundaries = boundaries_check["detail"].get("safety_boundaries", {}) if isinstance(boundaries_check, dict) and isinstance(boundaries_check.get("detail"), dict) else {}
    checks.append(
        {
            "name": "generic_writes_disabled",
            "passed": boundaries.get("ALLOW_GENERIC_REAL_ODOO_WRITES") is False,
            "status": None,
            "detail": "ALLOW_GENERIC_REAL_ODOO_WRITES=false",
        }
    )
    checks.append(
        {
            "name": "r3_r4_writes_disabled",
            "passed": boundaries.get("ALLOW_R3_R4_REAL_WRITES") is False,
            "status": None,
            "detail": "ALLOW_R3_R4_REAL_WRITES=false",
        }
    )

    passed_count = sum(1 for check in checks if check["passed"])
    return {
        "status": "passed" if passed_count == len(checks) else "failed",
        "checks_passed": passed_count,
        "checks_total": len(checks),
        "checks": checks,
    }


def main() -> int:
    parser = argparse.ArgumentParser(description="Run ERPGuard VPS operations check against release endpoints.")
    parser.add_argument("--base-url", default="http://127.0.0.1:8000", help="ERPGuard API base URL.")
    parser.add_argument("--timeout", type=float, default=5.0, help="HTTP timeout in seconds.")
    parser.add_argument("--skip-smoke", action="store_true", help="Skip POST /v1/release/operator-smoke.")
    parser.add_argument("--json", action="store_true", help="Print machine-readable JSON.")
    args = parser.parse_args()

    result = run_checks(args.base_url, args.timeout, include_smoke=not args.skip_smoke)
    if args.json:
        print(json.dumps(result, indent=2, default=str))
    else:
        print(f"ERPGuard operations check: {result['status']} ({result['checks_passed']}/{result['checks_total']})")
        for check in result["checks"]:
            marker = "PASS" if check["passed"] else "FAIL"
            status = f" status={check['status']}" if check["status"] is not None else ""
            print(f"[{marker}] {check['name']}{status}")

    return 0 if result["status"] == "passed" else 1


if __name__ == "__main__":
    sys.exit(main())
