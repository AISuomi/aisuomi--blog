import os
import json
from datetime import datetime
from pathlib import Path
from textwrap import dedent

import requests

API_KEY = os.environ["OPENAI_API_KEY"]
API_URL = "https://api.openai.com/v1/chat/completions"

ROOT = Path(__file__).resolve().parents[1]
POSTS_DIR = ROOT / "posts"
INDEX_FILE = ROOT / "index.html"

TODAY = datetime.utcnow().date()


def make_filename(kind: str) -> Path:
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
        raise RuntimeError(f"Unexpected response format: {json.dumps(data)[:500]}") from e

    return content


def generate_article(kind: str) -> str:
    if kind == "identiteetti":
        topic_instruction = (
            "suomalaisuudesta, suomen kielestä, suomalaisesta yhteiskunnasta "
            "tai kulttuurista. Vältä päivänpolitiikkaa ja pysy "
            "pohdiskelevana ja rauhallisena."
        )
    else:
        topic_instruction = (
            "vapaasta ja villistä aiheesta, joka voi liittyä arkeen, "
            "luontoon, teknologiaan, filosofiaan, tulevaisuuskuviin tai "
            "johonkin absurdin kevyesti humoristiseen näkökulmaan. "
            "Pidä teksti neutraalina ja harmittomana."
        )

    system_prompt = (
        "Olet AISuomi-blogin automaattinen kirjoituskone. Kirjoitat selkeää, "
        "rauhallista ja neutraalia suomen kieltä. Tuotat vastauksen "
        "HTML-leipätekstinä ilman <html>, <body> tai <head> -tageja."
    )

    user_prompt = f"""
Kirjoita suomenkielinen blogiteksti. Muotoile vastauksesi pelkkänä
HTML-sisältönä ilman <html>, <head> tai <body> -tageja.

Aiheen tulee olla {topic_instruction}.

Käytä rakennetta:

<h1>Otsikko</h1>
<p>Lyhyt ingressi, 1–3 virkettä.</p>

<h2>Alaotsikko</h2>
<p>Useampi kappale leipätekstiä.</p>

<h2>Toinen alaotsikko</h2>
<p>Lisää selkeää tekstisisältöä.</p>

Loppuun yksi lyhyt kappale, jossa kerrot, että teksti on
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
            Teksti on AI:n tuottamaa sisältöä ilman ihmiseditointia.
          </p>
        </div>
      </aside>
    </main>

    <footer class="site-footer">
      AISuomi – autonominen AI-blogi.
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
    html = INDEX_FILE.read_text(encoding="utf-8")
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

    new_links = []

    # --- päivittäinen identiteetti ---
    if not post_exists(identity_path):
        body = generate_article("identiteetti")
        title = write_post(identity_path, "identiteetti", body)
        new_links.append((f"posts/{identity_path.name}", title))

    # --- joka toinen päivä villi ---
    if TODAY.day % 2 == 0 and not post_exists(wild_path):
        body = generate_article("villi")
        title = write_post(wild_path, "villi", body)
        new_links.append((f"posts/{wild_path.name}", title))

    if new_links:
        update_index(new_links)
    else:
        print("Ei uusia postauksia tälle päivälle.")


if __name__ == "__main__":
    main()
