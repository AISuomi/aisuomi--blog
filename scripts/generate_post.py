import os
from datetime import datetime
from pathlib import Path
from textwrap import dedent

from openai import OpenAI

# API-avain haetaan GitHub-sekretistä
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
            "suomalaisuudesta, suomen kielestä, kulttuurista, "
            "identiteetistä tai Suomesta yhteiskuntana."
        )
    else:
        topic_instruction = (
            "vapaasta ja yllättävästä aiheesta, joka ei riko lakeja "
            "eikä sisällä vihaa, syrjintää, väkivaltaa tai muuta "
            "haitallista sisältöä."
        )

    prompt = f"""
Kirjoita suomenkielinen blogiteksti muodossa valmis HTML-sisältö
(ilman <html>, <head> tai <body> -elementtejä, vain otsikot ja
leipäteksti). Aiheen tulee olla {topic_instruction}

Rakenne:

<h1>Otsikko</h1>
<p>lyhyt ingressi</p>
<h2>alaotsikot</h2>
<p>leipätekstiä</p>

Lopussa lyhyt kappale, jossa muistutus, että teksti on
tekoälyn kirjoittama kokeellinen sisältö, eikä sitä ole
ihminen editoinut.
"""

    resp = client.responses.create(
        model="gpt-4.1-mini",
        input=prompt,
    )

    # Poimitaan tekstisisältö
    parts = []
    for out in resp.output:
        if out.type == "message":
            for c in out.message.content:
                if c.type == "output_text":
                    parts.append(c.text.value)
    if not parts:
        raise RuntimeError("Ei saatu vastausta mallilta.")
    return "".join(parts)


def write_post(path: Path, kind: str, html_body: str) -> str:
    # Nappaa otsikon <h1> tageista
    title = f"AISuomi – {kind} {TODAY.isoformat()}"
    start = html_body.find("<h1>")
    end = html_body.find("</h1>")
    if start != -1 and end != -1:
        title = (
            html_body[start + 4 : end]
            .strip()
            .replace("\n", " ")
        )

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
    </nav>

    <main class="layout">
      <section class="main-column">
      {html_body}
      </section>
      <aside class="sidebar">
        <div class="card">
          <h2>Huomio</h2>
          <p class="muted">
            Tämä kirjoitus on tekoälyn tuottama. Sisältöä ei ole
            ihminen editoinut ennen julkaisua.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen AI-blogikokeilu.
      | <a href="../privacy.html">Tietosuoja</a>
      | <a href="../cookies.html">Evästeet</a>
    </footer>
  </body>
</html>
"""
    path.write_text(dedent(document), encoding="utf-8")
    return title


def update_index(new_links: list[tuple[str, str]]):
    """Lisää linkit index.html-tiedoston sisälle kommenttien väliin."""
    html = INDEX_FILE.read_text(encoding="utf-8")

    start_tag = "<!-- AI-GENERATED-POST-LIST-START -->"
    end_tag = "<!-- AI-GENERATED-POST-LIST-END -->"

    start = html.find(start_tag)
    end = html.find(end_tag)

    if start == -1 or end == -1:
        print("Varoitus: placeholder-kommentteja ei löytynyt index.html:stä.")
        return

    before = html[: start + len(start_tag)]
    after = html[end:]

    # Rakennetaan <li>-linkit
    items = []
    for href, title in new_links:
        items.append(f'<li><a href="{href}">{title}</a></li>')

    middle = "\n          " + "\n          ".join(items) + "\n          "

    new_html = before + middle + after
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

