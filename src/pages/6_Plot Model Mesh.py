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

from hdf_utils import get_model_perimeter, get_model_breaklines, get_model_cell_polygons
from figures import plot_model_mesh

# layout options: wide mode, centered mode
st.set_page_config(layout="centered", page_icon="💧")
if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)
    session_data_dir = st.session_state["session_data_dir"]
    st.session_state["figure_generated"] = False
    st.title("Plot Model Mesh")
    st.write("Plot the constructed 2D model mesh.")

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
            # Get the model geometry
            model_perimeter = get_model_perimeter(
                GEOM_HDF_PATH, DOMAIN_ID, project_to_4326=True
            )
            domain_name = model_perimeter["mesh_name"].values[0]
            model_breaklines = get_model_breaklines(GEOM_HDF_PATH, project_to_4326=True)
            model_cell_polygons = get_model_cell_polygons(
                GEOM_HDF_PATH, project_to_4326=True
            )
            # Plot the Model Mesh
            img_path = plot_model_mesh(
                model_perimeter,
                model_breaklines,
                model_cell_polygons,
                domain_name,
                session_data_dir,
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
