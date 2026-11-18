#!/usr/bin/env python3

import argparse
import concurrent.futures
import html
import json
import sys
from datetime import datetime, timezone
from html.parser import HTMLParser
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.parse import urljoin, urlparse
from urllib.request import Request, urlopen


class LinkParser(HTMLParser):
    def __init__(self, page):
        super().__init__()
        self.page = page
        self.links = []

    def handle_starttag(self, tag, attrs):
        if tag.lower() != "a":
            return
        href = dict(attrs).get("href")
        if href:
            self.links.append((href, html.unescape(self.get_starttag_text())))


def collect_links(docs_dir):
    links = {}
    for page in sorted(docs_dir.glob("*.html")):
        parser = LinkParser(page)
        parser.feed(page.read_text(encoding="utf-8"))
        for href, _ in parser.links:
            if not href.startswith(("http://", "https://")):
                continue
            url = urljoin(page.as_uri(), href)
            parsed = urlparse(url)
            if parsed.hostname not in {"roigoatzzz.netlify.app", "wallsync.pages.dev"}:
                links.setdefault(url, set()).add(page.name)
    return links


def check_url(url, timeout):
    parsed = urlparse(url)
    if parsed.scheme not in {"http", "https"} or not parsed.hostname:
        return "broken", "Invalid URL"

    request = Request(
        url,
        method="GET",
        headers={
            "User-Agent": "WallSync-Link-Checker/1.0",
            "Range": "bytes=0-0",
            "Accept": "*/*",
        },
    )
    try:
        with urlopen(request, timeout=timeout) as response:
            status = response.status
            if status in {404, 410}:
                return "broken", str(status)
            if status in {401, 403, 405, 429}:
                return "uncertain", str(status)
            if 200 <= status < 400:
                return "working", str(status)
            return "uncertain", str(status)
    except HTTPError as error:
        if error.code in {404, 410}:
            return "broken", str(error.code)
        if error.code in {401, 403, 405, 429}:
            return "uncertain", str(error.code)
        return "uncertain", str(error.code)
    except (URLError, TimeoutError, OSError) as error:
        return "uncertain", str(error)


def main():
    parser = argparse.ArgumentParser(description="Check external links used by the WallSync HTML pages.")
    parser.add_argument("--docs", type=Path, default=Path(__file__).resolve().parents[1] / "docs")
    parser.add_argument("--timeout", type=float, default=12)
    parser.add_argument("--workers", type=int, default=8)
    parser.add_argument("--markdown", action="store_true", help="Print a markdown summary.")
    parser.add_argument("--status-json", type=Path, help="Write machine-readable link status to a JSON file.")
    parser.add_argument("--strict", action="store_true", help="Return a failure for broken links.")
    args = parser.parse_args()

    links = collect_links(args.docs)
    results = {"working": [], "broken": [], "uncertain": []}

    with concurrent.futures.ThreadPoolExecutor(max_workers=args.workers) as executor:
        futures = {executor.submit(check_url, url, args.timeout): url for url in links}
        for future in concurrent.futures.as_completed(futures):
            url = futures[future]
            category, detail = future.result()
            results[category].append((url, detail, sorted(links[url])))

    print(f"Checked {len(links)} unique external links.")
    print(f"Working: {len(results['working'])}")
    print(f"Broken: {len(results['broken'])}")
    print(f"Uncertain: {len(results['uncertain'])}")

    for category in ("broken", "uncertain"):
        if not results[category]:
            continue
        print(f"\n{category.upper()}:")
        for url, detail, pages in sorted(results[category]):
            print(f"- {url} [{detail}] ({', '.join(pages)})")

    if args.markdown:
        print("\n## Link check summary")
        print(f"- Working: {len(results['working'])}")
        print(f"- Broken: {len(results['broken'])}")
        print(f"- Uncertain: {len(results['uncertain'])}")
        for category in ("broken", "uncertain"):
            if not results[category]:
                continue
            print(f"\n### {category.title()}")
            for url, detail, pages in sorted(results[category]):
                print(f"- [{url}]({url}) — `{detail}` — {', '.join(pages)}")

    if args.status_json:
        status_data = {
            "checked_at": datetime.now(timezone.utc).isoformat(),
            "summary": {category: len(entries) for category, entries in results.items()},
            "links": {
                url: {
                    "status": category,
                    "detail": detail,
                    "pages": pages,
                }
                for category, entries in results.items()
                for url, detail, pages in entries
            },
        }
        args.status_json.parent.mkdir(parents=True, exist_ok=True)
        args.status_json.write_text(json.dumps(status_data, indent=2) + "\n", encoding="utf-8")

    return 1 if args.strict and results["broken"] else 0


if __name__ == "__main__":
    sys.exit(main())
