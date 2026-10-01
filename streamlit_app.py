from io import BytesIO
import logging

import streamlit as st

from generate_setlist import (
    DATA_SOURCE_ID, DATE_PROPERTY, EVENT_PROPERTY, NoSongsFound, generate_setlist, notion,
)

st.set_page_config(page_title="Setlist PDF", layout="centered")
st.title("Setlist PDF")
st.write("Choose a date or event to generate a fresh PDF.")

try:
    properties = notion.data_sources.retrieve(data_source_id=DATA_SOURCE_ID)["properties"]
    dates = [option["name"] for option in properties[DATE_PROPERTY]["multi_select"]["options"]]
    events = [option["name"] for option in properties[EVENT_PROPERTY]["multi_select"]["options"]]
except Exception:
    logging.exception("Could not load setlist choices")
    st.error("Could not load the setlist choices. Please refresh in a moment.")
    st.stop()

with st.form("export"):
    date = st.selectbox("Setlist date / label", dates[::-1], index=None, placeholder="Any date")
    event = st.selectbox("LS Convention / Events", events, index=None, placeholder="Any event")
    st.caption("If you select both, songs must match both.")
    submitted = st.form_submit_button("Generate PDF", type="primary", width="stretch")

if submitted:
    if not (date or event) or max(len(date or ""), len(event or "")) > 200:
        st.error("Choose a setlist date or an event from the lists.")
    else:
        try:
            # ponytail: one PDF per submission in memory; add a queue if concurrent exports exhaust memory.
            pdf = BytesIO()
            with st.spinner("Generating your PDF…"):
                generate_setlist(date, pdf, event)
            st.download_button("Download PDF", pdf.getvalue(), "setlist.pdf", "application/pdf", on_click="ignore", type="primary", width="stretch")
        except NoSongsFound as error:
            st.error(str(error))
        except Exception:
            logging.exception("PDF generation failed")
            st.error("Could not generate the PDF. Please try again in a moment.")
