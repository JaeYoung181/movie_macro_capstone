"""
Local demo macro for the Movie Macro capstone project.

Run this only against your own local development server. It signs in as a demo
user, submits the schedule step several times very quickly, and prints whether
the anti-macro rules blocked the requests.
"""

import argparse
import re
import time
from http.cookiejar import CookieJar
from urllib.parse import urlencode
from urllib.request import HTTPCookieProcessor, Request, build_opener
from urllib.error import HTTPError


DEMO_USER = "demo_macro"
DEMO_PASSWORD = "demo1234"


def request(opener, url, data=None):
    body = None
    headers = {}

    if data is not None:
        body = urlencode(data).encode("utf-8")
        headers["Content-Type"] = "application/x-www-form-urlencoded"

    req = Request(url, data=body, headers=headers)

    try:
        with opener.open(req, timeout=10) as response:
            return response.getcode(), response.read().decode("utf-8", errors="replace")
    except HTTPError as exc:
        return exc.code, exc.read().decode("utf-8", errors="replace")


def extract_macro_token(html):
    match = re.search(r'name="macro_token"\s+value="([^"]+)"', html)
    if not match:
        raise RuntimeError("macro_token을 찾지 못했습니다. 로그인 상태나 페이지를 확인하세요.")
    return match.group(1)


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--base-url", default="http://localhost:5555")
    parser.add_argument("--count", type=int, default=8)
    args = parser.parse_args()

    base_url = args.base_url.rstrip("/")
    opener = build_opener(HTTPCookieProcessor(CookieJar()))

    request(opener, f"{base_url}/register", {
        "userid": DEMO_USER,
        "password": DEMO_PASSWORD,
        "password2": DEMO_PASSWORD,
    })

    request(opener, f"{base_url}/login", {
        "userid": DEMO_USER,
        "password": DEMO_PASSWORD,
    })

    print(f"Local macro demo target: {base_url}")
    print("Sending schedule submissions quickly...\n")

    for index in range(1, args.count + 1):
        _, page = request(opener, f"{base_url}/reserve/mandalorian")
        token = extract_macro_token(page)

        status, html = request(opener, f"{base_url}/reserve/mandalorian", {
            "date": "2026-05-08",
            "time": "13:00",
            "macro_token": token,
            "company_name": "bot",
        })

        blocked = (
            "너무 빠른 제출" in html
            or "너무 많은 요청" in html
            or "자동화된 요청" in html
        )
        result = "BLOCKED" if blocked else "PASSED"
        print(f"{index:02d}. HTTP {status} - {result}")

        time.sleep(0.15)

    print("\n/logs 화면에서 '일정 선택 반복 요청' 또는 '차단' 상태를 확인하세요.")


if __name__ == "__main__":
    main()
