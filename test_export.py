import os
from io import BytesIO
from unittest.mock import patch

from streamlit.testing.v1 import AppTest

os.environ["NOTION_TOKEN"] = "test"
os.environ["DATA_SOURCE_ID"] = "test-source"
import generate_setlist


def check():
    page = {
        "id": "test-page",
        "properties": {
            "Order": {"rich_text": [{"plain_text": "1"}]},
            "Arabic Name": {"rich_text": [{"plain_text": "اختبار"}]},
            "Notes": {"rich_text": [{"plain_text": "A & B < C"}]},
        },
    }
    date_filter = {"property": "Select", "multi_select": {"contains": "10/6/26"}}
    event_filter = {"property": "LS Convention / Events", "multi_select": {"contains": "Conv 2 - Omseya"}}
    schema = {"properties": {
        "Select": {"multi_select": {"options": [{"name": "10/6/26"}]}},
        "LS Convention / Events": {"multi_select": {"options": [{"name": "Conv 2 - Omseya"}]}},
    }}
    with (
        patch.object(generate_setlist.notion.data_sources, "query", return_value={"results": [page]}) as query,
        patch.object(generate_setlist.notion.data_sources, "retrieve", return_value=schema),
        patch.object(generate_setlist.notion.blocks.children, "list", return_value={"results": []}),
    ):
        for date, event, expected in (
            ("10/6/26", None, date_filter),
            (None, "Conv 2 - Omseya", event_filter),
            ("10/6/26", "Conv 2 - Omseya", {"and": [date_filter, event_filter]}),
        ):
            output = BytesIO()
            generate_setlist.generate_setlist(date, output, event)
            assert output.getvalue().startswith(b"%PDF")
            assert query.call_args.kwargs["filter"] == expected

        web = AppTest.from_file("streamlit_app.py").run()
        assert not web.exception
        web.button[0].click().run()
        assert "Choose a setlist date or an event" in web.error[0].value
        web.selectbox[1].select("Conv 2 - Omseya")
        web.button[0].click().run()
        assert not web.exception
        assert len(web.get("download_button")) == 1
        assert query.call_args.kwargs["filter"] == event_filter
        web.selectbox[0].select("10/6/26")
        web.button[0].click().run()
        assert query.call_args.kwargs["filter"] == {"and": [date_filter, event_filter]}

        query.return_value = {"results": []}
        web.button[0].click().run()
        assert "No songs match" in web.error[0].value
    print("PDF and Streamlit filter checks passed.")


if __name__ == "__main__":
    check()
