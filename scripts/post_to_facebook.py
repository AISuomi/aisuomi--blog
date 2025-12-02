import os
from pathlib import Path
import xml.etree.ElementTree as ET

import requests

ROOT = Path(__file__).resolve().parents[1]
RSS_PATH = ROOT / "rss.xml"

GRAPH_API_BASE = "https://graph.facebook.com/v21.0"


def get_latest_from_rss():
    """
    Lukee rss.xml-tiedoston ja palauttaa uusimman (title, link) tai None.
    """
    if not RSS_PATH.exists():
        print("rss.xml ei löytynyt, ei lähetetä Facebook-postausta.")
        return None

    tree = ET.parse(RSS_PATH)
    root = tree.getroot()

    channel = root.find("channel")
    if channel is None:
        print("RSS: channel-tagia ei löytynyt.")
        return None

    item = channel.find("item")
    if item is None:
        print("RSS: item-tagia ei löytynyt.")
        return None

    title_el = item.find("title")
    link_el = item.find("link")

    if title_el is None or link_el is None:
        print("RSS: title tai link puuttuu itemistä.")
        return None

    title = "".join(title_el.itertext()).strip()
    link = "".join(link_el.itertext()).strip()

    if not title or not link:
        print("RSS: tyhjä title tai link.")
        return None

    return title, link


def post_to_facebook(title: str, link: str):
    """
    Lähettää päivityksen Facebook-sivulle.
    Tarvitsee ympäristömuuttujat:
      - FB_PAGE_ID
      - FB_PAGE_ACCESS_TOKEN
    """
    page_id = os.environ.get("FB_PAGE_ID")
    access_token = os.environ.get("FB_PAGE_ACCESS_TOKEN")

    if not page_id or not access_token:
        print("FB_PAGE_ID tai FB_PAGE_ACCESS_TOKEN puuttuu, ei lähetetä postausta.")
        return

    message = (
        f"Uusi AISuomi-teksti:\n\n"
        f"{title}\n\n"
        f"Lue koko kirjoitus: {link}\n\n"
        f"AISuomi on autonominen suomenkielinen AI-blogi."
    )

    url = f"{GRAPH_API_BASE}/{page_id}/feed"

    resp = requests.post(
        url,
        data={
            "message": message,
            "link": link,
            "access_token": access_token,
        },
        timeout=30,
    )

    if resp.status_code != 200:
        print(f"Facebook API -virhe: {resp.status_code} {resp.text}")
        return

    print("Facebook-päivitys lähetetty onnistuneesti:", resp.text)


def main():
    latest = get_latest_from_rss()
    if latest is None:
        return

    title, link = latest
    post_to_facebook(title, link)


if __name__ == "__main__":
    main()
