import json
from datetime import datetime, timedelta
from pathlib import Path

import feedparser

ROOT = Path(__file__).resolve().parents[1]
NEWS_PAGE = ROOT / "uutisiasuomesta.html"
DATA_DIR = ROOT / "data"
HISTORY_FILE = DATA_DIR / "news_history.json"

# RSS-lähteet (voit lisätä/poistaa halutessasi)
FEEDS = [
    ("Yle Uutiset", "https://feeds.yle.fi/uutiset/v1/recent.rss?publisherIds=YLE_UUTISET"),
    ("BBC World", "https://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters World", "https://www.reutersagency.com/feed/?best-topics=world&post_type=best"),
    ("DW World", "https://rss.dw.com/rdf/rss-en-world"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
]

KEYWORDS = [
    "suomi", "finland", "finnish", "finns", "kurejoki", "alajärvi", "eteläpohjanmaa", 
    "helsinki", "lapland", "lappi",
]

TODAY = datetime.utcnow().date()


def load_history():
    if HISTORY_FILE.exists():
        with HISTORY_FILE.open("r", encoding="utf-8") as f:
            return json.load(f)
    return {"items": []}


def save_history(history):
    DATA_DIR.mkdir(exist_ok=True)
    with HISTORY_FILE.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def normalize_date(entry):
    # Yritetään lukea julkaisupäivä, fallback: tämänpäiväinen
    for key in ("published_parsed", "updated_parsed"):
        value = entry.get(key)
        if value:
            try:
                return datetime(*value[:6]).date()
            except Exception:
                pass
    return TODAY


def is_finnish_related(title, summary):
    text = f"{title} {summary}".lower()
    return any(word in text for word in KEYWORDS)


def collect_news():
    history = load_history()
    known_links = {item["link"] for item in history["items"]}

    for source_name, url in FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            summary = entry.get("summary", "")
            link = entry.get("link", "").strip()
            if not title or not link:
                continue

            if not is_finnish_related(title, summary):
                continue

            if link in known_links:
                continue

            pub_date = normalize_date(entry)
            history["items"].append(
                {
                    "title": title,
                    "link": link,
                    "source": source_name,
                    "published": pub_date.isoformat(),
                }
            )
            known_links.add(link)

    # Pidetään historia kohtuullisena (esim. viimeiset 365 päivää)
    one_year_ago = TODAY - timedelta(days=365)
    history["items"] = [
        item
        for item in history["items"]
        if datetime.fromisoformat(item["published"]).date() >= one_year_ago
    ]

    save_history(history)
    return history


def build_recent_html(items):
    """Rakentaa <li>…</li>-rivit viimeisen 7 päivän uutisista."""
    seven_days_ago = TODAY - timedelta(days=7)

    recent = [
        item
        for item in items
        if datetime.fromisoformat(item["published"]).date() >= seven_days_ago
    ]

    if not recent:
        return '  <li class="muted">Ei uutisia viimeisten 7 päivän ajalta.</li>\n'

    # Uusimmat ensin
    recent.sort(key=lambda x: x["published"], reverse=True)

    lines = []
    for item in recent:
        date_str = datetime.fromisoformat(item["published"]).date().strftime("%d.%m.%Y")
        line = (
            f'  <li>'
            f'<a href="{item["link"]}" target="_blank" rel="noopener">'
            f'{item["title"]}</a> '
            f'<span class="muted">({item["source"]}, {date_str})</span>'
            f'</li>'
        )
        lines.append(line)
    return "\n".join(lines) + "\n"


def build_archives_html(items):
    """Rakentaa listan vuosilinkeistä arkistoille (jos haluat tehdä erilliset sivut)."""
    if not items:
        return '  <li class="muted">Arkistoja ei vielä ole.</li>\n'

    years = sorted({datetime.fromisoformat(i["published"]).year for i in items})
    lines = []
    for y in years:
        # Varsinaiset arkistosivut voi tehdä myöhemmin; linkit valmiina.
        lines.append(
            f'  <li><a href="/uutisiasuomesta-{y}.html">Vuosi {y}</a></li>'
        )
    return "\n".join(lines) + "\n"


def replace_between_markers(text, start_marker, end_marker, inner_html):
    start_idx = text.index(start_marker) + len(start_marker)
    end_idx = text.index(end_marker)
    return text[:start_idx] + "\n" + inner_html + text[end_idx:]


def update_news_page(history):
    html = NEWS_PAGE.read_text(encoding="utf-8")

    recent_html = build_recent_html(history["items"])
    archives_html = build_archives_html(history["items"])

    html = replace_between_markers(
        html,
        "<!-- AI-NEWS-RECENT-START -->",
        "<!-- AI-NEWS-RECENT-END -->",
        recent_html,
    )

    html = replace_between_markers(
        html,
        "<!-- AI-NEWS-ARCHIVES-START -->",
        "<!-- AI-NEWS-ARCHIVES-END -->",
        archives_html,
    )

    NEWS_PAGE.write_text(html, encoding="utf-8")


def main():
    history = collect_news()
    update_news_page(history)


if __name__ == "__main__":
    main()
