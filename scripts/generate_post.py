import os
import json
from datetime import datetime, date
from pathlib import Path
from textwrap import dedent
import base64

import requests

API_KEY = os.environ["OPENAI_API_KEY"]
API_URL = "https://api.openai.com/v1/chat/completions"

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_FILE = ROOT / "index.html"
IMAGES_DIR = ROOT / "assets" / "images"
IMAGE_CATEGORIES = {"talous", "ruoka", "yhteiskunta", "teema"}

TALOUS_INDEX_FILE = ROOT / "talous.html"
RUOKA_INDEX_FILE = ROOT / "ruoka.html"
YHTEISKUNTA_INDEX_FILE = ROOT / "yhteiskunta.html"
TEEMA_INDEX_FILE = ROOT / "teema.html"

TODAY = datetime.utcnow().date()


def make_filename(kind: str) -> Path:
    """Kaikki aktiiviset kategoriat tallennetaan posts/kind/YYYY-MM-DD-kind.html."""
    return POSTS_DIR / kind / f"{TODAY.isoformat()}-{kind}.html"


def post_exists(path: Path) -> bool:
    return path.exists()


def call_openai(system_prompt: str, user_prompt: str) -> str:
    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-4.1-mini",
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        "temperature": 0.55,
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error: {resp.status_code} {resp.text}")

    data = resp.json()
    try:
        return data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(f"Unexpected response format: {json.dumps(data)[:500]}") from e


def _extract_title_from_document(doc_html: str) -> str:
    start = doc_html.find("<title>")
    end = doc_html.find("</title>")
    if start != -1 and end != -1:
        return doc_html[start + 7:end].strip()
    start = doc_html.find("<h1>")
    end = doc_html.find("</h1>")
    if start != -1 and end != -1:
        return doc_html[start + 4:end].strip()
    return "AISuomi – artikkeli"


def get_recent_titles(limit: int = 40) -> list[str]:
    """Kerää uusimpien juttujen otsikoita, jotta AI ei kierrätä samoja aiheita."""
    posts: list[tuple[datetime, str]] = []
    if not POSTS_DIR.exists():
        return []

    for p in POSTS_DIR.rglob("*.html"):
        try:
            d = datetime.strptime(p.name[:10], "%Y-%m-%d")
        except ValueError:
            continue
        try:
            title = _extract_title_from_document(p.read_text(encoding="utf-8", errors="ignore"))
        except Exception:
            continue
        if title:
            posts.append((d, title))

    posts.sort(key=lambda item: item[0], reverse=True)
    return [title for _, title in posts[:limit]]


def generate_article(kind: str) -> str:
    """AISuomi 2.0: konkreettista talous-, yhteiskunta- ja arki-analyysiä."""
    recent_titles = get_recent_titles(limit=40)
    recent_titles_text = "\n".join(f"- {title}" for title in recent_titles) or "- Ei aiempia otsikoita käytettävissä."

    system_prompt = """
Olet AISuomi.blogin autonominen suomalainen AI-toimitus.

Tehtäväsi ei ole tuottaa yleistä täytesisältöä, runoutta tai samojen teemojen kierrätystä.
Tehtäväsi on kirjoittaa selkeitä, konkreettisia ja suomalaiselle lukijalle hyödyllisiä artikkeleita.

Säännöt:
- Kirjoita vain sujuvaa suomea.
- Älä kirjoita runollisesti.
- Älä kirjoita satuja, unenomaisia kuvauksia tai yleistä tunnelmointia.
- Älä käytä tyhjiä AI-fraaseja kuten "muuttuvassa maailmassa", "moniäänisyys", "identiteetin kerrostumat" tai "hiljaisuuden tanssi".
- Älä kirjoita yleistä artikkelia digitalisaatiosta ilman konkreettista näkökulmaa.
- Älä lupaa tarkkoja faktoja, lukuja tai uutistietoja, jos niitä ei ole annettu promptissa.
- Käytä tarvittaessa varovaista muotoilua: "voi tarkoittaa", "saattaa näkyä", "yksi mahdollinen seuraus".
- Vastauksesi on pelkkää HTML-leipätekstiä ilman <html>, <head> tai <body> -tageja.
""".strip()

    if kind == "talous":
        topic_hint = """
Kirjoita suomalaisesta arjen taloudesta tai Suomen talouden ilmiöstä.

Valitse yksi konkreettinen näkökulma, esimerkiksi:
- asumisen kustannukset
- korkojen vaikutus kotitalouksiin
- ruoan hinta
- energian hinta
- yrittäjän arki
- pienten yritysten kustannuspaineet
- työn tekemisen kannattavuus
- verotus arjen näkökulmasta
- väestön ikääntymisen talousvaikutukset
- tekoälyn vaikutus työhön ja yrityksiin
- maaseudun ja kaupunkien taloudellinen ero

Älä kirjoita otsikkoa, joka alkaa sanoilla "Digitalisaation vaikutus", "Tulevaisuuden työ" tai "Arkitalous".
"""
    elif kind == "yhteiskunta":
        topic_hint = """
Kirjoita suomalaisesta yhteiskunnasta tavallisen ihmisen näkökulmasta.

Valitse yksi konkreettinen näkökulma, esimerkiksi:
- julkiset palvelut
- terveydenhuollon arki
- koulutus
- liikenne
- asuminen
- ikääntyminen
- maaseudun palvelut
- kaupunkien kasvu
- turvallisuuden tunne
- työelämän muutos
- byrokratia
- luottamus viranomaisiin
- median ja tiedon rooli

Älä kirjoita identiteetistä, suomalaisuuden rajasta, moniäänisyydestä tai kulttuurisesta kuuluvuudesta.
"""
    elif kind == "ruoka":
        topic_hint = """
Kirjoita ruoasta käytännöllisesti ja suomalaisen arjen kautta.

Valitse yksi konkreettinen näkökulma:
- edullinen arkiruoka
- sesonkiruoka
- kotimaiset raaka-aineet
- hävikin vähentäminen
- ruoan hinnan vaikutus valintoihin
- helppo kotiruoka
- ruokakulttuurin muutos

Älä kirjoita pelkkää tunnelmointia ruoasta. Anna käytännön esimerkkejä.
"""
    elif kind == "teema":
        topic_hint = """
Kirjoita viikoittainen AI-havainto Suomesta.
Tämä ei ole runo. Tämä on lyhyt analyyttinen teemateksti siitä, miltä jokin suomalainen arjen ilmiö näyttää tekoälyn silmin.
Valitse konkreettinen aihe: arjen muutos, teknologia, palvelut, työ, media, luonto, liikkuminen tai kuluttaminen.
"""
    else:
        topic_hint = "Kirjoita konkreettinen artikkeli suomalaisesta arjesta, taloudesta, yhteiskunnasta tai teknologiasta."

    user_prompt = f"""
Kirjoita AISuomi.blogiin uusi suomenkielinen artikkeli.

Kategoria: {kind}

AISuomi.blogin uusi linja:
AISuomi on autonominen suomalainen AI-media. Se tarkastelee Suomen arkea, taloutta, teknologiaa ja yhteiskuntaa tekoälyn näkökulmasta. Tarkoitus ei ole korvata journalismia, vaan näyttää avoimesti, millaista analysoivaa sisältöä itsenäinen AI-järjestelmä pystyy tuottamaan.

{topic_hint}

Viimeisimmät otsikot, joita EI saa toistaa eikä kierrättää:
{recent_titles_text}

Kirjoita rakenne näin:
<h1>Selkeä ja konkreettinen otsikko</h1>
<p>Lyhyt ingressi, 1-3 virkettä. Kerro heti, miksi aiheella on merkitystä.</p>

<h2>Mistä on kyse?</h2>
<p>Selitä ilmiö ymmärrettävästi.</p>

<h2>Miksi tämä näkyy juuri nyt?</h2>
<p>Anna taustaa ilman tekaistuja tarkkoja lukuja.</p>

<h2>Miten tämä näkyy arjessa?</h2>
<p>Kuvaa käytännön vaikutuksia ihmisille, perheille, yrityksille tai kunnille.</p>

<h2>Mitä kannattaa seurata seuraavaksi?</h2>
<p>Nosta esiin 2-4 asiaa, joiden kehitystä lukijan kannattaa tarkkailla.</p>

<h2>Miksi tällä on merkitystä?</h2>
<p>Tee lyhyt, rauhallinen yhteenveto.</p>

<p><em>Teksti on tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmiseditointia. Se ei ole uutinen, viranomaisohje eikä henkilökohtainen talous-, sijoitus- tai lakineuvo.</em></p>

Tyyli:
- selkeä
- rauhallinen
- analyyttinen
- konkreettinen
- ei klikkiotsikko
- ei runollinen
- ei geneerinen

Pituus: 700-1000 sanaa.
"""

    return call_openai(system_prompt, user_prompt)


def extract_title(html_body: str, kind: str) -> str:
    title = f"AISuomi – {kind} {TODAY.isoformat()}"
    start = html_body.find("<h1>")
    end = html_body.find("</h1>")
    if start != -1 and end != -1:
        candidate = html_body[start + 4:end].strip().replace("\n", " ")
        if candidate:
            title = candidate
    return title


def get_week_key(d: date) -> str:
    iso_year, iso_week, _ = d.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def ensure_category_image(kind: str, week_key: str) -> str:
    if kind not in IMAGE_CATEGORIES:
        return ""

    cat_dir = IMAGES_DIR / kind
    cat_dir.mkdir(parents=True, exist_ok=True)
    filename = f"{week_key}-{kind}.png"
    img_path = cat_dir / filename

    if img_path.exists():
        return f"/assets/images/{kind}/{filename}"

    prompt_map = {
        "talous": "rauhallinen, moderni ja neutraali kuvitus suomalaisesta taloudesta, arjen raha, asuminen ja yrittäjyys, hillitty tyyli",
        "ruoka": "valoisa ja käytännöllinen kuvitus suomalaisesta arkiruoasta ja sesongin raaka-aineista, lämmin mutta realistinen tyyli",
        "yhteiskunta": "neutraali kuvitus suomalaisesta yhteiskunnasta: kirjasto, koulu, terveyspalvelut ja julkinen liikenne, ilman logoja tai poliitikkoja",
        "teema": "moderni ja rauhallinen kuvitus Suomesta tekoälyn näkökulmasta, arki, teknologia ja suomalainen ympäristö, hillitty tyyli",
    }
    prompt = prompt_map.get(kind, "rauhallinen ja neutraali kuvitus suomalaisesta arjesta")

    headers = {
        "Authorization": f"Bearer {API_KEY}",
        "Content-Type": "application/json",
    }
    payload = {
        "model": "gpt-image-1",
        "prompt": prompt,
        "size": "1024x1024",
        "n": 1,
        "response_format": "b64_json",
    }

    resp = requests.post("https://api.openai.com/v1/images", headers=headers, json=payload, timeout=120)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI Images API error: {resp.status_code} {resp.text}")

    data = resp.json()
    img_bytes = base64.b64decode(data["data"][0]["b64_json"])
    img_path.write_bytes(img_bytes)
    return f"/assets/images/{kind}/{filename}"


def get_category_image_for_current_week(kind: str) -> str:
    return ensure_category_image(kind, get_week_key(TODAY))


def get_related_posts(kind: str, current_path: Path, max_items: int = 2) -> list[tuple[str, str]]:
    results: list[tuple[datetime, Path]] = []
    base_dir = POSTS_DIR / kind
    pattern = f"*-{kind}.html"

    for p in base_dir.glob(pattern):
        if p == current_path:
            continue
        try:
            d = datetime.strptime(p.name[:10], "%Y-%m-%d")
        except ValueError:
            continue
        results.append((d, p))

    results.sort(key=lambda item: item[0], reverse=True)
    out: list[tuple[str, str]] = []
    for _, p in results[:max_items]:
        doc_html = p.read_text(encoding="utf-8", errors="ignore")
        title = _extract_title_from_document(doc_html)
        href = f"/{p.relative_to(ROOT).as_posix()}"
        out.append((href, title))
    return out


def write_post(path: Path, kind: str, html_body: str) -> str:
    title = extract_title(html_body, kind)
    relative = path.relative_to(ROOT)
    post_url = f"https://aisuomi.blog/{relative.as_posix()}"

    image_src = None
    try:
        image_src = get_category_image_for_current_week(kind)
    except Exception as e:
        print(f"Ei voitu hakea kuvituskuvaa kategorialle {kind}: {e}")

    hero_html = ""
    if image_src:
        hero_html = f"""
        <figure class="post-hero">
          <img src="{image_src}" alt="{title} – kuvituskuva">
          <figcaption class="muted">Kuvituskuva: autonomisesti luotu AI-kuva.</figcaption>
        </figure>
        """

    related_links = get_related_posts(kind, path, max_items=2)
    related_html = ""
    if related_links:
        items_html = "\n".join(f'<li><a href="{href}">{rtitle}</a></li>' for href, rtitle in related_links)
        related_html = f"""
        <div class="card">
          <h2>Suositellut jutut</h2>
          <p class="muted">Muita AISuomi-tekstejä samasta aihepiiristä.</p>
          <ul>{items_html}</ul>
        </div>
        """

    document = f"""<!doctype html>
<html lang="fi">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="/assets/styles.css">
  </head>
  <body>
    <header class="site-header">
      <h1>{title}</h1>
      <p class="tagline">Autonominen AISuomi-artikkeli ({kind}).</p>
    </header>

    <nav class="top-nav">
      <a href="/">Etusivu</a>
      <a href="/talous.html">Talous</a>
      <a href="/ruoka.html">Ruoka</a>
      <a href="/yhteiskunta.html">Yhteiskunta</a>
      <a href="/teema.html">Teema</a>
      <a href="/uutisiasuomesta.html">Uutisia Suomesta</a>
      <a href="/privacy.html">Tietosuoja</a>
      <a href="/cookies.html">Evästeet</a>
    </nav>

    <main class="layout">
      <section class="main-column">
        {hero_html}
        {html_body}

        <div class="card">
          <h2>Jaa tämä juttu</h2>
          <p class="muted">Voit halutessasi jakaa AISuomi-jutun eteenpäin.</p>
          <p class="share-links">
            <a href="https://www.facebook.com/sharer/sharer.php?u={post_url}" target="_blank" rel="noopener">Jaa Facebookissa</a><br>
            <a href="https://twitter.com/intent/tweet?url={post_url}" target="_blank" rel="noopener">Jaa X:ssä</a><br>
            <a href="https://api.whatsapp.com/send?text={post_url}" target="_blank" rel="noopener">Jaa WhatsAppissa</a>
          </p>
        </div>

        {related_html}
      </section>
      <aside class="sidebar">
        <div class="card">
          <h2>Huomio</h2>
          <p class="muted">Teksti on tekoälyn tuottamaa sisältöä. Ihminen ei ole editoinut sitä ennen julkaisua.</p>
        </div>
        <div class="card">
          <h3>Tue AISuomi-projektia</h3>
          <p>Tämä blogi toimii täysin autonomisesti tekoälyn ohjaamana.</p>
          <p style="text-align:center; margin-top:0.5rem;">
            <a href="https://buymeacoffee.com/aisuomi" target="_blank" rel="noopener" style="text-decoration:none; font-weight:600;">→ Siirry tukisivulle</a>
          </p>
          <p class="muted">Tukeminen on vapaaehtoista eikä vaikuta sisältöön.</p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen suomalainen AI-media.
      | <a href="/">Etusivu</a>
      | <a href="/talous.html">Talous</a>
      | <a href="/ruoka.html">Ruoka</a>
      | <a href="/yhteiskunta.html">Yhteiskunta</a>
      | <a href="/teema.html">Teema</a>
      | <a href="/privacy.html">Tietosuoja</a>
      | <a href="/cookies.html">Evästeet</a>
      | <a href="/contact.html">Yhteys</a>
    </footer>
  </body>
</html>
"""
    path.write_text(dedent(document), encoding="utf-8")
    return title


def get_last_post_date(dir_path: Path, kind: str):
    dates = []
    for p in dir_path.glob(f"*-{kind}.html"):
        try:
            dates.append(datetime.strptime(p.name[:10], "%Y-%m-%d").date())
        except ValueError:
            continue
    return max(dates) if dates else None


def update_index_file(index_path: Path, new_links: list[tuple[str, str]]):
    if not new_links or not index_path.exists():
        return
    html = index_path.read_text(encoding="utf-8")
    marker = '<ul class="post-list">'
    idx = html.find(marker)
    if idx == -1:
        return
    insert_at = idx + len(marker)
    items = [f'<li><a href="{href}">{title}</a></li>' for href, title in new_links]
    middle = "\n        " + "\n        ".join(items) + "\n"
    index_path.write_text(html[:insert_at] + middle + html[insert_at:], encoding="utf-8")


def _collect_rss_entry(path: Path, base_url: str):
    try:
        d = datetime.strptime(path.name[:10], "%Y-%m-%d")
    except ValueError:
        return None
    html = path.read_text(encoding="utf-8")
    title = _extract_title_from_document(html)
    link = f"{base_url}/{path.relative_to(ROOT).as_posix()}"
    return d, link, title


def build_rss_feed(base_url: str = "https://aisuomi.blog"):
    rss_path = ROOT / "rss.xml"
    entries: list[tuple[datetime, str, str]] = []

    for sub in ("talous", "ruoka", "yhteiskunta", "teema"):
        subdir = POSTS_DIR / sub
        if subdir.exists():
            for p in subdir.glob("*.html"):
                e = _collect_rss_entry(p, base_url)
                if e:
                    entries.append(e)

    if not entries:
        return

    entries.sort(key=lambda x: x[0], reverse=True)
    entries = entries[:50]
    last_build = entries[0][0].strftime("%a, %d %b %Y %H:%M:%S +0000")

    items_xml = []
    for pub_date, link, title in entries:
        pub_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items_xml.append(f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid>{link}</guid>
      <pubDate>{pub_str}</pubDate>
    </item>""")

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AISuomi – autonominen suomalainen AI-media</title>
    <link>{base_url}/</link>
    <description>Autonomisesti tekoälyn tuottamia suomenkielisiä artikkeleita Suomen arjesta, taloudesta ja yhteiskunnasta.</description>
    <language>fi</language>
    <lastBuildDate>{last_build}</lastBuildDate>
{os.linesep.join(items_xml)}
  </channel>
</rss>
"""
    rss_path.write_text(rss_xml, encoding="utf-8")


def build_sitemap(base_url: str = "https://aisuomi.blog"):
    sitemap_path = ROOT / "sitemap.xml"
    urls: list[str] = []

    root_files = [
        "index.html", "talous.html", "ruoka.html", "yhteiskunta.html", "teema.html",
        "privacy.html", "cookies.html", "uutisiasuomesta.html", "contact.html",
    ]
    for name in root_files:
        p = ROOT / name
        if p.exists():
            urls.append(f"{base_url}/" if name == "index.html" else f"{base_url}/{name}")

    if POSTS_DIR.exists():
        for p in POSTS_DIR.rglob("*.html"):
            urls.append(f"{base_url}/{p.relative_to(ROOT).as_posix()}")

    unique_urls = []
    seen = set()
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    if not unique_urls:
        return

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
    ]
    lines.extend(f"  <url><loc>{loc}</loc></url>" for loc in unique_urls)
    lines.append("</urlset>")
    sitemap_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def main():
    POSTS_DIR.mkdir(exist_ok=True)
    for sub in ("talous", "ruoka", "yhteiskunta", "teema"):
        (POSTS_DIR / sub).mkdir(exist_ok=True)

    talous_path = make_filename("talous")
    yhteiskunta_path = make_filename("yhteiskunta")
    ruoka_path = make_filename("ruoka")
    teema_path = make_filename("teema")

    front_links: list[tuple[str, str]] = []
    talous_links: list[tuple[str, str]] = []
    yhteiskunta_links: list[tuple[str, str]] = []
    ruoka_links: list[tuple[str, str]] = []
    teema_links: list[tuple[str, str]] = []

    # Päivittäiset pääjutut
    if not post_exists(talous_path):
        body = generate_article("talous")
        title = write_post(talous_path, "talous", body)
        href = f"posts/talous/{talous_path.name}"
        talous_links.append((href, title))
        front_links.append((href, title))

    if not post_exists(yhteiskunta_path):
        body = generate_article("yhteiskunta")
        title = write_post(yhteiskunta_path, "yhteiskunta", body)
        href = f"posts/yhteiskunta/{yhteiskunta_path.name}"
        yhteiskunta_links.append((href, title))
        front_links.append((href, title))

    # Viikoittaiset lisäjutut
    last_ruoka = get_last_post_date(POSTS_DIR / "ruoka", "ruoka")
    if (last_ruoka is None) or (TODAY - last_ruoka).days >= 7:
        if not post_exists(ruoka_path):
            body = generate_article("ruoka")
            title = write_post(ruoka_path, "ruoka", body)
            ruoka_links.append((f"posts/ruoka/{ruoka_path.name}", title))

    last_teema = get_last_post_date(POSTS_DIR / "teema", "teema")
    if (last_teema is None) or (TODAY - last_teema).days >= 7:
        if not post_exists(teema_path):
            body = generate_article("teema")
            title = write_post(teema_path, "teema", body)
            teema_links.append((f"posts/teema/{teema_path.name}", title))

    if front_links:
        update_index_file(INDEX_FILE, front_links)
    if talous_links:
        update_index_file(TALOUS_INDEX_FILE, talous_links)
    if yhteiskunta_links:
        update_index_file(YHTEISKUNTA_INDEX_FILE, yhteiskunta_links)
    if ruoka_links:
        update_index_file(RUOKA_INDEX_FILE, ruoka_links)
    if teema_links:
        update_index_file(TEEMA_INDEX_FILE, teema_links)

    if not (front_links or talous_links or yhteiskunta_links or ruoka_links or teema_links):
        print("Ei uusia postauksia tälle päivälle.")

    try:
        build_rss_feed()
        build_sitemap()
    except Exception as e:
        print(f"RSS/sitemap päivitys epäonnistui: {e}")


if __name__ == "__main__":
    main()
