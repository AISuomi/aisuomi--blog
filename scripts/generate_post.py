import os
import json
from datetime import datetime
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
IMAGE_CATEGORIES = {"identiteetti", "villi", "talous", "ruoka", "yhteiskunta", "teema"}


# Kategoriasivut
TALOUS_INDEX_FILE = ROOT / "talous.html"
RUOKA_INDEX_FILE = ROOT / "ruoka.html"
YHTEISKUNTA_INDEX_FILE = ROOT / "yhteiskunta.html"
TEEMA_INDEX_FILE = ROOT / "teema.html"

TODAY = datetime.utcnow().date()


def make_filename(kind: str) -> Path:
    """
    Luo tiedostopolun annetulle kategoriatyypille.
    - identiteetti, villi: posts/YYYY-MM-DD-kind.html
    - muut: posts/kind/YYYY-MM-DD-kind.html
    """
    if kind in {"talous", "ruoka", "yhteiskunta", "teema"}:
        return POSTS_DIR / kind / f"{TODAY.isoformat()}-{kind}.html"
    return POSTS_DIR / f"{TODAY.isoformat()}-{kind}.html"


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
        "temperature": 0.7,
    }

    resp = requests.post(API_URL, headers=headers, json=payload, timeout=60)
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI API error: {resp.status_code} {resp.text}")

    data = resp.json()
    try:
        content = data["choices"][0]["message"]["content"]
    except Exception as e:
        raise RuntimeError(
            f"Unexpected response format: {json.dumps(data)[:500]}"
        ) from e

    return content


def generate_article(kind: str) -> str:
    """
    Palauttaa HTML-leipätekstin annetulle kategoriatyypille.
    kind: identiteetti | villi | talous | ruoka | yhteiskunta | teema
    """
    # Perusraamit kaikille
    system_prompt = (
        "Olet AISuomi-blogin automaattinen kirjoituskone. "
        "Kirjoitat selkeää, rauhallista ja neutraalia suomen kieltä. "
        "Vältät politiikkaa, puolueita, ideologioita (kuten woke/maga/"
        "äärifeminismi/äärisovinismi), uskonnollisia kiistoja, sotaa, "
        "rokotekeskusteluja, rajua väkivaltaa, seksiä, päihteitä ja muuta "
        "lapsille sopimatonta sisältöä. Kirjoitat niin, että teksti sopii "
        "kaikenikäisille lukijoille. Tuotat vastauksen HTML-leipätekstinä "
        "ilman <html>, <head> tai <body> -tageja. Et lisää mainoksia etkä "
        "kehotuksia kommentoida."
    )

    # Kategorikohtaiset ohjeet
    if kind == "identiteetti":
        topic_instruction = (
            "suomalaisuudesta, Suomesta, suomen kielestä tai suomalaisesta "
            "arjesta, historiasta, luonnosta tai kulttuurista. "
            "Vältä päivänpolitiikkaa, puolueita, vaaleja, hallituksia, "
            "ulkopolitiikkaa ja kansainvälisiä konflikteja. "
            "Älä ota kantaa ideologioihin (esim. woke, maga, erilaiset "
            "äärifeminismi- tai äärisovinismi-keskustelut, uskonnolliset kiistat, "
            "ilmastokiistat, rokotekeskustelut). "
            "Kirjoita kuin yleisölle, jossa voi olla myös lapsia: "
            "siisti, asiallinen, rauhallinen sävy."
        )
        structure_instruction = """
Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä.</p>

<h2>Alaotsikko</h2>
<p>Useampi kappale leipätekstiä.</p>

<h2>Toinen alaotsikko</h2>
<p>Lisää selkeää tekstisisältöä.</p>
"""

    elif kind == "villi":
        topic_instruction = (
            "vapaasta ja mielikuvituksellisesta mutta harmittomasta aiheesta, "
            "joka liittyy esimerkiksi arkeen, luontoon, ihmisten väliseen "
            "ystävällisyyteen, luoviin ajatuksiin, filosofiaan, kevyisiin "
            "tulevaisuuskuviin tai arkisiin oivalluksiin. "
            "Vältä täysin politiikkaa, ideologioita, sotaa, rikoksia, "
            "väkivaltaa, päihteitä, seksiä, syrjintää ja muita "
            "riitaisiksi tai ronskeiksi koettuja aiheita. "
            "Teksti saa olla outo tai leikkisä, mutta aina siten, että "
            "se sopii myös lapsen luettavaksi."
        )
        structure_instruction = """
Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä.</p>

<h2>Alaotsikko</h2>
<p>Useampi kappale leipätekstiä.</p>

<h2>Toinen alaotsikko</h2>
<p>Lisää luovaa mutta rauhallista tekstisisältöä.</p>
"""

    elif kind == "talous":
        topic_instruction = (
            "Suomen talouteen, arjen talouteen, hintatasoon tai "
            "talouden ilmiöihin liittyvästä aiheesta. "
            "Kerro ilmiöistä yleisellä tasolla ilman yksityiskohtaisia "
            "ohjeita yksittäisiin osakkeisiin tai rahastoihin. "
            "Kuvaile suuntaa-antavasti, mitä tekijöitä voi pitää "
            "nousevina ja mitä laskevina, mutta älä anna "
            "henkilökohtaisia sijoitusneuvoja."
        )
        structure_instruction = """
Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä talouden ilmiöstä.</p>

<h2>Taustaa</h2>
<p>Kuvaile aihetta rauhallisesti ja selkeästi useamman kappaleen verran.</p>

<h2>Nousevat ilmiöt</h2>
<ul>
  <li>Kuvaile yksi talouteen liittyvä nouseva ilmiö tai sijoituskohdetyyppi yleisellä tasolla.</li>
  <li>Kuvaile toinen nouseva ilmiö tai sijoituskohdetyyppi yleisellä tasolla.</li>
</ul>

<h2>Laskevat ilmiöt</h2>
<ul>
  <li>Kuvaile yksi laskeva tai varovaisuutta vaativa ilmiö yleisellä tasolla.</li>
  <li>Kuvaile toinen laskeva tai varovaisuutta vaativa ilmiö yleisellä tasolla.</li>
</ul>

<p>Loppuun lisää selkeä kappale, jossa kerrot, että teksti ei ole
sijoitusneuvoja vaan viihteellistä, yleisluonteista pohdintaa.</p>
"""

    elif kind == "ruoka":
        topic_instruction = (
            "ruoasta, ruuanlaitosta, ruokakulttuurista tai arjen syömisestä. "
            "Voit käsitellä esimerkiksi sesongin raaka-aineita, "
            "arkiruokaa tai rauhallista yhdessä syömisen tunnelmaa."
        )
        structure_instruction = """
Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä ruokateemasta.</p>

<h2>Ruokatarina tai teema</h2>
<p>Kuvaile aihetta useamman kappaleen verran.</p>

<h2>Viikon ruokalista</h2>
<p>Esittele viikon ruokalista arkipäiville ja viikonlopulle.</p>
<ul>
  <li>Päivä + ruokalaji + lyhyt kuvaus.</li>
  <li>Toista, kunnes viikko on käsitelty.</li>
</ul>

<h2>Reseptipoimintoja</h2>
<p>Valitse 1–3 ruokalajia listasta ja anna niihin lyhyet reseptit
(ainesosat ja valmistusohje tiiviisti).</p>
"""

    elif kind == "yhteiskunta":
        topic_instruction = (
            "Suomen yhteiskunnallisesta rakenteesta, historiasta, "
            "palveluista tai arjen järjestelmistä (esim. koulu, terveydenhuolto, "
            "liikenne, verotus) kuvailevalla ja neutraalilla tavalla. "
            "Vältä vahvoja mielipiteitä ja selkeää puolesta–tai–vastaan-asettelua. "
            "Kuvaa ilmiöitä monipuolisesti ja faktapainotteisesti."
        )
        structure_instruction = """
Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä yhteiskunnallisesta ilmiöstä.</p>

<h2>Mistä ilmiössä on kyse?</h2>
<p>Kuvaile taustaa ja nykytilannetta neutraalisti.</p>

<h2>Miten tämä näkyy arjessa?</h2>
<p>Anna esimerkkejä ilman vahvaa kannanottoa.</p>

<p>Loppuun lisää lyhyt kappale, jossa muistutat, että teksti
on yleisluonteinen kuvaus eikä ota kantaa puoluepolitiikkaan.</p>
"""

    elif kind == "teema":
        # Joulu / uusivuosi / yleinen runoteema
        if TODAY.month == 12 and TODAY.day <= 25:
            # Joulu
            topic_instruction = (
                "jouluisesta ja rauhallisesta tunnelmasta, talvisesta luonnosta tai "
                "lempeästä joulunvietosta. Voit viitata myös kristilliseen "
                "joulun perinteeseen (esimerkiksi hiljainen yö, enkelit, "
                "tähdet), mutta ilman voimakasta julistusta."
            )
        elif (TODAY.month == 12 and TODAY.day > 25) or (TODAY.month == 1 and TODAY.day == 1):
            # Uusivuosi
            topic_instruction = (
                "uuden vuoden tunnelmasta, toiveikkuudesta, rauhallisesta "
                "vuodenvaihteesta ja pienistä päätöksistä. Vältä kuvaamasta "
                "päihteitä tai rajuja ilotulitteita, keskity ennemmin valoon, "
                "hiljaisuuteen ja tulevaisuuden toivoon."
            )
        else:
            # Yleinen runo/laulu myöhemmin
            topic_instruction = (
                "lyhyestä runosta tai laulunomaisesta tekstistä, joka liittyy "
                "esimerkiksi vuodenaikaan, luontoon, arkeen tai ystävällisyyteen. "
                "Teksti saa olla leikittelevä, mutta rauhallinen ja kaikenikäisille sopiva."
            )

        structure_instruction = """
Kirjoita runomuotoinen tai laulunomainen teksti käyttäen HTML-rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt johdanto, 1–3 virkettä.</p>

<h2>Runo</h2>
<p>Kirjoita runo niin, että jokainen säe tai pari säettä on omassa rivissään
(esimerkiksi <br>-tagien avulla) tai omissa kappaleissaan.</p>
"""

    else:
        # Varmuuden vuoksi: käsitellään kuin identiteetti
        topic_instruction = (
            "suomalaisuudesta, Suomesta tai suomalaisesta arjesta neutraalisti."
        )
        structure_instruction = """
<h1>Otsikko</h1>
<p>Lyhyt ingressi.</p>
"""

    user_prompt = f"""
Kirjoita suomenkielinen blogiteksti. Muotoile vastauksesi pelkkänä
HTML-sisältönä ilman <html>, <head> tai <body> -tageja.

Aiheen tulee olla {topic_instruction}
{structure_instruction}

Loppuun lisää yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmiseditointia.
"""

    return call_openai(system_prompt, user_prompt)


def extract_title(html_body: str, kind: str) -> str:
    title = f"AISuomi – {kind} {TODAY.isoformat()}"
    start = html_body.find("<h1>")
    end = html_body.find("</h1>")
    if start != -1 and end != -1:
        candidate = html_body[start + 4 : end].strip().replace("\n", " ")
        if candidate:
            title = candidate
    return title

def write_post(path: Path, kind: str, html_body: str) -> str:
    # Otsikko <h1>:stä tai varatitteli
    title = extract_title(html_body, kind)

    # Absoluuttinen URL jakoa varten (FB / X / WhatsApp)
    relative = path.relative_to(ROOT)
    post_url = f"https://aisuomi.blog/{relative.as_posix()}"

    # Yritetään hakea mahdollinen kuvituskuva tälle kategorialle
    image_src = None
    try:
        image_src = get_category_image_for_current_week(kind)
    except Exception as e:
        print(f"Ei voitu hakea kuvituskuvaa kategorialle {kind}: {e}")

    # Haetaan suositellut jutut (sisäinen “AI-suositus”)
    related_links = get_related_posts(kind, path, max_items=2)

    # Rakennetaan mahdollinen kuvablokki
    if image_src:
        hero_html = f"""
        <figure class="post-hero">
          <img src="{image_src}" alt="{title} – kuvituskuva">
          <figcaption class="muted">
            Kuvituskuva: autonomisesti luotu AI-kuva.
          </figcaption>
        </figure>
        """
    else:
        hero_html = ""

    # Rakennetaan suositellut jutut -kortti
    if related_links:
        items_html = "\n".join(
            f'<li><a href="{href}">{rtitle}</a></li>' for href, rtitle in related_links
        )
        related_html = f"""
        <div class="card">
          <h2>Suositellut jutut</h2>
          <p class="muted">Muita AISuomi-tekstejä samasta aihepiiristä.</p>
          <ul>
            {items_html}
          </ul>
        </div>
        """
    else:
        related_html = ""

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
      <p class="tagline">Autonominen AISuomi-blogikirjoitus ({kind}).</p>
    </header>

       <nav class="top-nav">
  <a href="/index.html">Etusivu</a>
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
          <p class="muted">
            Voit halutessasi jakaa AISuomi-jutun eteenpäin.
          </p>
          <p class="share-links">
            <a href="https://www.facebook.com/sharer/sharer.php?u={post_url}"
               target="_blank" rel="noopener">
              Jaa Facebookissa
            </a><br>
            <a href="https://twitter.com/intent/tweet?url={post_url}"
               target="_blank" rel="noopener">
              Jaa X:ssä
            </a><br>
            <a href="https://api.whatsapp.com/send?text={post_url}"
               target="_blank" rel="noopener">
              Jaa WhatsAppissa
            </a>
          </p>
        </div>

        {related_html}
      </section>
      <aside class="sidebar">
        <div class="card">
          <h2>Huomio</h2>
          <p class="muted">
            Teksti on tekoälyn tuottamaa sisältöä. Ihminen ei ole
            editoinut sitä ennen julkaisua.
          </p>
        </div>
        <div class="card">
          <h3>Tue AISuomi-projektia</h3>
          <p>
            Tämä blogi toimii täysin autonomisesti tekoälyn ohjaamana.
            Jos haluat tukea projektin jatkokehitystä, voit tehdä pienen
            vapaaehtoisen lahjoituksen.
          </p>
          <p style="text-align:center; margin-top:0.5rem;">
            <a href="https://buymeacoffee.com/aisuomi" target="_blank" rel="noopener"
               style="text-decoration:none; font-weight:600;">
              → Siirry tukisivulle
            </a>
          </p>
          <p class="muted">
            Tukeminen on vapaaehtoista eikä vaikuta sisältöön.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen AI-blogi.
      | <a href="../index.html">Etusivu</a>
      | <a href="../talous.html">Talous</a>
      | <a href="../ruoka.html">Ruoka</a>
      | <a href="../yhteiskunta.html">Yhteiskunta</a>
      | <a href="../teema.html">Teema</a>
      | <a href="../privacy.html">Tietosuoja</a>
      | <a href="../cookies.html">Evästeet</a>
      | <a href="../contact.html">Yhteys</a>
    </footer>
  </body>
</html>
"""
    path.write_text(dedent(document), encoding="utf-8")
    return title

def get_last_post_date(dir_path: Path, kind: str):
    """
    Palauttaa viimeisimmän päivämäärän (date) annetusta hakemistosta,
    jossa tiedostonimi on muotoa YYYY-MM-DD-kind.html.
    """
    dates = []
    for p in dir_path.glob(f"*-{kind}.html"):
        name = p.name
        try:
            d = datetime.strptime(name[:10], "%Y-%m-%d").date()
            dates.append(d)
        except ValueError:
            continue

    if not dates:
        return None
    return max(dates)

def get_week_key(date: datetime.date) -> str:
    iso_year, iso_week, _ = date.isocalendar()
    return f"{iso_year}-W{iso_week:02d}"


def ensure_category_image(kind: str, week_key: str) -> str:
    """
    Varmistaa, että kategoria-kindille on olemassa kuvituskuva tälle viikolle.
    Palauttaa kuvan polun /assets/images/... -muodossa (URL:ia varten).
    Luo kuvan kerran viikossa per kategoria OpenAI-kuvamallilla.
    """
    if kind not in IMAGE_CATEGORIES:
        return ""

    cat_dir = IMAGES_DIR / kind
    cat_dir.mkdir(parents=True, exist_ok=True)

    filename = f"{week_key}-{kind}.png"
    img_path = cat_dir / filename

    if img_path.exists():
        # Kuva on jo luotu aiemmin tällä viikolla
        return f"/assets/images/{kind}/{filename}"

    # Jos kuvaa ei ole, luodaan se OpenAI-kuvamallilla
    prompt_map = {
        "talous": (
            "rauhallinen, abstrakti kuvitus suomalaisesta taloudesta, "
            "pehmeät siniset ja vihreät sävyt, moderni mutta hillitty tyyli"
        ),
        "ruoka": (
            "valoisa, lämmin kuvitus suomalaisesta kotiruuasta ja "
            "sesongin raaka-aineista, pehmeä ja ystävällinen tyyli"
        ),
        "yhteiskunta": (
            "neutraali kuvitus suomalaisesta yhteiskunnasta: koulu, "
            "terveydenhuolto, kirjasto, ilman politiikkaa tai logoja"
        ),
        "teema": (
            "tunnelmallinen, vuodenaikaan sopiva kuvitus, kuten talvinen "
            "metsä tai hiljainen kaupunkimaisema, rauhallinen tyyli"
        ),
        "identiteetti": (
            "kuvitus suomalaisesta luonnosta ja kulttuurista, järvi, "
            "metsä ja valoisa taivas, rauhallinen ja mietiskelevä"
        ),
        "villi": (
            "mielikuvituksellinen, lempeän outo kuvitus, jossa on "
            "luontoa, valoa ja hieman satumainen tunnelma"
        ),
    }

    prompt = prompt_map.get(
        kind,
        "rauhallinen ja neutraali kuvitus suomalaisesta luonnosta ja arjesta"
    )

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

    resp = requests.post(
        "https://api.openai.com/v1/images",
        headers=headers,
        json=payload,
        timeout=120,
    )
    if resp.status_code != 200:
        raise RuntimeError(f"OpenAI Images API error: {resp.status_code} {resp.text}")

    data = resp.json()
    img_b64 = data["data"][0]["b64_json"]
    img_bytes = base64.b64decode(img_b64)
    img_path.write_bytes(img_bytes)

    return f"/assets/images/{kind}/{filename}"


def get_category_image_for_current_week(kind: str) -> str:
    """
    Julkinen apufunktio write_post:ille: yksi kuva/viikko/kategoria.
    """
    week_key = get_week_key(TODAY)
    return ensure_category_image(kind, week_key)

def _extract_title_from_document(doc_html: str) -> str:
    start = doc_html.find("<title>")
    end = doc_html.find("</title>")
    if start != -1 and end != -1:
        return doc_html[start + 7 : end].strip()
    # fallback: etsi <h1>
    start = doc_html.find("<h1>")
    end = doc_html.find("</h1>")
    if start != -1 and end != -1:
        return doc_html[start + 4 : end].strip()
    return "AISuomi – artikkeli"


def get_related_posts(kind: str, current_path: Path, max_items: int = 2) -> list[tuple[str, str]]:
    """
    Etsii samasta kategoriasta muita postauksia ja palauttaa listan
    (href, title). Yksinkertainen, mutta riittää “AI-suosittelijaksi”.
    """
    results: list[tuple[datetime, Path]] = []

    if kind in {"talous", "ruoka", "yhteiskunta", "teema"}:
        base_dir = POSTS_DIR / kind
        pattern = f"*-{kind}.html"
    else:
        base_dir = POSTS_DIR
        pattern = f"*-{kind}.html"

    for p in base_dir.glob(pattern):
        if p == current_path:
            continue
        name = p.name
        try:
            d = datetime.strptime(name[:10], "%Y-%m-%d")
        except ValueError:
            continue
        results.append((d, p))

    # Uusimmat ensin
    results.sort(key=lambda item: item[0], reverse=True)
    results = results[:max_items]

    out: list[tuple[str, str]] = []
    for _, p in results:
        doc_html = p.read_text(encoding="utf-8", errors="ignore")
        title = _extract_title_from_document(doc_html)
        rel = p.relative_to(ROOT).as_posix()
        href = f"/{rel}"
        out.append((href, title))

    return out

def update_index_file(index_path: Path, new_links: list[tuple[str, str]]):
    """
    Lisää uudet linkit annetun indeksisivun <ul class="post-list"> -listaan.
    """
    if not new_links:
        return

    html = index_path.read_text(encoding="utf-8")
    marker = '<ul class="post-list">'
    idx = html.find(marker)

    if idx != -1:
        insert_at = idx + len(marker)
        items = []
        for href, title in new_links:
            items.append(f'<li><a href="{href}">{title}</a></li>')
        middle = "\n        " + "\n        ".join(items) + "\n"
        new_html = html[:insert_at] + middle + html[insert_at:]
        index_path.write_text(new_html, encoding="utf-8")

def build_rss_feed(base_url: str = "https://aisuomi.blog"):
    """
    Rakentaa yksinkertaisen RSS 2.0 -syötteen kaikista posteista ja
    kirjoittaa sen juureen tiedostoon rss.xml.
    """
    rss_path = ROOT / "rss.xml"

    entries: list[tuple[datetime, str, str]] = []

    # Kerää kaikki postit: posts/*.html ja posts/**/**/*.html
    # (sekä juuren postit että alikansiot talous/ruoka/yhteiskunta/teema)
    for p in POSTS_DIR.glob("*.html"):
        entries.append(_collect_rss_entry(p, base_url))
    for sub in ("talous", "ruoka", "yhteiskunta", "teema"):
        subdir = POSTS_DIR / sub
        if subdir.exists():
            for p in subdir.glob("*.html"):
                entries.append(_collect_rss_entry(p, base_url))

    # Suodata pois epäonnistuneet (None) ja lajittele uusimmat ensin
    entries = [e for e in entries if e is not None]  # type: ignore
    entries.sort(key=lambda x: x[0], reverse=True)

    # Rajaa esim. 50 uusimpaan
    entries = entries[:50]

    if not entries:
        return

    last_build = entries[0][0].strftime("%a, %d %b %Y %H:%M:%S +0000")

    items_xml = []
    for pub_date, link, title in entries:
        pub_str = pub_date.strftime("%a, %d %b %Y %H:%M:%S +0000")
        items_xml.append(
            f"""    <item>
      <title>{title}</title>
      <link>{link}</link>
      <guid>{link}</guid>
      <pubDate>{pub_str}</pubDate>
    </item>"""
        )

    rss_xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<rss version="2.0">
  <channel>
    <title>AISuomi – autonominen AI-blogi</title>
    <link>{base_url}/</link>
    <description>Autonomisesti tekoälyn tuottamia suomenkielisiä tekstejä.</description>
    <language>fi</language>
    <lastBuildDate>{last_build}</lastBuildDate>
{os.linesep.join(items_xml)}
  </channel>
</rss>
"""
    rss_path.write_text(rss_xml, encoding="utf-8")


def _collect_rss_entry(path: Path, base_url: str):
    """
    Palauttaa (päivämäärä, linkki, otsikko) tai None, jos tiedosto ei
    sovi RSS-syötteeseen.
    """
    name = path.name
    try:
        d = datetime.strptime(name[:10], "%Y-%m-%d")
    except ValueError:
        return None

    # Lue otsikko <title>-tagista
    html = path.read_text(encoding="utf-8")
    start = html.find("<title>")
    end = html.find("</title>")
    if start == -1 or end == -1:
        return None
    title = html[start + 7 : end].strip()

    rel = path.relative_to(ROOT)
    link = f"{base_url}/{rel.as_posix()}"
    return d, link, title
def build_sitemap(base_url: str = "https://aisuomi.blog"):
    """
    Rakentaa yksinkertaisen sitemap.xml-tiedoston, joka sisältää
    kaikki tärkeät sivut ja postit.
    """
    sitemap_path = ROOT / "sitemap.xml"

    urls: list[str] = []

    # Pääsivut
    root_files = [
        "index.html",
        "talous.html",
        "ruoka.html",
        "yhteiskunta.html",
        "teema.html",
        "privacy.html",
        "cookies.html",
    ]

    for name in root_files:
        p = ROOT / name
        if p.exists():
            if name == "index.html":
                urls.append(f"{base_url}/")
            else:
                urls.append(f"{base_url}/{name}")

    # Kaikki postit posts/-hakemistosta (myös alikansiot)
    if POSTS_DIR.exists():
        for p in POSTS_DIR.rglob("*.html"):
            rel = p.relative_to(ROOT)
            urls.append(f"{base_url}/{rel.as_posix()}")

    # Poista duplikaatit
    seen = set()
    unique_urls = []
    for u in urls:
        if u not in seen:
            seen.add(u)
            unique_urls.append(u)

    if not unique_urls:
        return

    lines = [
        '<?xml version="1.0" encoding="UTF-8"?>',
        '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">'
    ]
    for loc in unique_urls:
        lines.append(f"  <url><loc>{loc}</loc></url>")
    lines.append("</urlset>")

    sitemap_xml = "\n".join(lines) + "\n"
    sitemap_path.write_text(sitemap_xml, encoding="utf-8")


def main():
    # Perusrakenne
    POSTS_DIR.mkdir(exist_ok=True)
    # Alikansiot uusille blogeille
    for sub in ("talous", "ruoka", "yhteiskunta", "teema"):
        (POSTS_DIR / sub).mkdir(exist_ok=True)

    identity_path = make_filename("identiteetti")
    wild_path = make_filename("villi")
    talous_path = make_filename("talous")
    ruoka_path = make_filename("ruoka")
    yhteiskunta_path = make_filename("yhteiskunta")
    teema_path = make_filename("teema")

    # Etusivun linkit (vain identiteetti + villi)
    front_links: list[tuple[str, str]] = []

    # Kategorioiden linkit
    talous_links: list[tuple[str, str]] = []
    ruoka_links: list[tuple[str, str]] = []
    yhteiskunta_links: list[tuple[str, str]] = []
    teema_links: list[tuple[str, str]] = []

    # 1) Päivittäinen identiteetti
    if not post_exists(identity_path):
        body = generate_article("identiteetti")
        title = write_post(identity_path, "identiteetti", body)
        front_links.append((f"posts/{identity_path.name}", title))

    # 2) Joka toinen päivä villi (parilliset päivät)
    if TODAY.day % 2 == 0 and not post_exists(wild_path):
        body = generate_article("villi")
        title = write_post(wild_path, "villi", body)
        front_links.append((f"posts/{wild_path.name}", title))

    # 3) Talous – noin kerran viikossa
    talous_dir = POSTS_DIR / "talous"
    last_talous = get_last_post_date(talous_dir, "talous")
    if (last_talous is None) or (TODAY - last_talous).days >= 7:
        if not post_exists(talous_path):
            body = generate_article("talous")
            title = write_post(talous_path, "talous", body)
            talous_links.append((f"posts/talous/{talous_path.name}", title))

    # 4) Ruoka – noin kerran viikossa
    ruoka_dir = POSTS_DIR / "ruoka"
    last_ruoka = get_last_post_date(ruoka_dir, "ruoka")
    if (last_ruoka is None) or (TODAY - last_ruoka).days >= 7:
        if not post_exists(ruoka_path):
            body = generate_article("ruoka")
            title = write_post(ruoka_path, "ruoka", body)
            ruoka_links.append((f"posts/ruoka/{ruoka_path.name}", title))

    # 5) Yhteiskunta – noin kerran viikossa
    yhteiskunta_dir = POSTS_DIR / "yhteiskunta"
    last_yhteiskunta = get_last_post_date(yhteiskunta_dir, "yhteiskunta")
    if (last_yhteiskunta is None) or (TODAY - last_yhteiskunta).days >= 7:
        if not post_exists(yhteiskunta_path):
            body = generate_article("yhteiskunta")
            title = write_post(yhteiskunta_path, "yhteiskunta", body)
            yhteiskunta_links.append(
                (f"posts/yhteiskunta/{yhteiskunta_path.name}", title)
            )

    # 6) Teemablogi – joulu / uusivuosi / viikkorunot
    teema_dir = POSTS_DIR / "teema"
    should_teema = False

    if TODAY.month == 12 and TODAY.day <= 25:
        # Jouluteema: yksi runo per päivä, kunnes päivän tiedosto on olemassa
        if not post_exists(teema_path):
            should_teema = True
    elif (TODAY.month == 12 and TODAY.day > 25) or (
        TODAY.month == 1 and TODAY.day == 1
    ):
        # Uusivuosi: myös yksi per päivä tälle välille
        if not post_exists(teema_path):
            should_teema = True
    else:
        # 2.1. alkaen: yksi runo/laulu noin kerran viikossa
        last_teema = get_last_post_date(teema_dir, "teema")
        if (last_teema is None) or (TODAY - last_teema).days >= 7:
            if not post_exists(teema_path):
                should_teema = True

    if should_teema:
        body = generate_article("teema")
        title = write_post(teema_path, "teema", body)
        teema_links.append((f"posts/teema/{teema_path.name}", title))

    # Päivitä etusivu (vain identiteetti ja villi näkyvät siellä)
    if front_links:
        update_index_file(INDEX_FILE, front_links)

    # Päivitä kategoriasivut
    if talous_links:
        update_index_file(TALOUS_INDEX_FILE, talous_links)

    if ruoka_links:
        update_index_file(RUOKA_INDEX_FILE, ruoka_links)

    if yhteiskunta_links:
        update_index_file(YHTEISKUNTA_INDEX_FILE, yhteiskunta_links)

    if teema_links:
        update_index_file(TEEMA_INDEX_FILE, teema_links)

    if not (front_links or talous_links or ruoka_links or yhteiskunta_links or teema_links):
        print("Ei uusia postauksia tälle päivälle.")

    # Lopuksi päivitä RSS-syöte ja sivukartta
    try:
        build_rss_feed()
        build_sitemap()
    except Exception as e:
        print(f"RSS/sitemap päivitys epäonnistui: {e}")



if __name__ == "__main__":
    main()
