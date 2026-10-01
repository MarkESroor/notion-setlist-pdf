from notion_client import Client, iterate_paginated_api
from dotenv import load_dotenv
import os
import requests
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Image, Spacer, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.units import cm
from io import BytesIO
from concurrent.futures import ThreadPoolExecutor, as_completed
import arabic_reshaper
from bidi.algorithm import get_display
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont
import argparse
from xml.sax.saxutils import escape


BASE_DIR = os.path.dirname(os.path.abspath(__file__))

FONT_PATH = os.path.join(
    BASE_DIR,
    "fonts",
    "NotoNaskhArabic-VariableFont_wght.ttf"
)

pdfmetrics.registerFont(TTFont("NotoNaskhArabic", FONT_PATH))

load_dotenv()

NOTION_TOKEN = os.getenv("NOTION_TOKEN")
if not NOTION_TOKEN:
    raise RuntimeError("Missing NOTION_TOKEN environment variable.")

notion = Client(auth=NOTION_TOKEN)

DATA_SOURCE_ID = os.getenv("DATA_SOURCE_ID")
if not DATA_SOURCE_ID:
    raise RuntimeError("Missing DATA_SOURCE_ID environment variable.")
DATE_PROPERTY = "Select"
EVENT_PROPERTY = "LS Convention / Events"


class NoSongsFound(ValueError):
    pass


def fix_arabic(text):
    if not text:
        return ""
    reshaped = arabic_reshaper.reshape(text)
    return get_display(reshaped)


def get_order(page):
    try:
        return int(page["properties"]["Order"]["rich_text"][0]["plain_text"])
    except Exception:
        return 9999


def get_text(prop):
    try:
        return prop["rich_text"][0]["plain_text"]
    except Exception:
        return ""


def get_image_urls_from_page(page_id, depth=0, max_depth=3):
    if depth > max_depth:
        return []

    urls = []

    try:
        for block in iterate_paginated_api(notion.blocks.children.list, block_id=page_id):
            btype = block["type"]

            if btype == "image":
                image = block["image"]

                if image["type"] == "file":
                    urls.append((page_id, image["file"]["url"]))
                elif image["type"] == "external":
                    urls.append((page_id, image["external"]["url"]))

            if block.get("has_children") and btype not in ("image", "file", "pdf"):
                urls.extend(get_image_urls_from_page(block["id"], depth + 1, max_depth))

    except Exception as e:
        print(f"  [Block error: {e}]")

    return urls


def download_one(page_id, url):
    r = requests.get(url, timeout=30, stream=True)
    r.raise_for_status()

    buf = BytesIO()

    for chunk in r.iter_content(8192):
        if chunk:
            buf.write(chunk)

    buf.seek(0)
    return page_id, buf


def fetch_all_images(pages):
    print("Fetching block lists...")

    all_tuples = []

    for page in pages:
        urls = get_image_urls_from_page(page["id"])

        if urls:
            all_tuples.append(urls[0])  # first image only

    print(f"Downloading {len(all_tuples)} images in parallel...")

    results = {}

    with ThreadPoolExecutor(max_workers=8) as executor:
        futures = {
            executor.submit(download_one, pid, url): pid
            for pid, url in all_tuples
        }

        for i, f in enumerate(as_completed(futures), 1):
            try:
                page_id, buf = f.result()
                results.setdefault(page_id, []).append(buf)
                print(f"  [{i}/{len(all_tuples)}] downloaded")
            except Exception as e:
                print(f"  [Download failed: {e}]")

    return results


def build_pdf(pages, image_cache, output_path="setlist.pdf"):
    doc = SimpleDocTemplate(
        output_path,
        pagesize=A4,
        rightMargin=1 * cm,
        leftMargin=1 * cm,
        topMargin=1 * cm,
        bottomMargin=1 * cm,
    )

    story = []
    styles = getSampleStyleSheet()

    styles["Title"].fontName = "NotoNaskhArabic"
    styles["Title"].alignment = 2

    styles["Normal"].fontName = "NotoNaskhArabic"

    for page in pages:
        props = page["properties"]

        arabic_name = get_text(props.get("Arabic Name", {}))
        key_and_capo = get_text(props.get("Key and capo", {}))
        notes = get_text(props.get("Notes", {}))

        if arabic_name:
            story.append(Paragraph(f"<b>{escape(fix_arabic(arabic_name))}</b>", styles["Title"]))

        if key_and_capo:
            story.append(Paragraph(f"Key / Capo: {escape(key_and_capo)}", styles["Normal"]))

        if notes:
            story.append(Paragraph(f"Notes: {escape(fix_arabic(notes))}", styles["Normal"]))

        story.append(Spacer(1, 0.3 * cm))

        images = image_cache.get(page["id"], [])

        if not images:
            story.append(Paragraph("[No chord image found]", styles["Normal"]))
        else:
            for buf in images:
                try:
                    img = Image(buf, width=18 * cm, height=24 * cm, kind="proportional")
                    story.append(img)
                    story.append(Spacer(1, 0.5 * cm))
                except Exception as e:
                    story.append(Paragraph(f"[Image error: {e}]", styles["Normal"]))

        story.append(Spacer(1, 1 * cm))

    doc.build(story)
    print(f"\nDone! PDF saved to {output_path}")


def generate_setlist(date_filter, output_path, event_filter=None):
    filters = [
        {"property": name, "multi_select": {"contains": value.strip()}}
        for name, value in ((DATE_PROPERTY, date_filter), (EVENT_PROPERTY, event_filter))
        if value and value.strip()
    ]
    if not filters:
        raise ValueError("Choose a setlist date or an event.")

    print("Querying setlist...")
    pages = list(iterate_paginated_api(
        notion.data_sources.query,
        data_source_id=DATA_SOURCE_ID,
        filter=filters[0] if len(filters) == 1 else {"and": filters},
    ))
    pages.sort(key=get_order)

    print(f"Found {len(pages)} songs")

    if not pages:
        raise NoSongsFound("No songs match those filters. Try a different date or event.")

    image_cache = fetch_all_images(pages)
    build_pdf(pages, image_cache, output_path=output_path)


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--date", help="Setlist date / label, e.g. 10/6/26")
    parser.add_argument("--event", help="LS Convention / Events label")
    parser.add_argument("--output", default="setlist.pdf")

    args = parser.parse_args()

    try:
        generate_setlist(args.date, args.output, args.event)
    except ValueError as error:
        parser.error(str(error))
