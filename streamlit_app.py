from io import BytesIO
import logging

import streamlit as st

from generate_setlist import (
    DATA_SOURCE_ID, DATE_PROPERTY, EVENT_PROPERTY, NoSongsFound,
    export_setlist, get_song_name, notion, prepare_setlist,
)


def invalidate_pdf():
    st.session_state.pop("pdf_bytes", None)


@st.cache_data(ttl=60, show_spinner=False)
def load_choices():
    properties = notion.data_sources.retrieve(data_source_id=DATA_SOURCE_ID)["properties"]
    dates = [option["name"] for option in properties[DATE_PROPERTY]["multi_select"]["options"]]
    events = [option["name"] for option in properties[EVENT_PROPERTY]["multi_select"]["options"]]
    return dates, events


def move_song(page_id):
    pages = st.session_state["setlist"]
    index = next(i for i, page in enumerate(pages) if page["id"] == page_id)
    destination = st.session_state[f"position_{page_id}"] - 1
    if destination != index:
        pages.insert(destination, pages.pop(index))
        invalidate_pdf()
    for position, page in enumerate(pages, 1):
        st.session_state[f"position_{page['id']}"] = position


st.set_page_config(page_title="Setlist PDF", layout="centered")
st.title("Setlist PDF")
st.write("Choose a date or event, then review the songs and chord images for your PDF. Ma7abba God Bless")

try:
    dates, events = load_choices()
except Exception:
    logging.exception("Could not load setlist choices")
    st.error("Could not load the setlist choices. Please refresh in a moment.")
    st.stop()

date = st.selectbox("Setlist date / label", dates[::-1], index=None, placeholder="Any date")
event = st.selectbox("LS Convention / Events", events, index=None, placeholder="Any event")
st.caption("If you select both, songs must match both.")

filters = (date, event)
if st.session_state.get("loaded_filters") != filters:
    st.session_state.pop("setlist", None)
    invalidate_pdf()

if st.button("Load songs", key="load_songs", type="primary", width="stretch"):
    st.session_state.pop("setlist", None)
    invalidate_pdf()
    if not (date or event) or max(len(date or ""), len(event or "")) > 200:
        st.error("Choose a setlist date or an event from the lists.")
    else:
        try:
            with st.spinner("Loading songs and image choices…"):
                pages = prepare_setlist(date, event)
            st.session_state["setlist"] = pages
            st.session_state["loaded_filters"] = filters
            for key in list(st.session_state):
                if key.startswith(("image_", "position_")):
                    del st.session_state[key]
        except NoSongsFound as error:
            st.error(str(error))
        except Exception:
            logging.exception("Could not load songs")
            st.error("Could not load the songs. Please try again in a moment.")

pages = st.session_state.get("setlist")
if pages:
    st.subheader("Review your setlist")
    st.caption("Type a song position to change its order. The first image is checked by default; select any extras you want.")
    for position, page in enumerate(pages):
        page_id = page["id"]
        name = get_song_name(page)
        with st.container(border=True):
            st.write(f"{position + 1}. {name}")
            st.session_state.setdefault(f"position_{page_id}", position + 1)
            st.number_input("Song position", min_value=1, max_value=len(pages),
                            step=1, key=f"position_{page_id}",
                            on_change=move_song, args=(page_id,))
            if not page["image_urls"]:
                st.caption("No chord images found. The song's title and notes will still be included.")
            for index, url in enumerate(page["image_urls"]):
                st.checkbox(f"Include image {index + 1}", value=index == 0,
                            key=f"image_{page_id}_{index}", on_change=invalidate_pdf)
                with st.expander(f"Preview image {index + 1}"):
                    st.image(url, width="stretch")

    if st.button("Generate PDF", key="generate_pdf", type="primary", width="stretch"):
        invalidate_pdf()
        selected_images = {
            page["id"]: [index for index in range(len(page["image_urls"]))
                         if st.session_state[f"image_{page['id']}_{index}"]]
            for page in pages
        }
        try:
            # ponytail: one PDF per session in memory; add a queue if exports exhaust memory.
            pdf = BytesIO()
            with st.spinner("Generating your PDF…"):
                export_setlist(pages, pdf, selected_images)
            st.session_state["pdf_bytes"] = pdf.getvalue()
        except Exception:
            logging.exception("PDF generation failed")
            st.error("Could not generate the PDF. Please try again in a moment.")

    if "pdf_bytes" in st.session_state:
        st.download_button("Download PDF", st.session_state["pdf_bytes"], "setlist.pdf",
                           "application/pdf", on_click="ignore", type="primary", width="stretch")

