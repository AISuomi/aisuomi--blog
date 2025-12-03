# scripts/generate_news.py
import json
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta, timezone
from pathlib import Path
from textwrap import dedent

import feedparser  # muista: pip install feedparser

ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)
HISTORY_FILE = DATA_DIR / "news_history.json"
MAIN_PAGE = ROOT / "uutisiasuomesta.html"

# Arkistosivut: uutisiasuomesta-2025.html jne
ARCHIVE_TEMPLATE_NAME = "uutisiasuomesta-{year}.html"

# Esimerkkisyötteitä – näitä voi säätää myöhemmin
RSS_FEEDS = [
    ("Yle Uutiset", "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss"),
    ("BBC World", "http://feeds.bbci.co.uk/news/world/rss.xml"),
    ("Reuters World", "http://feeds.reuters.com/reuters/worldNews"),
    ("DW English", "https://rss.dw.com/rdf/rss-en-world"),
    ("The Guardian World", "https://www.theguardian.com/world/rss"),
    # Voit lisätä tänne myöhemmin HS, IS, muiden maiden lehtiä, jne.
]

KEYWORDS = [
    "suomi",
    "finland",
    "finnish",
    "helsinki",
    "lapland",
    "lappi",
    "finns",
  "kurejoki",
  "alajärvi",
]

DAYS_RECENT = 7


@dataclass
class NewsItem:
    title: str
    url: str
    source: str
    published: str  # ISO8601 string


def load_history() -> list[NewsItem]:
    if not HISTORY_FILE.exists():
        return []
    data = json.loads(HISTORY_FILE.read_text(encoding="utf-8"))
    items: list[NewsItem] = []
    for obj in data:
        try:
            items.append(NewsItem(**obj))
        except TypeError:
            continue
    return items


def save_history(items: list[NewsItem]) -> None:
    data = [asdict(i) for i in items]
    HISTORY_FILE.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")


def normalize_text(s: str) -> str:
    return (s or "").lower()


def is_about_finland(title: str, summary: str) -> bool:
    text = normalize_text(title) + " " + normalize_text(summary)
    return any(kw in text for kw in KEYWORDS)


def get_entry_datetime(entry) -> datetime:
    # feedparser normalisoi published_parsed / updated_parsed -kentät
    dt = None
    for attr in ("published_parsed", "updated_parsed"):
        if getattr(entry, attr, None):
            t = getattr(entry, attr)
            dt = datetime(
                year=t.tm_year,
                month=t.tm_mon,
                day=t.tm_mday,
                hour=t.tm_hour,
                minute=t.tm_min,
                second=t.tm_sec,
                tzinfo=timezone.utc,
            )
            break
    if dt is None:
        dt = datetime.now(timezone.utc)
    return dt


def fetch_new_items() -> list[NewsItem]:
    new_items: list[NewsItem] = []
    for source_name, url in RSS_FEEDS:
        feed = feedparser.parse(url)
        for entry in feed.entries:
            title = entry.get("title", "").strip()
            link = entry.get("link", "").strip()
            summary = entry.get("summary", "")
            if not title or not link:
                continue
            if not is_about_finland(title, summary):
                continue
            dt = get_entry_datetime(entry)
            item = NewsItem(
                title=title,
                url=link,
                source=source_name,
                published=dt.isoformat(),
            )
            new_items.append(item)
    return new_items


def merge_items(history: list[NewsItem], fetched: list[NewsItem]) -> list[NewsItem]:
    # Ei duplikaatteja saman URL:n perusteella
    existing_urls = {h.url for h in history}
    merged = history[:]
    for item in fetched:
        if item.url not in existing_urls:
            merged.append(item)
            existing_urls.add(item.url)
    # Järjestys: uusin ensin
    merged.sort(key=lambda i: i.published, reverse=True)
    return merged


def split_recent_and_archive(items: list[NewsItem]):
    now = datetime.now(timezone.utc)
    recent: list[NewsItem] = []
    archive: list[NewsItem] = []
    for item in items:
        try:
            dt = datetime.fromisoformat(item.published)
        except ValueError:
            dt = now
        if now - dt <= timedelta(days=DAYS_RECENT):
            recent.append(item)
        else:
            archive.append(item)
    return recent, archive


def render_recent_list(items: list[NewsItem]) -> str:
    lines = []
    for i in items:
        # Päivä muodossa YYYY-MM-DD
        try:
            d = datetime.fromisoformat(i.published).date().isoformat()
        except ValueError:
            d = ""
        lines.append(
            f'<li><span class="muted">{d}</span> '
            f'<a href="{i.url}" target="_blank" rel="noopener">{i.title}</a> '
            f'<span class="muted">({i.source})</span></li>'
        )
    return "\n          ".join(lines) if lines else '<li class="muted">Ei uutisia viimeisten päivien ajalta.</li>'


def render_archive_links(archive_items: list[NewsItem]) -> tuple[str, dict[int, list[NewsItem]]]:
    # Ryhmittele vuodella
    by_year: dict[int, list[NewsItem]] = {}
    for i in archive_items:
        try:
            year = datetime.fromisoformat(i.published).year
        except ValueError:
            year = datetime.now().year
        by_year.setdefault(year, []).append(i)

    if not by_year:
        return '<li class="muted">Ei arkistoituja uutisia vielä.</li>', {}

    years_sorted = sorted(by_year.keys(), reverse=True)
    lines = []
    for y in years_sorted:
        href = ARCHIVE_TEMPLATE_NAME.format(year=y)
        lines.append(f'<li><a href="/{href}">Uutisia Suomesta {y}</a></li>')
    return "\n          ".join(lines), by_year


def update_main_page(recent_html: str, archives_html: str):
    html = MAIN_PAGE.read_text(encoding="utf-8")

    def replace_block(content: str, start_marker: str, end_marker: str) -> str:
        start = html.find(start_marker)
        end = html.find(end_marker)
        if start == -1 or end == -1 or end < start:
            return html
        before = html[: start + len(start_marker)]
        after = html[end:]
        return before + "\n          " + content + "\n          " + after

    new_html = html
    new_html = replace_block(new_html, "<!-- AI-NEWS-RECENT-START -->", "<!-- AI-NEWS-RECENT-END -->")
    html = new_html
    new_html = replace_block(html, "<!-- AI-NEWS-ARCHIVES-START -->", "<!-- AI-NEWS-ARCHIVES-END -->")

    MAIN_PAGE.write_text(new_html, encoding="utf-8")


def write_archive_pages(by_year: dict[int, list[NewsItem]]):
    for year, items in by_year.items():
        items.sort(key=lambda i: i.published, reverse=True)
        list_lines = []
        for i in items:
            try:
                d = datetime.fromisoformat(i.published).date().isoformat()
            except ValueError:
                d = ""
            list_lines.append(
                f'<li><span class="muted">{d}</span> '
                f'<a href="{i.url}" target="_blank" rel="noopener">{i.title}</a> '
                f'<span class="muted">({i.source})</span></li>'
            )
        list_html = "\n          ".join(list_lines)

        page_html = f"""<!doctype html>
<html lang="fi">
  <head>
    <meta charset="utf-8">
    <title>Uutisia Suomesta {year} – AISuomi-kooste</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/assets/styles.css">
  </head>
  <body>
    <header class="site-header">
      <h1>Uutisia Suomesta {year}</h1>
      <p class="tagline">
        Tämä sivu kokoaa linkkejä ulkopuolisiin uutismedioihin, joissa on mainittu Suomi tai suomalaiset vuonna {year}.
      </p>
    </header>

    <nav class="top-nav">
      <a href="/index.html">Etusivu</a>
      <a href="/uutisiasuomesta.html">Uutisia Suomesta</a>
      <a href="/privacy.html">Tietosuoja</a>
      <a href="/cookies.html">Evästeet</a>
    </nav>

    <main class="layout">
      <section class="main-column">
        <h2>Uutislinkit vuodelta {year}</h2>
        <ul class="post-list">
          {list_html}
        </ul>
      </section>
      <aside class="sidebar">
        <div class="card">
          <h3>Huomio</h3>
          <p class="muted">
            Linkkien takana oleva sisältö on uutismedioiden omaa materiaalia.
            AISuomi kokoaa linkit automaattisesti.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen AI-blogi.
      | <a href="/index.html">Etusivu</a>
      | <a href="/uutisiasuomesta.html">Uutisia Suomesta</a>
    </footer>
  </body>
</html>
"""
        out_path = ROOT / ARCHIVE_TEMPLATE_NAME.format(year=year)
        out_path.write_text(dedent(page_html), encoding="utf-8")


def main():
    history = load_history()
    fetched = fetch_new_items()
    merged = merge_items(history, fetched)
    save_history(merged)

    recent, archive = split_recent_and_archive(merged)
    recent_html = render_recent_list(recent)
    archives_html, by_year = render_archive_links(archive)

    update_main_page(recent_html, archives_html)
    write_archive_pages(by_year)


if __name__ == "__main__":
    main()
