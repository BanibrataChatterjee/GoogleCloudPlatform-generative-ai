"""This module is the page for Exposure Check Search feature"""

# pylint: disable=line-too-long,import-error

from database import compliance_query, display_spanner_query
from itables.streamlit import interactive_table
import streamlit as st

st.set_page_config(
    layout="wide",
    page_title="FinVest Advisor",
    page_icon="https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/small-logo.png",
    initial_sidebar_state="expanded",
)

st.logo(
    "https://storage.googleapis.com/github-repo/generative-ai/sample-apps/finance-advisor-spanner/images/investments.png"
)


def compliance_search() -> None:
    """This function implements Compliance Check Graph feature"""
    st.header("FinVest Fund Advisor")
    st.subheader("Exposure Check")

    st.columns([0.25, 0.25, 0.20, 0.10])
    classes = ["display", "compact", "cell-border", "stripe"]
    buttons = ["pageLength", "csvHtml5", "excelHtml5", "colvis"]
    style = "table-layout:auto;width:auto;margin:auto;caption-side:bottom"
    it_args = dict(
        classes=classes,
        style=style,
    )

    if buttons:
        it_args["buttons"] = buttons

    query_params = []
    query_params.append(sectorOption)
    query_params.append(exposurePercentage)
    with st.spinner("Querying Spanner..."):
        return_vals = compliance_query(query_params)
        spanner_query = return_vals.get("query")
        data = return_vals.get("data")
        display_spanner_query(str(spanner_query))

    interactive_table(data, caption="", **it_args)


with st.sidebar:
    with st.form("Compliance Search"):
        st.subheader("Search Criteria")
        sectorOption = st.selectbox(
            "Which sector would you want to focus on?",
            ("Technology", "Pharma", "Semiconductors"),
            index=None,
            placeholder="Select sector ...",
        )
        exposurePercentage = st.select_slider(
            "How much exposure to this sector would you prefer",
            options=["10%", "20%", "30%", "40%", "50%", "60%", "70%"],
        )
        exposurePercentage = exposurePercentage[:2]
        compliance_search_submitted = st.form_submit_button("Submit")
if compliance_search_submitted:
    compliance_search()
