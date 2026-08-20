"""Import public GSMArena phone metadata into the static MobileManch site."""

from __future__ import annotations

import argparse
import html
import json
import re
import sys
import time
from pathlib import Path
from urllib.parse import urljoin, urlparse
from urllib.request import Request, build_opener
from urllib.error import HTTPError, URLError
from urllib.robotparser import RobotFileParser

from bs4 import BeautifulSoup


USER_AGENT = "MobileManch research importer/1.0 (+local static site)"
DEFAULT_SITES = (Path("index.html"), Path("mobilemanch-site-1/index.html"))
REVIEWS_START = "<!-- GSMARENA REVIEWS START -->"
REVIEWS_END = "<!-- GSMARENA REVIEWS END -->"
COMPARE_START = "<!-- GSMARENA COMPARISON START -->"
COMPARE_END = "<!-- GSMARENA COMPARISON END -->"


def validate_url(url: str) -> str:
    parsed = urlparse(url)
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme not in {"http", "https"} or not hostname.endswith("gsmarena.com"):
        raise ValueError("Only a GSMArena URL is accepted.")
    return url


def can_fetch(url: str) -> bool:
    parsed = urlparse(url)
    robots = RobotFileParser(f"{parsed.scheme}://{parsed.netloc}/robots.txt")
    try:
        robots.read()
    except OSError as error:
        print(f"Warning: could not read robots.txt ({error}); continuing cautiously.", file=sys.stderr)
        return True
    return robots.can_fetch(USER_AGENT, url)


def fetch(url: str) -> str:
    request = Request(url, headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"})
    last_error: OSError | None = None
    for attempt in range(3):
        try:
            with build_opener().open(request, timeout=30) as response:
                return response.read().decode("utf-8", errors="replace")
        except (HTTPError, URLError, TimeoutError) as error:
            last_error = error
            if attempt < 2:
                time.sleep(2 ** attempt)
    raise OSError(f"Could not fetch {url} after 3 attempts: {last_error}")


def clean_text(value: str | None) -> str:
    return re.sub(r"\s+", " ", value or "").strip()


def catalog_key(slug: str) -> str:
    return re.sub(r"_5g(?=-\d+\.php$)", "", slug, flags=re.IGNORECASE)


def first_text(soup: BeautifulSoup, selectors: tuple[str, ...]) -> str:
    for selector in selectors:
        element = soup.select_one(selector)
        if element:
            value = clean_text(element.get_text(" ", strip=True))
            if value:
                return value
    return ""


def extract_specs(soup: BeautifulSoup) -> dict[str, dict[str, str]]:
    specs: dict[str, dict[str, str]] = {}
    spec_tables = soup.select("#specs-list table") or soup.select("table")
    for table in spec_tables:
        current_section = "General"
        last_label = ""
        for row in table.select("tr"):
            heading = row.select_one("th[colspan], th[scope='col']")
            if heading:
                current_section = clean_text(heading.get_text(" ", strip=True)) or current_section
                continue
            label_cell = row.select_one(".ttl")
            value_cell = row.select_one(".nfo")
            if label_cell and value_cell:
                label = clean_text(label_cell.get_text(" ", strip=True))
                value = clean_text(value_cell.get_text(" ", strip=True))
                if not value:
                    continue
                if not label:
                    label = last_label
                if label and value:
                    section = specs.setdefault(current_section, {})
                    section[label] = f"{section[label]} | {value}" if label in section else value
                    last_label = label
                continue
            cells = [clean_text(cell.get_text(" ", strip=True)) for cell in row.select("th, td")]
            cells = [cell for cell in cells if cell]
            if len(cells) >= 2:
                specs.setdefault(current_section, {})[cells[0]] = " | ".join(cells[1:])
    return specs


def extract_phone(url: str, page: str) -> dict[str, object]:
    soup = BeautifulSoup(page, "html.parser")
    canonical = soup.select_one('link[rel="canonical"]')
    canonical_url = canonical.get("href", "") if canonical else url
    path = urlparse(canonical_url or url).path.rstrip("/")
    slug = path.split("/")[-1]
    related_links: dict[str, str] = {}
    for link in soup.select("a[href]"):
        label = clean_text(link.get_text(" ", strip=True)).lower()
        href = link.get("href", "")
        if not href:
            continue
        absolute = urljoin(canonical_url or url, href)
        for key, terms in {
            "review_url": ("review",),
            "price_url": ("price",),
            "pictures_url": ("picture",),
            "compare_url": ("compare",),
            "opinions_url": ("opinion", "user reviews"),
        }.items():
            if any(term in label or term in absolute.lower() for term in terms):
                related_links.setdefault(key, absolute)
    image = soup.select_one('meta[property="og:image"]') or soup.select_one(".specs-photo-main img, .specs-photo-main")
    description = soup.select_one('meta[property="og:description"], meta[name="description"]')
    return {
        "slug": slug,
        "name": first_text(soup, ("h1.specs-phone-name-title", "h1")),
        "description": description.get("content", "") if description else "",
        "image_url": (image.get("content") or image.get("src") or "") if image else "",
        "gsmarena_url": canonical_url or url,
        **related_links,
        "specifications": extract_specs(soup),
    }


def find_spec(phone: dict[str, object], labels: tuple[str, ...], fallback: str = "Not listed") -> str:
    specifications = phone["specifications"]
    if not isinstance(specifications, dict):
        return fallback
    for section in specifications.values():
        if isinstance(section, dict):
            for label, value in section.items():
                if any(term in label.lower() for term in labels):
                    return str(value)
    return fallback


def make_card(phone: dict[str, object]) -> str:
    name = html.escape(str(phone.get("name", "Unknown phone")))
    description = html.escape(clean_text(str(phone.get("description", ""))) or "Specifications and availability details from GSMArena.")
    review_url = html.escape(str(phone.get("review_url", "")), quote=True)
    source_url = html.escape(str(phone.get("gsmarena_url", "")), quote=True)
    review_link = f'<a class="review-link" href="{review_url}" target="_blank" rel="noopener">Read Review →</a>' if review_url else ""
    camera = html.escape(find_spec(phone, ("camera", "main camera")))
    battery = html.escape(find_spec(phone, ("battery",)))
    network = html.escape(find_spec(phone, ("network", "technology")))
    detail_url = f"device.html?slug={html.escape(str(phone.get('slug', '')), quote=True)}"
    return f'''            <div class="card gsmarena-card" data-source="{source_url}">
                <div class="card-img" style="background:linear-gradient(135deg,#263d52,#1a2138)">📱</div>
                <div class="card-body">
                    <h3><a href="{detail_url}">{name}</a></h3>
                    <div class="price">Pakistan price: Check local listing</div>
                    <p>{description}</p>
                    <div class="tags"><span class="tag">{camera}</span><span class="tag">{battery}</span><span class="tag">{network}</span></div>
                    {review_link}
                </div>
            </div>'''


def make_row(phone: dict[str, object]) -> str:
    return "                <tr><td>{}</td><td>Check local price</td><td>{}</td><td>{}</td><td>{}</td><td>New</td></tr>".format(
        html.escape(str(phone.get("name", "Unknown phone"))),
        html.escape(find_spec(phone, ("chipset", "platform"))),
        html.escape(find_spec(phone, ("camera", "main camera"))),
        html.escape(find_spec(phone, ("battery",))),
    )


def replace_marked_content(page: str, start: str, end: str, content: str) -> str:
    pattern = re.compile(re.escape(start) + r".*?" + re.escape(end), re.DOTALL)
    replacement = f"{start}\n{content}\n{end}"
    if not pattern.search(page):
        raise ValueError(f"Missing import markers: {start}")
    return pattern.sub(replacement, page, count=1)


def update_site(site: Path, phone: dict[str, object]) -> None:
    page = site.read_text(encoding="utf-8")
    page = replace_marked_content(page, REVIEWS_START, REVIEWS_END, make_card(phone))
    page = replace_marked_content(page, COMPARE_START, COMPARE_END, make_row(phone))
    site.write_text(page, encoding="utf-8")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Import structured GSMArena phone data into MobileManch.")
    parser.add_argument("url", help="A GSMArena phone page URL")
    parser.add_argument("--data", type=Path, default=Path("data/gsmarena_mobiles.json"))
    parser.add_argument("--site", type=Path, action="append", help="Static HTML file to update; may be repeated")
    parser.add_argument("--delay", type=float, default=2.0, help="Seconds to wait before the request")
    parser.add_argument("--ignore-robots", action="store_true", help="Skip robots.txt permission check")
    parser.add_argument("--skip-site-update", action="store_true", help="Only update the device JSON, not homepage cards")
    return parser.parse_args()


def main() -> int:
    args = parse_args()
    try:
        url = validate_url(args.url)
        if not args.ignore_robots and not can_fetch(url):
            raise PermissionError("robots.txt does not allow this URL for the importer user-agent.")
        time.sleep(max(0, args.delay))
        phone = extract_phone(url, fetch(url))
        if not phone["name"]:
            raise ValueError("Could not find a phone name on this page.")

        args.data.parent.mkdir(parents=True, exist_ok=True)
        existing = json.loads(args.data.read_text(encoding="utf-8")) if args.data.exists() else []
        phone_key = catalog_key(str(phone["slug"]))
        existing = [item for item in existing if catalog_key(str(item.get("slug", ""))) != phone_key]
        existing.append(phone)
        args.data.write_text(json.dumps(existing, indent=2, ensure_ascii=False) + "\n", encoding="utf-8")

        if not args.skip_site_update:
            sites = args.site or [path for path in DEFAULT_SITES if path.exists()]
            for site in sites:
                update_site(site, phone)
        print(f"Imported {phone['name']} into {args.data}.")
        return 0
    except (OSError, PermissionError, ValueError, json.JSONDecodeError) as error:
        print(f"Import failed: {error}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())