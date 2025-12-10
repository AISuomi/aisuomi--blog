from pathlib import Path
from datetime import datetime
import re

# Projektin juuri (sama taso kuin index.html)
ROOT = Path(__file__).resolve().parents[1]
INDEX_FILE = ROOT / "index.html"


def main() -> None:
    if not INDEX_FILE.exists():
        print(f"Index-tiedostoa ei löytynyt: {INDEX_FILE}")
        return

    html_text = INDEX_FILE.read_text(encoding="utf-8")

    today = datetime.utcnow().date()
    iso_date = today.isoformat()        # esim. 2025-12-10
    version = today.strftime("%Y%m%d")  # esim. 20251210

    # ---------------------------------------------
    # 1) Päivitä / lisää <meta name="last-modified">
    # ---------------------------------------------
    meta_tag = f'<meta name="last-modified" content="{iso_date}" />'

    meta_re = re.compile(r'<meta\s+name="last-modified"[^>]*>', re.IGNORECASE)
    if meta_re.search(html_text):
        # Korvaa olemassa oleva last-modified-meta
        html_text = meta_re.sub(meta_tag, html_text, count=1)
    else:
        # Jos last-modified puuttuu, lisätään se:
        # yritetään laittaa viewport-metatagin jälkeen
        viewport_re = re.compile(r'(<meta[^>]+name="viewport"[^>]*>\s*)', re.IGNORECASE)
        m = viewport_re.search(html_text)
        if m:
            insert_pos = m.end()
            html_text = html_text[:insert_pos] + "  " + meta_tag + "\n" + html_text[insert_pos:]
        else:
            # varatapa: lisätään juuri ennen </head>
            head_end_re = re.compile(r'</head>', re.IGNORECASE)
            m2 = head_end_re.search(html_text)
            if m2:
                insert_pos = m2.start()
                html_text = (
                    html_text[:insert_pos]
                    + "  " + meta_tag + "\n"
                    + html_text[insert_pos:]
                )
            else:
                # aivan varmuuden vuoksi, jos headia ei löytyisi
                html_text = meta_tag + "\n" + html_text

    # ---------------------------------------------
    # 2) Päivitä stylesheet-linkki versionumerolla
    # ---------------------------------------------
    # Etsitään rivi, jossa viitataan /assets/styles.css -tiedostoon
    # ja korvataan se muodolla href="/assets/styles.css?v=YYYYMMDD"
    def replace_styles_href(match: re.Match) -> str:
        return f'href="/assets/styles.css?v={version}"'

    html_text, count = re.subn(
        r'href="/assets/styles\.css[^"]*"',
        replace_styles_href,
        html_text,
        count=1,
    )

    if count == 0:
        print("VAROITUS: styles.css -viittausta ei löytynyt index.html:stä.")

    # ---------------------------------------------
    # 3) Kirjoita takaisin levylle
    # ---------------------------------------------
    INDEX_FILE.write_text(html_text, encoding="utf-8")
    print(f"index.html päivitetty: last-modified={iso_date}, css-versio=v{version}")


if __name__ == "__main__":
    main()
