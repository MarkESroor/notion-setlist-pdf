import os
import time
import unittest
from io import BytesIO
from unittest.mock import patch

from PIL import Image
from streamlit.testing.v1 import AppTest

os.environ.setdefault("NOTION_TOKEN", "test")
os.environ.setdefault("DATA_SOURCE_ID", "test-source")
import generate_setlist as exporter


SCHEMA = {"properties": {
    "Select": {"multi_select": {"options": [{"name": "10/6/26"}]}},
    "LS Convention / Events": {"multi_select": {"options": [{"name": "Evening"}]}},
}}
PAGES = [
    {"id": "song-a", "properties": {"Arabic Name": {"rich_text": [{"plain_text": "Song A"}]}}},
    {"id": "song-b", "properties": {"Arabic Name": {"rich_text": [{"plain_text": "Song B"}]}}},
]


def blocks(block_id, **kwargs):
    if block_id == "song-a":
        return {"results": [
            {"id": "a1", "type": "image", "image": {"type": "external", "external": {"url": "https://example.com/a1.png"}}},
            {"id": "nested", "type": "toggle", "has_children": True},
        ], "has_more": False}
    if block_id == "nested":
        return {"results": [
            {"id": "a2", "type": "image", "image": {"type": "file", "file": {"url": "https://example.com/a2.png"}}},
        ], "has_more": False}
    return {"results": [
        {"id": "b1", "type": "image", "image": {"type": "external", "external": {"url": "https://example.com/b1.png"}}},
    ], "has_more": False}


def download(page_id, url):
    # The extra image finishes first: completion order must not reorder the PDF.
    if url.endswith("a1.png"):
        time.sleep(0.03)
    buf = BytesIO()
    color = "red" if url.endswith("a1.png") else "blue"
    Image.new("RGB", (20, 20), color).save(buf, format="PNG")
    buf.seek(0)
    return page_id, buf


class SelectionTests(unittest.TestCase):
    def setUp(self):
        for target, kwargs in (
            (exporter.notion.data_sources, {"query": {"return_value": {"results": PAGES, "has_more": False}},
                                           "retrieve": {"return_value": SCHEMA}}),
            (exporter.notion.blocks.children, {"list": {"side_effect": blocks}}),
        ):
            for name, options in kwargs.items():
                patcher = patch.object(target, name, **options)
                patcher.start()
                self.addCleanup(patcher.stop)
        patcher = patch.object(exporter, "download_one", side_effect=download)
        self.download = patcher.start()
        self.addCleanup(patcher.stop)

    def test_default_and_extra_images_keep_page_order_and_nested_ownership(self):
        pages = exporter.prepare_setlist("10/6/26")
        default = exporter.fetch_all_images(pages)
        self.assertEqual(len(default["song-a"]), 1)
        self.assertEqual(len(default["song-b"]), 1)
        selected = exporter.fetch_all_images(pages, {"song-a": [0, 1], "song-b": []})
        self.assertEqual(list(selected), ["song-a"])
        self.assertEqual([Image.open(buf).getpixel((0, 0)) for buf in selected["song-a"]],
                         [(255, 0, 0), (0, 0, 255)])
        extra_only = exporter.fetch_all_images(pages, {"song-a": [1], "song-b": []})
        self.assertEqual(len(extra_only["song-a"]), 1)
        self.assertNotIn("nested", extra_only)

    def test_export_uses_reviewed_song_order(self):
        pages = exporter.prepare_setlist("10/6/26")
        output = BytesIO()
        with patch.object(exporter, "build_pdf", wraps=exporter.build_pdf) as build:
            exporter.export_setlist(pages[::-1], output, {"song-a": [0, 1], "song-b": [0]})
        self.assertTrue(output.getvalue().startswith(b"%PDF"))
        self.assertEqual([page["id"] for page in build.call_args.args[0]], ["song-b", "song-a"])

    def test_failed_selected_download_does_not_produce_an_incomplete_pdf(self):
        pages = exporter.prepare_setlist("10/6/26")
        self.download.side_effect = RuntimeError("download unavailable")
        output = BytesIO()
        with self.assertRaises(RuntimeError):
            exporter.export_setlist(pages, output, {"song-a": [1], "song-b": []})
        self.assertEqual(output.getvalue(), b"")

    def test_streamlit_checklist_reorder_and_download_invalidation(self):
        web = AppTest.from_file("streamlit_app.py", default_timeout=10).run()
        self.assertFalse(web.exception)
        web.selectbox[0].select("10/6/26")
        web.button[0].click().run()
        self.assertFalse(web.exception)
        self.assertEqual([box.value for box in web.checkbox], [True, False, True])
        web.checkbox[1].check().run()
        web.button(key="down_song-a").click().run()
        self.assertEqual([p["id"] for p in web.session_state["setlist"]], ["song-b", "song-a"])
        self.assertTrue(web.checkbox(key="image_song-a_1").value)
        web.button(key="generate_pdf").click().run()
        self.assertFalse(web.exception)
        self.assertEqual(len(web.get("download_button")), 1)
        web.checkbox(key="image_song-a_1").uncheck().run()
        self.assertEqual(len(web.get("download_button")), 0)
        web.button(key="generate_pdf").click().run()
        self.assertEqual(len(web.get("download_button")), 1)
        web.button(key="up_song-a").click().run()
        self.assertEqual(len(web.get("download_button")), 0)
        web.button(key="load_songs").click().run()
        self.assertEqual([box.value for box in web.checkbox], [True, False, True])
        web.selectbox[1].select("Evening").run()
        self.assertEqual(len(web.checkbox), 0)
        self.assertEqual(len(web.get("download_button")), 0)


if __name__ == "__main__":
    unittest.main()
