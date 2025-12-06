from pathlib import Path
from datetime import datetime, timedelta
import json
import html

import feedparser  # asennettu workflowissa


# Projektin juuripolku
ROOT = Path(__file__).resolve().parents[1]

# Data-hakemisto uutishistorialle
DATA_DIR = ROOT / "data"
DATA_DIR.mkdir(exist_ok=True)

NEWS_HISTORY_PATH = DATA_DIR / "news_history.json"
NEWS_INDEX_PAGE = ROOT / "uutisiasuomesta.html"

# ---------------------------------------------------------------------------
# AVAINSANAT: MITÄ ETSITÄÄN OTSIKOISTA / TIIVISTELMISTÄ
# ---------------------------------------------------------------------------

KEYWORDS = [
    # Suomi yleisesti
  "finland",
    "finnish",
    "finns",
    "suomi",
    "suomalainen",
    "suomalaiset",

    # Paikat

    "helsinki",
    "lapland",
    "lappi",
    "kurejoki",
    "alajärvi",
    "alajarvi",
    "etelä-pohjanmaa",
    "etelapohjanmaa",
    "south ostrobothnia",
]

# ---------------------------------------------------------------------------
# RSS-LÄHTEET – VAIN ULKOMAISET MEDIAT
# (on tarkoituksella rajattu lähteisiin, jotka ovat tyypillisesti
#  hyvin muodostettua RSS:ää / RDF:ää, eivätkä aiheuta XML-virheitä)
# ---------------------------------------------------------------------------

SOURCES = [
    # EUROOPPA
    {
        "name": "DW World",
        "lang": "en",
        "url": "https://rss.dw.com/rdf/rss-en-world",
    },
    {
        "name": "DW Europe",
        "lang": "en",
        "url": "https://rss.dw.com/rdf/rss-en-europe",
    },
    {
        "name": "Euronews World",
        "lang": "en",
        "url": "https://www.euronews.com/rss?level=theme&name=news",
    },
    {
        "name": "Euronews Europe",
        "lang": "en",
        "url": "https://www.euronews.com/rss?level=theme&name=europe",
    },
    {
        "name": "BBC World",
        "lang": "en",
        "url": "http://feeds.bbci.co.uk/news/world/rss.xml",
    },
    {
        "name": "BBC Europe",
        "lang": "en",
        "url": "http://feeds.bbci.co.uk/news/world/europe/rss.xml",
    },
    {
        "name": "Politico Europe",
        "lang": "en",
        "url": "https://www.politico.eu/feed/",
    },
    {
        "name": "EUobserver",
        "lang": "en",
        "url": "https://euobserver.com/rss",
    },

    # POHJOIS-AMERIKKA
    {
        "name": "NYT World",
        "lang": "en",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    },
    {
        "name": "Washington Post World",
        "lang": "en",
        "url": "http://feeds.washingtonpost.com/rss/world",
    },

    # AASIA / OSEANIA
    {
        "name": "Japan Times",
        "lang": "en",
        "url": "https://www.japantimes.co.jp/feed/",
    },
    {
        "name": "SCMP World",
        "lang": "en",
        "url": "https://www.scmp.com/rss/91/feed",
    },
    {
        "name": "ABC Australia World",
        "lang": "en",
        "url": "https://www.abc.net.au/news/feed/51120/rss.xml",
    },

    # LÄHI-ITÄ
    {
        "name": "Al Jazeera – All News",
        "lang": "en",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
    },

    # ETELÄ-AMERIKKA
    {
        "name": "MercoPress",
        "lang": "en",
        "url": "https://en.mercopress.com/rss",
    },
]


# ---------------------------------------------------------------------------
# HISTORIA-TIEDOSTO
# ---------------------------------------------------------------------------


def load_history() -> dict:
    """
    Lataa news_history.json ja normalisoi sen muotoon {'items': [...]}.
    Vanha formaatti (pelkkä lista) kääritään dictin sisään.
    """
    if not NEWS_HISTORY_PATH.exists():
        return {"items": []}

    try:
        with NEWS_HISTORY_PATH.open("r", encoding="utf-8") as f:
            data = json.load(f)
    except Exception:
        # Jos tiedosto on rikki → aloita alusta
        return {"items": []}

    # Jos sisältö on lista, kääritään se dictin sisään
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
    """
    Palauttaa päivämäärän muodossa YYYY-MM-DD.
    Yrittää käyttää published_parsed / updated_parsed -kenttiä.
    """
    for attr in ("published_parsed", "updated_parsed"):
        t = getattr(entry, attr, None)
        if t:
            try:
                return datetime(*t[:6]).date().isoformat()
            except Exception:
                pass
    return datetime.utcnow().date().isoformat()


# ---------------------------------------------------------------------------
# UUTISTEN KERUU
# ---------------------------------------------------------------------------


def collect_news() -> dict:
    """
    Hakee uutisia kaikista SOURCES-lähteistä,
    suodattaa vain jutut joissa esiintyy jokin KEYWORDS-avainsanoista,
    ja palauttaa päivitetyn history-dictin.
    """
    history = load_history()

    known_links = {
        item.get("link")
        for item in history["items"]
        if isinstance(item, dict) and item.get("link")
    }

    new_items = []

    for src in SOURCES:
        url = src["url"]
        name = src["name"]
        print(f"Haetaan uutisia lähteestä: {name} ({url})")

        # Suojataan yksittäisen lähteen kaatuminen
        try:
            feed = feedparser.parse(url)
        except Exception as e:
            print(f"VAROITUS: Lähteen '{name}' haku epäonnistui: {e}")
            continue

        # Jos parsinta epäonnistui tai ei ole entries-listaa
        if not getattr(feed, "entries", None):
            bozo = getattr(feed, "bozo", False)
            bozo_exc = getattr(feed, "bozo_exception", None)
            print(
                f"VAROITUS: Lähteen '{name}' syöte tyhjä tai virheellinen "
                f"(bozo={bozo}, exc={bozo_exc})"
            )
            continue

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "")

            if not title or not link:
                continue

            text = f"{title} {summary}".lower()

            # Poimi vain jutut, joissa mainitaan jokin avainsanoista
            if not any(word in text for word in KEYWORDS):
                continue

            if link in known_links:
                continue

            item = {
                "title": title,
                "link": link,
                "source": name,
                "lang": src.get("lang", "en"),
                "published": iso_date_from_entry(entry),
            }
            new_items.append(item)
            known_links.add(link)

    if new_items:
        history["items"].extend(new_items)
        # Uusimmat ensin
        history["items"].sort(
            key=lambda x: x.get("published", "1970-01-01"), reverse=True
        )
        # Pidetään historia hillittynä
        history["items"] = history["items"][:1000]

    return history


# ---------------------------------------------------------------------------
# HTML-RAKENTAMINEN
# ---------------------------------------------------------------------------


def build_recent_html(history: dict) -> str:
    """
    Rakentaa uusimmat 7 päivän uutiset <li>-elementteinä.
    """
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
        date = html.escape(item.get("published", ""))

        rows.append(
            f'  <li><a href="{link}" target="_blank" rel="noopener">'
            f"{date}: {title} – {source} ({lang})</a></li>"
        )

    if not rows:
        return '  <li class="muted">Ei Suomiaiheisia uutisia viimeisen 7 päivän ajalta.</li>'

    return "\n".join(rows)


def build_archive_pages_and_index_list(history: dict) -> str:
    """
    Luo uutisiasuomesta-YYYY.html -sivut ja palauttaa
    index-sivulle tulevan arkistolistan <li>-elementit.
    """

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
        Vuoden {year} aikana ulkomaisissa medioissa julkaistuja uutisia, joissa mainitaan Suomi, Finland tai suomalaiset.
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


# ---------------------------------------------------------------------------
# INDEX-SIVUN PÄIVITYS
# ---------------------------------------------------------------------------


def patch_between_markers(html_text: str, start_marker: str, end_marker: str, new_block: str) -> str:
    """
    Korvaa kahden kommenttimerkin välin.
    Jos markkereita ei löydy, palauttaa alkuperäisen tekstin.
    """
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


# ---------------------------------------------------------------------------
# MAIN
# ---------------------------------------------------------------------------


def main() -> None:
    history = collect_news()
    save_history(history)
    update_index_page(history)


if __name__ == "__main__":
    main()
