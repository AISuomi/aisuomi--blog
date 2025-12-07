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

¨def generate_article(kind: str) -> str:
    """
    Palauttaa HTML-leipätekstin annetulle kategoriatyypille.

    - identiteetti & villi:
        vapaa AISuomi-tyyli, AI valitsee aiheen itse, suomalainen,
        rauhallinen, vähäeleinen ote.
    - talous, ruoka, yhteiskunta, teema:
        pysyvät selvästi omissa aiheissaan.
    """

    # 1) VAPAA AISUOMI – ETUSIVU (identiteetti + villi)
    if kind in {"identiteetti", "villi"}:
        system_prompt = (
            "Kirjoitat suomenkielistä blogitekstiä AISuomi-sivustolle. "
            "Saat valita aiheen täysin vapaasti. "
            "Tyyli on suomalainen: vähäeleinen, rauhallinen, suora ja selkeä. "
            "Vältä ylitunteikasta tai amerikkalaista ilmaisua, liioittelua "
            "ja suuria dramaattisia kaaria. "
            "Käytä arkisia havaintoja, konkreettisuutta ja rehellistä sävyä. "
            "Voit kirjoittaa mistä tahansa: arjesta, tunteista, historiasta, "
            "yhteiskunnasta, taloudesta, luonnosta, teknologiasta, "
            "kuvitteellisista tarinoista, runoudesta tai mistä vain keksit. "
            "Tekstin ei tarvitse olla kaunokirjallista tai runollista, "
            "voit kirjoittaa kuin suomalainen kirjoittaja, joka ei tee "
            "itsestään numeroa mutta ajattelee asioita rauhassa. "
            "Et lisää loppuun kehotuksia kommentoida, jakaa tai tilata."
        )

        user_prompt = """
Kirjoita suomenkielinen blogiteksti. AI saa päättää aiheen itse.

Käytä seuraavaa rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi: 1–3 virkettä, joissa kerrot mistä tekstissä
suurin piirtein on kyse.</p>

<h2>Alaotsikko</h2>
<p>Leipätekstiä useammassa kappaleessa. Voit pohtia aihetta,
kertoa havaintoja, kuvauksia tai ajatuksia rauhalliseen sävyyn.</p>

<h2>Toinen alaotsikko</h2>
<p>Jatka aihetta, vie ajatusta hieman eteenpäin tai sivuun:
mitä tästä voi oppia, miltä tämä tuntuu arjessa, tai mihin suuntaan
ajatukset vievät.</p>

Loppuun lisää yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmisen editointia.
"""
        return call_openai(system_prompt, user_prompt)

    # 2) TALOUS – pysyy talousaiheisena
    if kind == "talous":
        system_prompt = (
            "Kirjoitat AISuomi-blogiin talousaiheisen tekstin. "
            "Käsittelet talouden ilmiöitä yleisellä tasolla. "
            "Et anna yksittäisiin sijoituskohteisiin kohdistuvia neuvoja, "
            "vaan kuvailet ilmiöitä. Tyyli on rauhallinen ja selkeä."
        )

        user_prompt = """
Kirjoita suomenkielinen talousaiheinen blogiteksti.

Aiheen tulee liittyä Suomen talouteen, arjen talouteen, hintatasoon
tai talouden ilmiöihin yleisellä tasolla.

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

Lisäksi loppuun yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmisen editointia.
"""
        return call_openai(system_prompt, user_prompt)

    # 3) RUOKA – pysyy ruoka-aiheisena
    if kind == "ruoka":
        system_prompt = (
            "Kirjoitat AISuomi-blogiin ruoka-aiheisen tekstin. "
            "Voit käsitellä esimerkiksi ruokaa, ruuanlaittoa, "
            "ruokakulttuuria ja arjen syömistä. Tyyli on rauhallinen."
        )

        user_prompt = """
Kirjoita suomenkielinen ruoka-aiheinen blogiteksti.

Aiheen tulee liittyä ruokaan, ruuanlaittoon, ruokakulttuuriin
tai arjen syömiseen.

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä ruokateemasta.</p>

<h2>Ruokatarina tai teema</h2>
<p>Kuvaile aihetta useamman kappaleen verran: arjen ruoka, sesongin
raaka-aineet, yhdessä syöminen tai muu vastaava.</p>

<h2>Viikon ruokalista</h2>
<p>Esittele viikon ruokalista arkipäiville ja viikonlopulle.</p>
<ul>
  <li>Päivä + ruokalaji + lyhyt kuvaus.</li>
  <li>Toista, kunnes viikko on käsitelty.</li>
</ul>

<h2>Reseptipoimintoja</h2>
<p>Valitse 1–3 ruokalajia listasta ja anna lyhyet reseptit
(ainesosat ja valmistusohje tiiviisti).</p>

Loppuun yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmiseditointia.
"""
        return call_openai(system_prompt, user_prompt)

    # 4) YHTEISKUNTA – neutraali, faktapainotteinen
    if kind == "yhteiskunta":
        system_prompt = (
            "Kirjoitat AISuomi-blogiin neutraalin yhteiskunta-aiheisen tekstin. "
            "Kuvailet ilmiötä tai järjestelmää (esim. koulu, terveydenhuolto, "
            "liikenne, verotus, palvelut) yleisellä tasolla. "
            "Vältät puoluepolitiikkaa ja vahvoja kannanottoja."
        )

        user_prompt = """
Kirjoita suomenkielinen yhteiskunta-aiheinen blogiteksti.

Aiheen tulee liittyä johonkin Suomen yhteiskunnalliseen rakenteeseen,
palveluun tai arjen järjestelmään (esim. koulutus, terveydenhuolto,
liikenne, verotus, sosiaaliturva) neutraalilla otteella.

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä yhteiskunnallisesta ilmiöstä.</p>

<h2>Mistä ilmiössä on kyse?</h2>
<p>Kuvaile taustaa ja nykytilannetta neutraalisti useamman kappaleen verran.</p>

<h2>Miten tämä näkyy arjessa?</h2>
<p>Anna konkreettisia esimerkkejä ilman vahvaa puolesta–tai–vastaan-asettelua.</p>

<p>Loppuun lisää lyhyt kappale, jossa muistutat, että teksti
on yleisluonteinen kuvaus eikä ota kantaa puoluepolitiikkaan.</p>

Lisäksi loppuun yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmisen editointia.
"""
        return call_openai(system_prompt, user_prompt)

    # 5) TEEMA – runot / joulu / uusivuosi
    if kind == "teema":
        # Joulu / uusivuosi / muu
        if TODAY.month == 12 and TODAY.day <= 25:
            topic_instruction = (
                "jouluisesta ja rauhallisesta tunnelmasta, talvisesta luonnosta "
                "tai lempeästä joulunvietosta. Voit viitata myös kristilliseen "
                "jouluperinteeseen (esim. hiljainen yö, tähdet, enkelit), "
                "mutta ilman voimakasta julistusta."
            )
        elif (TODAY.month == 12 and TODAY.day > 25) or (TODAY.month == 1 and TODAY.day == 1):
            topic_instruction = (
                "uuden vuoden tunnelmasta, toiveikkuudesta, rauhallisesta "
                "vuodenvaihteesta ja pienistä päätöksistä. Vältä päihteitä ja "
                "rajuja ilotulitekuvauksia, keskity valoon, hiljaisuuteen ja toivoon."
            )
        else:
            topic_instruction = (
                "lyhyestä runosta tai laulunomaisesta tekstistä, joka liittyy "
                "vuodenaikaan, luontoon, arkeen tai ystävällisyyteen. "
                "Teksti saa olla leikittelevä, mutta rauhallinen ja kaikenikäisille sopiva."
            )

        system_prompt = (
            "Kirjoitat AISuomi-blogiin teemallisen runon tai laulunomaisen tekstin. "
            "Tyyli on rauhallinen, selkeä ja luettavissa kaikenikäisille."
        )

        user_prompt = f"""
Kirjoita suomenkielinen runo- tai laulunomainen teksti.

Aiheen tulee olla {topic_instruction}

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt johdanto, 1–3 virkettä.</p>

<h2>Runo</h2>
<p>Kirjoita runo niin, että jokainen säe tai pari säettä on omassa rivissään
(esimerkiksi <br>-tagien avulla) tai omissa kappaleissaan.</p>

Loppuun lisää yksi lyhyt kappale, jossa kerrot, että teksti on
tekoälyn kokeellisesti tuottamaa sisältöä ilman ihmiseditointia.
"""
        return call_openai(system_prompt, user_prompt)

    # 6) VARA – jos kind on jokin odottamaton
    system_prompt = (
        "Kirjoitat suomenkielisen blogitekstin AISuomi-sivustolle. "
        "Tyyli on suomalainen: rauhallinen ja suora."
    )
    user_prompt = """
Kirjoita suomenkielinen blogiteksti vapaasti valitsemastasi aiheesta.

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi.</p>

<h2>Alaotsikko</h2>
<p>Leipätekstiä useammassa kappaleessa.</p>

<h2>Toinen alaotsikko</h2>
<p>Lisää pohdintaa aiheesta.</p>

Loppuun lyhyt kappale, jossa kerrot että teksti on tekoälyn
kokeellisesti tuottamaa sisältöä ilman ihmiseditointia.
"""
    return call_openai(system_prompt, user_prompt)


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
