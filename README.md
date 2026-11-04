# Notion setlist PDF

[Open the app](https://notion-setlist-pdf.streamlit.app/).

Choose a setlist date or **LS Convention / Events**, then tap **Load songs**. Review the image checklists: the first image for each song is checked by default, and you can select extras or uncheck any image. Expand a preview to see the image. Use **Move up** and **Move down** to reorder the songs, then tap **Generate PDF** and **Download PDF**. Select both filters to include songs matching both. Loading songs fetches the current songs and image choices from Notion. The PDF follows your song order and includes only the checked images, in their original Notion order. Choices stay with each song as you move it. Editing choices clears the previous download until you generate again. Reloading or changing filters starts a fresh review. These choices do not edit Notion.

## Deploy

Deploy this public repository on [Streamlit Community Cloud](https://share.streamlit.io/) with `streamlit_app.py` as the entry point and Python 3.14. Connect GitHub with public-repository access only.

Add these values in Streamlit's server secrets:

```toml
NOTION_TOKEN = "your_integration_token"
DATA_SOURCE_ID = "your_notion_data_source_id"
```

The integration needs read access to the Notion data source. Its properties are `Select` and `LS Convention / Events` (both multi-select), `Order`, `Arabic Name`, `Key and capo`, and `Notes`. The review lists chord images within each song's page, including images in nested blocks.

Keep real tokens, database IDs, PDFs, and Notion content out of this repository. The hosted app is public, so anyone can generate a PDF through it. Choose **This app is public and searchable** in Sharing settings for access without signing in.

## Run locally

Set `NOTION_TOKEN` and `DATA_SOURCE_ID` in a local `.env` file, then:

```sh
python -m pip install -r requirements.txt
python -m streamlit run streamlit_app.py
```

Run the mocked PDF and filter check with `python test_export.py` and the image selection and ordering tests with `python -m unittest discover -v`.

The bundled Noto Naskh Arabic font is licensed under the [SIL Open Font License](fonts/OFL.txt).

