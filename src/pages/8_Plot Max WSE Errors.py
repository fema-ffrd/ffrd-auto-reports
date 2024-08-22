# -*- coding: utf-8 -*-

# Imports #####################################################################

import sys
import os
import asyncio
import streamlit as st
import warnings

warnings.filterwarnings("ignore")

from app_utilities import initialize_session

# Determine where the script is located in the Pages folder
currDir = os.path.dirname(os.path.realpath(__file__))
# Shift one level up to the src directory
srcDir = os.path.abspath(os.path.join(currDir, ".."))
# Shift another level up to the local root directory
rootDir = os.path.abspath(os.path.join(srcDir, ".."))
# Define the data directory as the assets folder within the src directory
dataDir = os.path.join(srcDir, "assets")

from hdf_utils import get_plan_cell_pts
from figures import plot_wse_errors

# layout options: wide mode, centered mode
st.set_page_config(layout="centered", page_icon="💧")
if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)
    session_data_dir = st.session_state["session_data_dir"]
    st.session_state["figure_generated"] = False
    st.title("Plot Max WSE Errors")
    st.write("Plot the maximum water surface elevation (WSE) errors.")

    st.subheader("Required Input")
    st.write("File paths from the developed HEC-RAS model")
    PLAN_HDF_PATH = st.text_input(
        "Plan HDF File",
        "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.p03.hdf",
    )
    st.subheader("Optional Input")
    st.write("Error threshold for the histogram's x-axis")
    WSE_ERROR_THRESHOLD = st.number_input("WSE Error Threshold (ft)", 0.2)
    st.write(
        "Number of bins for the histogram to plot with respect to cells within the model"
    )
    NUM_BINS = st.number_input("Number of Bins", 100)
    # Create and set an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Generate Report
    st.subheader("Generate Figure")
    st.write("Click the button below to generate the figure.")
    if st.button("Begin Figure Generation"):
        if PLAN_HDF_PATH is not None:
            # Plot the Model Mesh
            img_path = plot_wse_errors(
                PLAN_HDF_PATH,
                WSE_ERROR_THRESHOLD,
                NUM_BINS,
                session_data_dir,
                plan_index=None,
                report_document=None,
                report_keywords=None,
            )
            if os.path.exists(img_path):
                st.session_state["figure_generated"] = True
                st.success("Figure generated successfully!")
            else:
                st.error("Figure generation failed.")
                st.write(img_path)

        else:
            st.error("Please provide the required input.")

    if st.session_state["figure_generated"]:
        st.write("Download the figure:")
        st.markdown(
            f'<a href="{img_path}" download>Click here to download the figure</a>',
            unsafe_allow_html=True,
        )
        # view the figure
        st.image(img_path)