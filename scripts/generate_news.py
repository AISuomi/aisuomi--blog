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

# ---------------------------------------------------------------------------
# Lähdelista: ulkomaiset uutismediat, jotka voivat mainita Suomen
# (voit lisätä tänne myöhemmin uusia helposti)
# ---------------------------------------------------------------------------

SOURCES = [
    # Yle poistettu – idea on seurata, mitä MUU maailma Suomesta kirjoittaa

    # Kansainväliset isot englanninkieliset
    {
        "name": "Reuters World News",
        "lang": "en",
        "url": "https://feeds.reuters.com/reuters/worldNews",
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
        "name": "The Guardian World",
        "lang": "en",
        "url": "https://www.theguardian.com/world/rss",
    },
    {
        "name": "The Guardian Europe",
        "lang": "en",
        "url": "https://www.theguardian.com/world/europe-news/rss",
    },
    {
        "name": "DW News (DE→EN feed)",
        "lang": "en",
        "url": "https://rss.dw.com/rdf/rss-en-all",
    },
    {
        "name": "Euronews",
        "lang": "en",
        "url": "https://www.euronews.com/rss?level=theme&name=news",
    },
    {
        "name": "Politico Europe",
        "lang": "en",
        "url": "https://www.politico.eu/feed/",
    },
    {
        "name": "France24 World (EN)",
        "lang": "en",
        "url": "https://www.france24.com/en/rss",
    },
    {
        "name": "EUobserver",
        "lang": "en",
        "url": "https://euobserver.com/rss",
    },
    {
        "name": "CNN World",
        "lang": "en",
        "url": "http://rss.cnn.com/rss/edition_world.rss",
    },
    {
        "name": "CNN Europe",
        "lang": "en",
        "url": "http://rss.cnn.com/rss/edition_europe.rss",
    },
    {
        "name": "New York Times World",
        "lang": "en",
        "url": "https://rss.nytimes.com/services/xml/rss/nyt/World.xml",
    },
    {
        "name": "Washington Post World",
        "lang": "en",
        "url": "http://feeds.washingtonpost.com/rss/world",
    },

    # Pohjoismaat, Eurooppa (kansalliskieliä)
    {
        "name": "SVT Nyheter (SE)",
        "lang": "sv",
        "url": "https://www.svt.se/nyheter/rss.xml",
    },
    {
        "name": "NRK Nyheter (NO)",
        "lang": "no",
        "url": "https://www.nrk.no/toppsaker.rss",
    },
    {
        "name": "DR Nyheder (DK)",
        "lang": "da",
        "url": "https://www.dr.dk/nyheder/service/feeds/allenyheder",
    },
    {
        "name": "NOS Nieuws (NL)",
        "lang": "nl",
        "url": "https://feeds.nos.nl/nosnieuwsalgemeen",
    },

    # Ranska, Saksa, Espanja – pyytämäsi
    {
        "name": "Le Monde (FR)",
        "lang": "fr",
        "url": "https://www.lemonde.fr/rss/une.xml",
    },
    {
        "name": "El País Internacional (ES)",
        "lang": "es",
        "url": "https://feeds.elpais.com/mrss-s/pages/ep/site/elpais.com/section/internacional",
    },
    {
        "name": "Der Spiegel International Section (DE→EN)",
        "lang": "en",
        "url": "https://www.spiegel.de/international/index.rss",
    },

    # Italia, Portugali
    {
        "name": "La Repubblica Mondo (IT)",
        "lang": "it",
        "url": "https://www.repubblica.it/rss/mondo/rss2.0.xml",
    },
    {
        "name": "Público Mundo (PT)",
        "lang": "pt",
        "url": "https://www.publico.pt/rss/mundo",
    },

    # Kanada, Australia
    {
        "name": "ABC Australia World",
        "lang": "en",
        "url": "https://www.abc.net.au/news/feed/51120/rss.xml",
    },

    # Aasia
    {
        "name": "Japan Times",
        "lang": "en",
        "url": "https://www.japantimes.co.jp/feed/",
    },
    # Etelä-Korea, Intia jne. voidaan lisätä myöhemmin

    # Kiinan suunnalta neutraalein: Hongkongin SCMP
    {
        "name": "South China Morning Post (HK, EN)",
        "lang": "en",
        "url": "https://www.scmp.com/rss/91/feed",
    },

    # Lähi-itä & Afrikka
    {
        "name": "Al Jazeera – All News",
        "lang": "en",
        "url": "https://www.aljazeera.com/xml/rss/all.xml",
    },
    {
        "name": "MercoPress (South Atlantic / LatAm)",
        "lang": "en",
        "url": "https://en.mercopress.com/rss",
    },
]

# ---------------------------------------------------------------------------
# Hakusanat: mikä tulkitaan Suomi-aiheiseksi?
# ---------------------------------------------------------------------------

# Maatason sanat: “Suomi” eri kielillä
KEYWORDS_COUNTRY = [
    "finland",
    "finnish",
    "suomi",
    "finlande",    # ranska
    "finlandia",   # espanja, italia, puola ym.
    "finnland",    # saksa
    "finlândia",   # portugali
    "finlandiya",  # turkki ym.
    "финляндия",   # venäjä
    "芬兰",        # kiina
]

# Paikalliset / alueelliset sanat
KEYWORDS_LOCAL = [
    "kurejoki",
    "alajärvi",
    "eteläpohjanmaa",
    "etelä-pohjanmaa",
    "lappi",
    "lapland",
    "saame",
    "helsinki",  # usein merkki Suomesta, vaikka sana “Finland” ei olisi mukana
]

ALL_KEYWORDS = KEYWORDS_COUNTRY + KEYWORDS_LOCAL


# ---------------------------------------------------------------------------
# Historia-tiedosto
# ---------------------------------------------------------------------------

def load_history() -> dict:
    """Lataa news_history.json ja normalisoi muotoon {'items': [...]}."""
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


# ---------------------------------------------------------------------------
# Uutisten keruu
# ---------------------------------------------------------------------------

def collect_news() -> dict:
    history = load_history()

    known_links = {
        item.get("link")
        for item in history["items"]
        if isinstance(item, dict) and item.get("link")
    }

    new_items: list[dict] = []

    for src in SOURCES:
        print(f"Haetaan uutisia lähteestä: {src['name']} ({src['url']})")

        try:
            feed = feedparser.parse(src["url"])
        except Exception as e:
            print(f"VAROITUS: Lähteen '{src['name']}' haku epäonnistui: {e}")
            continue

        if getattr(feed, "bozo", 0):
            print(
                f"VAROITUS: Lähteen '{src['name']}' syöte voi olla ongelmallinen "
                f"(bozo={feed.bozo}, exc={getattr(feed, 'bozo_exception', None)})"
            )

        for entry in feed.entries:
            title = getattr(entry, "title", "").strip()
            link = getattr(entry, "link", "").strip()
            summary = getattr(entry, "summary", "")

            if not title or not link:
                continue

            text = f"{title} {summary}".lower()

            # Poimi vain jutut joissa esiintyy jokin ALL_KEYWORDS -listasta
            if not any(kw in text for kw in ALL_KEYWORDS):
                continue

            if link in known_links:
                continue

            item = {
                "title": title,
                "link": link,
                "source": src["name"],
                "lang": src["lang"],
                "published": iso_date_from_entry(entry),
                # Talteen myös hakuteksti (otsikko + summary) luokittelua varten
                "text": text,
            }

            new_items.append(item)
            known_links.add(link)

    if new_items:
        history["items"].extend(new_items)
        history["items"].sort(key=lambda x: x.get("published", ""), reverse=True)
        # pidetään historia maltillisena
        history["items"] = history["items"][:2000]

    return history


# ---------------------------------------------------------------------------
# HTML-pätkien rakentaminen
# ---------------------------------------------------------------------------

def build_recent_html(history: dict) -> str:
    """Uusimmat 7 päivän uutiset <li>-elementteinä.

    Jaetaan kahteen ryhmään:
    - 'keskeiset' = otsikko/summary sisältää jonkin KEYWORDS_COUNTRY-sanan
    - 'muut' = sisältää vain paikallisia sanoja (KEYWORDS_LOCAL),
      mutta ei KEYWORDS_COUNTRY-sanoja.
    """
    cutoff = datetime.utcnow().date() - timedelta(days=7)

    primary_rows: list[str] = []   # keskeiset Suomi-maininnat
    other_rows: list[str] = []     # muut paikalliset/alueelliset maininnat

    for item in history["items"]:
        try:
            d = datetime.strptime(item.get("published", "1970-01-01"), "%Y-%m-%d").date()
        except Exception:
            continue

        if d < cutoff:
            continue

        title_raw = item.get("title", "").strip()
        link_raw = item.get("link", "").strip()
        source_raw = item.get("source", "")
        lang_raw = item.get("lang", "").upper()

        title = html.escape(title_raw)
        link = html.escape(link_raw)
        source = html.escape(source_raw)
        lang = html.escape(lang_raw)

        # Käytä ensisijaisesti talteen otettua tekstikenttää,
        # mutta toimi myös vanhan datan kanssa.
        stored_text = item.get("text")
        if isinstance(stored_text, str) and stored_text:
            text_lower = stored_text
        else:
            text_lower = f"{title_raw} {source_raw}".lower()

        has_country = any(kw in text_lower for kw in KEYWORDS_COUNTRY)
        has_local = any(kw in text_lower for kw in KEYWORDS_LOCAL)

        line = (
            f'  <li><a href="{link}" target="_blank" rel="noopener">'
            f"{title} – {source} ({lang})</a></li>"
        )

        if has_country:
            primary_rows.append(line)
        elif has_local:
            other_rows.append(line)
        else:
            # varalta, jos ALL_KEYWORDS-match tuli vain summaryssa
            other_rows.append(line)

    if not primary_rows and not other_rows:
        return '  <li class="muted">Ei Suomi-aiheisia uutisia viimeisen 7 päivän ajalta.</li>'

    rows: list[str] = []

    if primary_rows:
        rows.append('  <li class="section-title"><strong>Keskeiset Suomi-maininnat</strong></li>')
        rows.extend(primary_rows)

    if other_rows:
        if primary_rows:
            rows.append('  <li class="section-title"><strong>Muut Suomi-aiheiset maininnat</strong></li>')
        else:
            rows.append('  <li class="section-title"><strong>Suomi-aiheiset maininnat</strong></li>')
        rows.extend(other_rows)

    return "\n".join(rows)


def build_archive_pages_and_index_list(history: dict) -> str:
    """Luo uutisiasuomesta-YYYY.html -sivut ja palauttaa index-sivun arkistolistan."""

    by_year: dict[str, list[dict]] = {}
    for item in history["items"]:
        published = item.get("published", "")
        if len(published) < 4:
            continue
        year = published[:4]
        by_year.setdefault(year, []).append(item)

    index_items: list[str] = []

    for year, items in sorted(by_year.items(), reverse=True):
        page_name = f"uutisiasuomesta-{year}.html"
        page_path = ROOT / page_name

        li_rows: list[str] = []
        # Voisi halutessa sortata myös tässä päivämäärän mukaan
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
    if not NEWS_INDEX_PAGE.exists():
        print(f"VAROITUS: Index-sivua ei löytynyt: {NEWS_INDEX_PAGE}")
        return

    try:
        html_text = NEWS_INDEX_PAGE.read_text(encoding="utf-8")
    except Exception as e:
        print(f"VAROITUS: Index-sivun lukeminen epäonnistui: {e}")
        return

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
