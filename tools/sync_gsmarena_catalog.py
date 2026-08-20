"""Synchronize public GSMArena phone specifications into the MobileManch catalog."""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import parse_qs, urljoin, urlparse
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup

from import_gsmarena import USER_AGENT, catalog_key, extract_phone, fetch

BASE_URL = "https://www.gsmarena.com/"
MAKERS_URL = urljoin(BASE_URL, "makers.php3")
PHONE_PATTERN = re.compile(r"^[a-z0-9_]+-\d+\.php$", re.IGNORECASE)


class RobotsPolicy:
    def __init__(self, ignore: bool = False) -> None:
        self.ignore = ignore
        self.parsers: dict[str, RobotFileParser] = {}

    def allowed(self, url: str) -> bool:
        if self.ignore:
            return True
        parsed = urlparse(url)
        origin = f"{parsed.scheme}://{parsed.netloc}"
        parser = self.parsers.get(origin)
        if parser is None:
            parser = RobotFileParser(f"{origin}/robots.txt")
            try:
                parser.read()
            except OSError as error:
                print(f"Warning: robots.txt unavailable ({error}); skipping {url}", file=sys.stderr)
                return False
            self.parsers[origin] = parser
        return parser.can_fetch(USER_AGENT, url)


def clean_url(url: str, base: str) -> str:
    absolute = urljoin(base, url)
    parsed = urlparse(absolute)
    return absolute if parsed.hostname and parsed.hostname.endswith("gsmarena.com") else ""


def is_phone_url(url: str) -> bool:
    return bool(PHONE_PATTERN.fullmatch(urlparse(url).path.rstrip("/").split("/")[-1]))


def is_next_list_page(url: str, current: str) -> bool:
    if urlparse(url).netloc != urlparse(current).netloc:
        return False
    query = parse_qs(urlparse(url).query)
    return "page" in query or bool(re.search(r"page\d+", urlparse(url).path, re.IGNORECASE))


def discover_makers(policy: RobotsPolicy) -> list[str]:
    if not policy.allowed(MAKERS_URL):
        raise PermissionError(f"robots.txt does not allow {MAKERS_URL}")
    soup = BeautifulSoup(fetch(MAKERS_URL), "html.parser")
    urls = {clean_url(link.get("href", ""), MAKERS_URL) for link in soup.select("a[href*='-phones-']")}
    return sorted(url for url in urls if url)


def discover_phones(
    makers: list[str],
    policy: RobotsPolicy,
    delay: float,
    max_list_pages: int,
    max_phones: int,
) -> list[str]:
    phone_urls: set[str] = set()
    for maker_index, maker_url in enumerate(makers, start=1):
        pending = [maker_url]
        visited: set[str] = set()
        while pending and (not max_list_pages or len(visited) < max_list_pages):
            list_url = pending.pop(0)
            if list_url in visited or not policy.allowed(list_url):
                continue
            visited.add(list_url)
            try:
                page = fetch(list_url)
            except OSError as error:
                print(f"List skipped: {list_url} ({error})", file=sys.stderr)
                continue
            soup = BeautifulSoup(page, "html.parser")
            for link in soup.select("a[href]"):
                candidate = clean_url(link.get("href", ""), list_url)
                if candidate and is_phone_url(candidate):
                    phone_urls.add(candidate)
                    if max_phones and len(phone_urls) >= max_phones:
                        return sorted(phone_urls)
                elif candidate and is_next_list_page(candidate, list_url) and candidate not in visited:
                    pending.append(candidate)
            if delay:
                time.sleep(delay)
        print(f"Discovered {len(phone_urls)} phones after maker {maker_index}/{len(makers)}: {maker_url}")
    return sorted(phone_urls)


def load_catalog(path: Path) -> list[dict[str, object]]:
    if not path.exists():
        return []
    payload = json.loads(path.read_text(encoding="utf-8"))
    if not isinstance(payload, list):
        raise ValueError(f"Expected a list in {path}")
    return [item for item in payload if isinstance(item, dict) and item.get("slug")]


def save_catalog(path: Path, records: list[dict[str, object]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    records.sort(key=lambda item: str(item.get("name", "")).lower())
    path.write_text(json.dumps(records, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")


def sync_catalog(args: argparse.Namespace) -> tuple[int, int, int]:
    policy = RobotsPolicy(args.ignore_robots)
    makers = discover_makers(policy)
    if args.max_makers:
        makers = makers[: args.max_makers]
    phone_urls = discover_phones(makers, policy, args.delay, args.max_list_pages, args.max_phones)
    catalog = load_catalog(args.data)
    by_slug = {catalog_key(str(item["slug"])): item for item in catalog}
    imported = 0
    skipped = 0

    for index, url in enumerate(phone_urls, start=1):
        if not policy.allowed(url):
            skipped += 1
            continue
        try:
            if args.delay:
                time.sleep(args.delay)
            phone = extract_phone(url, fetch(url))
            if not phone.get("name") or not phone.get("slug"):
                skipped += 1
                continue
            by_slug[catalog_key(str(phone["slug"]))] = phone
            imported += 1
            print(f"Imported {index}/{len(phone_urls)}: {phone['name']}")
        except (OSError, ValueError) as error:
            skipped += 1
            print(f"Phone skipped: {url} ({error})", file=sys.stderr)

    save_catalog(args.data, list(by_slug.values()))
    return len(makers), imported, skipped


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Sync public GSMArena phone specifications into MobileManch.")
    parser.add_argument("--data", type=Path, default=Path("data/gsmarena_mobiles.json"))
    parser.add_argument("--delay", type=float, default=1.0, help="Seconds between requests.")
    parser.add_argument("--max-makers", type=int, default=0, help="Maximum maker lists; 0 means all discovered makers.")
    parser.add_argument("--max-list-pages", type=int, default=3, help="Maximum pages per maker; 0 means no limit.")
    parser.add_argument("--max-phones", type=int, default=500, help="Maximum phone pages; 0 means no limit.")
    parser.add_argument("--ignore-robots", action="store_true", help="Skip robots.txt checks only when explicitly permitted.")
    return parser.parse_args()


def main() -> int:
    try:
        args = parse_args()
        makers, imported, skipped = sync_catalog(args)
        print(f"Catalog sync complete: {makers} makers, {imported} imported, {skipped} skipped.")
        return 0
    except (OSError, PermissionError, ValueError, json.JSONDecodeError) as error:
        print(f"Catalog sync failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.path.insert(0, str(Path(__file__).resolve().parent))
    raise SystemExit(main())
