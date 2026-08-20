from __future__ import annotations

from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup


SOURCE_URL = "https://www.gsmarena.com/news.php3"
OUTPUT_PATH = Path("updates.json")
IMAGE_DIR = Path("mobilemanch-site-1/assets/news")
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
    "AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)


def fetch_gsmarena_updates(limit: int = 10) -> list[dict[str, str]]:
    response = requests.get(
        SOURCE_URL,
        headers={"User-Agent": USER_AGENT, "Accept-Language": "en-US,en;q=0.8"},
        timeout=30,
    )
    response.raise_for_status()

    soup = BeautifulSoup(response.text, "html.parser")
    updates: list[dict[str, str]] = []
    seen_links: set[str] = set()
    news_items = soup.select("div.news-item, article.news-item, .news-item")

    for item in news_items:
        link_tag = next(
            (
                candidate
                for candidate in item.select("a[href]")
                if " ".join(candidate.get_text(" ", strip=True).split())
            ),
            None,
        )
        if not link_tag:
            continue

        title = " ".join(link_tag.get_text(" ", strip=True).split())
        link = urljoin(SOURCE_URL, link_tag["href"])
        if not title or link in seen_links or "gsmarena.com" not in link:
            continue

        image_tag = item.select_one("img[src], img[data-src]")
        image_url = ""
        if image_tag:
            image_url = urljoin(SOURCE_URL, image_tag.get("src") or image_tag.get("data-src") or "")

        updates.append({"title": title, "link": link, "image_url": image_url})
        seen_links.add(link)
        if len(updates) >= limit:
            break

    return updates


def download_image(image_url: str, index: int) -> str:
    if not image_url:
        return ""
    IMAGE_DIR.mkdir(parents=True, exist_ok=True)
    extension = Path(image_url.split("?", 1)[0]).suffix.lower()
    if extension not in {".jpg", ".jpeg", ".png", ".webp", ".gif"}:
        extension = ".jpg"
    filename = f"news-{index:02d}-{hashlib.sha1(image_url.encode()).hexdigest()[:10]}{extension}"
    destination = IMAGE_DIR / filename
    response = requests.get(image_url, headers={"User-Agent": USER_AGENT}, timeout=30)
    response.raise_for_status()
    destination.write_bytes(response.content)
    return destination.as_posix()


def write_updates(updates: list[dict[str, str]]) -> None:
    articles = []
    for index, article in enumerate(updates, start=1):
        local_image = ""
        try:
            local_image = download_image(article["image_url"], index)
        except requests.RequestException as error:
            print(f"Poster download skipped: {error}")
        articles.append(
            {
                "title": article["title"],
                "link": article["link"],
                "image": local_image or article["image_url"],
            }
        )

    payload = {
        "last_updated": datetime.now(timezone.utc).isoformat(),
        "source": SOURCE_URL,
        "articles": articles,
    }
    OUTPUT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=4) + "\n", encoding="utf-8")


def main() -> int:
    try:
        updates = fetch_gsmarena_updates()
        if not updates:
            raise RuntimeError("No news items were found; keeping the existing updates.json.")
        write_updates(updates)
        print(f"Saved {len(updates)} articles and local posters to {OUTPUT_PATH}.")
        return 0
    except (OSError, requests.RequestException, RuntimeError) as error:
        print(f"Update failed: {error}")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
