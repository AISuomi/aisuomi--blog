from pathlib import Path
from datetime import datetime, timedelta
import json
import html

import feedparser  # asennettu workflowissa


ROOT = Path(__file__).resolve().parents[1]
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

NEWS_HISTORY_PATH = DATA_DIR / "news_history.json"
NEWS_INDEX_PAGE = ROOT / "uutisiasuomesta.html"

# Voit vaihtaa/antaa lisää syötteitä myöhemmin
SOURCES = [
    {
        "name": "Yle News (EN)",
        "lang": "en",
        "url": "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_NEWS_ENGLISH.rss",
    },
    {
        "name": "Yle Uutiset (FI)",
        "lang": "fi",
        "url": "https://feeds.yle.fi/uutiset/v1/majorHeadlines/YLE_UUTISET.rss",
    },
    {
        "name": "Reuters World News",
        "lang": "en",
        "url": "https://feeds.reuters.com/reuters/worldNews",
    },
]


# --- Historia-tiedosto ----------------------------------------------------


def load_history() -> dict:
    """Lataa news_history.json ja normalisoi sen muotoon {'items': [...]}."""
    if not NEWS_HISTORY_PATH.exists():
        return {"items": []}

    try:
        with NEWS_HISTORY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Jos tiedosto on rikki → aloita puhtaalta pöydältä
        return {"items": []}

    # Vanha formaatti: lista → kääri dictin sisään
    if isinstance(data, list):
        return {"items": data}

    if not isinstance(data, dict):
        return {"items": []}

    items = data.get("items")
    if not isinstance(items, list):
        data["items"] = []
    return data


def save_history(history: dict) -> None:
    with NEWS_HISTORY_PATH.open("w", encoding="utf-8") as f:
        json.dump(history, f, ensure_ascii=False, indent=2)


def iso_date_from_entry(entry) -> str:
    """Palauta YYYY-MM-DD, käytetään published/updated -ajasta tai tämän päivän päivää."""
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6]).date().isoformat()
            except Exception:
                pass
    return datetime.utcnow().date().isoformat()


# --- Uutisten keruu --------------------------------------------------------


def collect_news() -> dict:
    history = load_history()

    known_links = {
        item.get("link")
        for item in history["items"]
        if isinstance(item, dict) and item.get("link")
    }

    new_items = []

    for src in SOURCES:
        feed = feedparser.parse(src["url"])
        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "")

            if not title or not link:
                continue

            text = f"{title} {summary}".lower()
            # Poimi vain jutut joissa mainitaan Suomi / Finland
            if "finland" not in text and "suomi" not in text and "finnish" not in text:
                continue

            if link in known_links:
                continue

            item = {
                "title": title,
                "link": link,
                "source": src["name"],
                "lang": src["lang"],
                "published": iso_date_from_entry(entry),
            }
            new_items.append(item)
            known_links.add(link)

    if new_items:
        history["items"].extend(new_items)
        # Uusimmat ensin
        history["items"].sort(key=lambda x: x.get("published", ""), reverse=True)
        # Pidetään historia hillittynä
        history["items"] = history["items"][:1000]

    return history


# --- HTML-pätkien rakentaminen --------------------------------------------


def build_recent_html(history: dict) -> str:
    """Uusimmat 7 päivän uutiset <li>-elementteinä."""
    cutoff = datetime.utcnow().date() - timedelta(days=7)
    rows = []

    for item in history["items"]:
        try:
            d = datetime.strptime(item.get("published", "1970-01-01"), "%Y-%m-%d").date()
        except Exception:
            continue

        if d < cutoff:
            continue

        title = html.escape(item.get("title", "").strip())
        link = html.escape(item.get("link", "").strip())
        source = html.escape(item.get("source", ""))
        lang = html.escape(item.get("lang", "").upper())

        rows.append(
            f'  <li><a href="{link}" target="_blank" rel="noopener">'
            f"{title} – {source} ({lang})</a></li>"
        )

    if not rows:
        return '  <li class="muted">Ei Suomiaiheisia uutisia viimeisen 7 päivän ajalta.</li>'

    return "\n".join(rows)


def build_archive_pages_and_index_list(history: dict) -> str:
    """Luo uutisiasuomesta-YYYY.html -sivut ja palauttaa index-sivun arkistolistan."""

    # Ryhmitellään vuoden mukaan
    by_year: dict[str, list[dict]] = {}
    for item in history["items"]:
        published = item.get("published", "")
        if len(published) < 4:
            continue
        year = published[:4]
        by_year.setdefault(year, []).append(item)

    index_items = []

    for year, items in sorted(by_year.items(), reverse=True):
        page_name = f"uutisiasuomesta-{year}.html"
        page_path = ROOT / page_name

        li_rows = []
        for it in items:
            title = html.escape(it.get("title", "").strip())
            link = html.escape(it.get("link", "").strip())
            source = html.escape(it.get("source", ""))
            lang = html.escape(it.get("lang", "").upper())
            date = html.escape(it.get("published", ""))
            li_rows.append(
                f'        <li><a href="{link}" target="_blank" rel="noopener">'
                f"{date}: {title} – {source} ({lang})</a></li>"
            )

        if not li_rows:
            year_list = '        <li class="muted">Ei uutisia tälle vuodelle.</li>'
        else:
            year_list = "\n".join(li_rows)

        page_html = f"""<!doctype html>
<html lang="fi">
  <head>
    <meta charset="utf-8">
    <title>Uutisia Suomesta – {year}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/assets/styles.css">
  </head>
  <body>
    <header class="site-header">
      <h1>Uutisia Suomesta – {year}</h1>
      <p class="tagline">
        Vuoden {year} aikana eri kielissä julkaistuja uutisia, joissa mainitaan Suomi tai suomalaiset.
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
        <h2>Uutisia Suomesta {year}</h2>
        <ul class="post-list">
{year_list}
        </ul>
      </section>

      <aside class="sidebar">
        <div class="card">
          <h3>Huomio</h3>
          <p class="muted">
            Uutiset ovat ulkopuolisten toimijoiden tuottamia. AISuomi ei
            edusta tai suodata toimituksellisia näkemyksiä, vaan kokoaa
            linkkejä automaattisesti.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen AI-blogi.
      | <a href="/index.html">Etusivu</a>
      | <a href="/uutisiasuomesta.html">Uutisia Suomesta</a>
      | <a href="/privacy.html">Tietosuoja</a>
      | <a href="/cookies.html">Evästeet</a>
    </footer>
  </body>
</html>
"""
        page_path.write_text(page_html, encoding="utf-8")

        index_items.append(
            f'  <li><a href="/uutisiasuomesta-{year}.html">'
            f"Vuoden {year} uutiskooste ({len(items)} linkkiä)</a></li>"
        )

    if not index_items:
        return '  <li class="muted">Arkistoja ei vielä ole.</li>'

    return "\n".join(index_items)


def patch_between_markers(html_text: str, start_marker: str, end_marker: str, new_block: str) -> str:
    """Korvaa kahden kommenttimerkin välin."""
    start = html_text.find(start_marker)
    end = html_text.find(end_marker)
    if start == -1 or end == -1 or end < start:
        return html_text
    start_end = start + len(start_marker)
    return html_text[:start_end] + "\n" + new_block + "\n" + html_text[end:]


def update_index_page(history: dict) -> None:
    html_text = NEWS_INDEX_PAGE.read_text(encoding="utf-8")

    recent_block = build_recent_html(history)
    archive_block = build_archive_pages_and_index_list(history)

    html_text = patch_between_markers(
        html_text,
        "<!-- AI-NEWS-RECENT-START -->",
        "<!-- AI-NEWS-RECENT-END -->",
        recent_block,
    )
    html_text = patch_between_markers(
        html_text,
        "<!-- AI-NEWS-ARCHIVES-START -->",
        "<!-- AI-NEWS-ARCHIVES-END -->",
        archive_block,
    )

    NEWS_INDEX_PAGE.write_text(html_text, encoding="utf-8")


def main() -> None:
    history = collect_news()
    save_history(history)
    update_index_page(history)


if __name__ == "__main__":
    main()
