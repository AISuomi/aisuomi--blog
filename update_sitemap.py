from pathlib import Path
from datetime import datetime
import html

# Repojuuri (sama kansio, jossa index.html ja posts/)
ROOT = Path(__file__).resolve().parent
POSTS_DIR = ROOT / "posts"
SITEMAP_FILE = ROOT / "sitemap.xml"

BASE_URL = "https://aisuomi.blog"


def get_lastmod(path: Path) -> str:
    """Palauttaa tiedoston viimeisimmän muokkauspäivän ISO-muodossa (YYYY-MM-DD)."""
    ts = path.stat().st_mtime
    return datetime.utcfromtimestamp(ts).date().isoformat()


def build_url(loc: str, lastmod: str, changefreq: str = "weekly", priority: str = "0.7") -> str:
    return f"""  <url>
    <loc>{html.escape(loc)}</loc>
    <lastmod>{lastmod}</lastmod>
    <changefreq>{changefreq}</changefreq>
    <priority>{priority}</priority>
  </url>
"""


def main():
    # Etusivu
    index_file = ROOT / "index.html"
    index_lastmod = get_lastmod(index_file) if index_file.exists() else datetime.utcnow().date().isoformat()

    urls = []

    # Etusivu prioriteetilla 1.0
    urls.append(build_url(f"{BASE_URL}/", index_lastmod, changefreq="daily", priority="1.0"))

    # Blogipostit: oletetaan, että ne ovat posts-hakemistossa .html-tiedostoja
    if POSTS_DIR.exists():
        for post in sorted(POSTS_DIR.glob("*.html")):
            loc = f"{BASE_URL}/posts/{post.name}"
            lastmod = get_lastmod(post)
            urls.append(build_url(loc, lastmod))

    # Rakennetaan sitemap.xml
    sitemap_content = f"""<?xml version="1.0" encoding="UTF-8"?>
<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">
{''.join(urls)}
</urlset>
"""

    SITEMAP_FILE.write_text(sitemap_content, encoding="utf-8")
    print(f"Generated sitemap with {len(urls)} URLs at {SITEMAP_FILE}")


if __name__ == "__main__":
    main()
