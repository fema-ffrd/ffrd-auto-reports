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
from figures import plot_stream_network

# layout options: wide mode, centered mode
st.set_page_config(layout="centered", page_icon="💧")
if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)
    session_data_dir = st.session_state["session_data_dir"]
    st.session_state["figure_generated"] = False
    st.title("Plot Stream Network")
    st.write(
        "Plot the stream network (i.e., NHD streams, NID dams, and USGS gages) for the respective modeled domain."
    )

    st.subheader("Required Input")
    st.write("File paths from the developed HEC-RAS model")
    GEOM_HDF_PATH = st.text_input(
        "Geometry HDF File",
        "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.g01.hdf",
    )
    st.subheader("Optional Input")
    st.write(
        "The name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present."
    )
    DOMAIN_ID = st.text_input("Domain ID", None)
    NID_DAM_HEIGHT = st.number_input("Height (ft)", 30)
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
    st.subheader("Generate Figure")
    st.write("Click the button below to generate the figure.")
    if st.button("Begin Figure Generation"):
        if GEOM_HDF_PATH is not None:
            # Get the model perimeter and domain name
            model_perimeter = get_model_perimeter(
                GEOM_HDF_PATH, DOMAIN_ID, project_to_4326=True
            )
            domain_name = model_perimeter["mesh_name"].values[0]
            # Load the NID parquet file
            nid_parquet_file = os.path.join(dataDir, "nid_inventory.parquet")
            # Acquire all USGS gages within the model perimeter
            df_gages_usgs = get_usgs_stations(model_perimeter, "flow", None)
            if GAGE_COLLECTION_METHOD == "Only collect gages that provide current data":
                end_date = df_gages_usgs.end_date.max().strftime("%Y-%m-%d")
                df_gages_usgs = df_gages_usgs[df_gages_usgs["end_date"] == end_date]
            else:
                pass
            # Plot the stream network
            img_path = plot_stream_network(
                model_perimeter,
                df_gages_usgs,
                domain_name,
                nid_parquet_file,
                NID_DAM_HEIGHT,
                session_data_dir,
                active_streamlit=True,
                report_document=None,
                report_keywords=None,
            )
            st.session_state["figure_generated"] = True
            st.success("Figure generated successfully!")
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
        st.dataframe(
            df_gages_usgs.drop(columns=["geometry"]).sort_values(
                by="end_date", ascending=False
            )
        )
