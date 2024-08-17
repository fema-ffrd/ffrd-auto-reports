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

sys.path.append(srcDir)

from hdf_utils import get_model_perimeter
from hy_river import get_usgs_stations
from figures import plot_hydrographs

# layout options: wide mode, centered mode
st.set_page_config(layout="centered", page_icon="💧")
if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)
    session_data_dir = st.session_state["session_data_dir"]
    st.session_state["figure_generated"] = False
    st.title("Plot Hydrographs")
    st.write(
        "Plot each calibrated gage hydrograph within the respective modeled domain."
    )

    st.subheader("Required Input")
    st.write("File paths from the developed HEC-RAS model")
    selected_file_source = st.radio("Select the file source:", ("Local", "S3"))
    if selected_file_source == "Local":
        GEOM_HDF_PATH = st.file_uploader(
            "Geometry HDF File", type=["hdf"], accept_multiple_files=False
        )
        PLAN_HDF_PATH = st.file_uploader(
            "Plan HDF File", type=["hdf"], accept_multiple_files=False
        )
    else:
        GEOM_HDF_PATH = st.text_input(
            "Geometry HDF File",
            "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.g01.hdf",
        )
        PLAN_HDF_PATH = st.text_input(
            "Plan HDF File",
            "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.p03.hdf",
        )
    st.subheader("Optional Input")
    st.write(
        "The name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present."
    )
    DOMAIN_ID = st.text_input("Domain ID", None)
    st.write("Filter out old gages or process all available gage data.")
    GAGE_COLLECTION_METHOD = st.radio(
        "Gage Filter Method:",
        [
            "Collect all gages, old and current",
            "Only collect gages that provide current data",
        ],
        index=1,
    )
    # Create and set an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    # Generate Report
    st.subheader("Generate Figure(s)")
    st.write("Click the button below to generate the figure(s).")
    if st.button("Begin Figure Generation"):
        if GEOM_HDF_PATH is not None and PLAN_HDF_PATH is not None:
            # Get the model perimeter and domain name
            model_perimeter = get_model_perimeter(
                GEOM_HDF_PATH, DOMAIN_ID, project_to_4326=True
            )
            domain_name = model_perimeter["mesh_name"].values[0]
            # Acquire all USGS gages within the model perimeter
            df_gages_usgs = get_usgs_stations(model_perimeter, None)
            if GAGE_COLLECTION_METHOD == "Only collect gages that provide current data":
                end_date = df_gages_usgs.end_date.max().strftime("%Y-%m-%d")
                df_gages_usgs = df_gages_usgs[df_gages_usgs["end_date"] == end_date]
            else:
                pass
            # Plot the calibrated gage hydrographs
            img_path_list = plot_hydrographs(
                PLAN_HDF_PATH,
                df_gages_usgs,
                domain_name,
                session_data_dir,
                report_document=None,
                report_keywords=None,
            )
            st.session_state["figure_generated"] = True
            if img_path_list is None:
                st.error("No gages were found within the model perimeter.")
            else:
                st.success("Figure(s) generated successfully!")
        else:
            st.error("Please provide the required input.")

    if st.session_state["figure_generated"]:
        if img_path_list is not None:
            for img_path in img_path_list:
                st.write("Download the figure:")
                st.markdown(
                    f'<a href="{img_path}" download>Click here to download the figure</a>',
                    unsafe_allow_html=True,
                )
                # view the figure
                st.image(img_path)
