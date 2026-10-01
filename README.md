# Notion setlist PDF

[Open the app](https://notion-setlist-pdf.streamlit.app/).

Choose a setlist date or **LS Convention / Events**, then tap **Generate PDF** and **Download PDF**. Select both filters to include songs matching both. Each export fetches the current songs and chord images from Notion.

## Deploy

Deploy this public repository on [Streamlit Community Cloud](https://share.streamlit.io/) with `streamlit_app.py` as the entry point and Python 3.14. Connect GitHub with public-repository access only.

Add these values in Streamlit's server secrets:

```toml
NOTION_TOKEN = "your_integration_token"
DATA_SOURCE_ID = "your_notion_data_source_id"
```

The integration needs read access to the Notion data source. Its properties are `Select` and `LS Convention / Events` (both multi-select), `Order`, `Arabic Name`, `Key and capo`, and `Notes`. The exporter uses the first chord image within each song's page.

Keep real tokens, database IDs, PDFs, and Notion content out of this repository. The hosted app is public, so anyone can generate a PDF through it. Choose **This app is public and searchable** in Sharing settings for access without signing in.

## Run locally

Set `NOTION_TOKEN` and `DATA_SOURCE_ID` in a local `.env` file, then:

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Run the mocked PDF and filter check with `python test_export.py`.

The bundled Noto Naskh Arabic font is licensed under the [SIL Open Font License](fonts/OFL.txt).
