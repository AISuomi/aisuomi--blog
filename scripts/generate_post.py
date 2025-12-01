import os
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from openai import OpenAI

# API-avain tulee GitHubin secrettinä
client = OpenAI(api_key=os.environ["OPENAI_API_KEY"])

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_FILE = ROOT / "index.html"

TODAY = datetime.utcnow().date()


def make_filename(kind: str) -> Path:
    # kind = "identiteetti" tai "villi"
    return POSTS_DIR / f"{TODAY.isoformat()}-{kind}.html"


def post_exists(path: Path) -> bool:
    return path.exists()


def generate_article(kind: str) -> str:
    if kind == "identiteetti":
        topic_instruction = (
            "suomalaisuudesta, suomen kielestä, suomalaisesta yhteiskunnasta "
            "tai kulttuurista. Vältä puhdasta päivänpolitiikkaa ja pysy "
            "pohdiskelevana, rakentavana ja faktasuuntautuneena."
        )
    else:
        topic_instruction = (
            "vapaasta mutta harmittomasta aiheesta, joka voi liittyä "
            "esimerkiksi arkiseen elämään Suomessa, luontoon, "
            "ajattelutapoihin, tulevaisuuskuviin tai teknologiaan. "
            "Vältä väkivaltaa, vihaa, syrjintää tai sensaatiohakuisuutta."
        )

    system_prompt = (
        "Olet AISuomi-blogin automaattinen kirjoituskone. Kirjoitat selkeää, "
        "kohtuullisen rauhallista ja neutraalia suomen kieltä. Tuotat vastauksen "
        "suoraan HTML-muotoisena leipätekstinä, mutta ET lisää <html>, <head> "
        "tai <body> -tageja. Et lisää mainoksia, etkä kehotuksia kommentoida."
    )

    user_prompt = f"""
Kirjoita suomenkielinen blogiteksti. Muotoile vastauksesi niin, että
se on pelkkää HTML-sisältöä ilman <html>, <head> tai <body> -tageja.

Aiheen tulee olla {topic_instruction}

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä.</p>
<h2>Alaotsikko</h2>
<p>Leipätekstiä useampia kappaleita.</p>
<h2>Toinen alaotsikko</h2>
<p>Lisää leipätekstiä.</p>

Lopussa yksi lyhyt kappale, jossa kerrotaan, että teksti on
tekoälyn kirjoittama kokeellinen sisältö, jota ihminen ei ole
editoinut ennen julkaisua. Älä lisää mitään mainostekstiä.
"""

    resp = client.chat.completions.create(
        model="gpt-4.1-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt},
        ],
        temperature=0.7,
    )

    content = resp.choices[0].message.content
    if not content:
        raise RuntimeError("Ei saatu sisältöä mallilta.")
    return content


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
    title = extract_title(html_body, kind)
    document = f"""<!doctype html>
<html lang="fi">
  <head>
    <meta charset="utf-8">
    <title>{title}</title>
    <meta name="viewport" content="width=device-width, initial-scale=1">
    <link rel="stylesheet" href="../assets/styles.css">
  </head>
  <body>
    <header class="site-header">
      <h1>{title}</h1>
      <p class="tagline">Autonominen AISuomi-blogikirjoitus ({kind}).</p>
    </header>

    <nav class="top-nav">
      <a href="../index.html">Etusivu</a>
      <a href="../privacy.html">Tietosuoja</a>
      <a href="../cookies.html">Evästeet</a>
    </nav>

    <main class="layout">
      <section class="main-column">
      {html_body}
      </section>
      <aside class="sidebar">
        <div class="card">
          <h2>Huomio</h2>
          <p class="muted">
            Tämä kirjoitus on tekoälyn tuottama. Ihminen ei ole editoinut
            sitä ennen julkaisua. Jos löydät virheitä, ne kertovat enemmän
            järjestelmän rajoista kuin Suomesta.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen suomenkielinen AI-blogikokeilu.
      | <a href="../index.html">Etusivu</a>
      | <a href="../privacy.html">Tietosuoja</a>
      | <a href="../cookies.html">Evästeet</a>
    </footer>
  </body>
</html>
"""
    path.write_text(dedent(document), encoding="utf-8")
    return title


def update_index(new_links: list[tuple[str, str]]):
    """Lisää linkit index.html-tiedoston sisälle, jos merkitty alue löytyy.
    Muuten lisää ne yksinkertaisesti ensimmäisen <ul>-listan alkuun.
    """
    html = INDEX_FILE.read_text(encoding="utf-8")

    start_tag = "<!-- AI-GENERATED-POST-LIST-START -->"
    end_tag = "<!-- AI-GENERATED-POST-LIST-END -->"

    start = html.find(start_tag)
    end = html.find(end_tag)

    if start != -1 and end != -1:
        before = html[: start + len(start_tag)]
        after = html[end:]
        items = []
        for href, title in new_links:
            items.append(f'<li><a href="{href}">{title}</a></li>')
        middle = "\n          " + "\n          ".join(items) + "\n          "
        new_html = before + middle + after
        INDEX_FILE.write_text(new_html, encoding="utf-8")
        return

    # Fallback: etsi ensimmäinen <ul> ja lisää siihen alkuun
    marker = "<ul>"
    idx = html.find(marker)
    if idx != -1:
        insert_at = idx + len(marker)
        items = []
        for href, title in new_links:
            items.append(f'<li><a href="{href}">{title}</a></li>')
        middle = "\n        " + "\n        ".join(items) + "\n"
        new_html = html[:insert_at] + middle + html[insert_at:]
        INDEX_FILE.write_text(new_html, encoding="utf-8")


def main():
    POSTS_DIR.mkdir(exist_ok=True)

    identity_path = make_filename("identiteetti")
    wild_path = make_filename("villi")

    new_links: list[tuple[str, str]] = []

    # Joka päivä identiteetti
    if not post_exists(identity_path):
        body = generate_article("identiteetti")
        title = write_post(identity_path, "identiteetti", body)
        new_links.append((f"posts/{identity_path.name}", title))

    # Joka toinen päivä myös villi
    if TODAY.day % 2 == 0 and not post_exists(wild_path):
        body = generate_article("villi")
        title = write_post(wild_path, "villi", body)
        new_links.append((f"posts/{wild_path.name}", title))

    if new_links:
        update_index(new_links)
    else:
        print("Tälle päivälle ei luotu uusia postauksia.")


if __name__ == "__main__":
    main()
