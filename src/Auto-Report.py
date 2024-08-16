# -*- coding: utf-8 -*-

# Imports #####################################################################

import sys
import os
import zipfile
import asyncio
import streamlit as st
from docx import Document
from pathlib import Path
import warnings
import streamlit.components.v1 as components

warnings.filterwarnings("ignore")

from app_utilities import (
    compress_directory,
    write_session_parameters,
    initialize_session,
    particles_js,
)

# Determine where the script is located
currDir = os.path.dirname(os.path.realpath(__file__))
# Shift one level up to the local root directory
rootDir = os.path.abspath(os.path.join(currDir, ".."))
# Define the data directory
dataDir = os.path.join(rootDir, "data")
# Add the src directory to sys.path
srcDir = os.path.join(rootDir, "src", "auto_report")
sys.path.append(srcDir)

from auto_report import main_auto_report

# Main Page ###################################################################

st.set_page_config(layout="wide", page_icon="💧")

if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)

    st.title(
        "Welcome to the Automated Report Generator for FFRD hydraulic HEC-RAS models! 👋"
    )

    session_data_dir = st.session_state["session_data_dir"]
    col1, col2, col3 = st.columns(3)

    # Intro, and required inputs
    with col1:
        st.subheader("Introduction:")
        st.write(
            """
              This tool is intended to automate the process of generating reports for hydraulic FFRD models created in HEC-RAS.
              
              Model geometry and plan HDF files may be uploaded locally or acquired from S3 with a provided URI. Afterwards, a multitude
               of datasets and analyses are processed to generate a comprehensive report as a Word document.
              The following steps are outlined for this tool to processes as it generates the report:"""
        )
        st.markdown(
            """
                  1. Processing for the HDF geometry data
                  2. Processing for the HDF plan data
                  3. Processing for USGS gage metadata
                  4. Processing for the HUC04 pilot boundary
                  5. Processing for the DEM dataset
                  6. Processing for the NHD stream network
                  7. Processing for the streamflow period of record
                  8. Processing for the NLCD data
                  9. Processing for the constructed model mesh
                  10. Processing for the max WSE errors
                  11. Processing for the WSE time to peak
                  12. Processing for the calibration hydrographs
                  """
        )

        st.subheader("Required Input:")
        st.write("File paths from the developed HEC-RAS model")
        selected_file_source = st.radio("Select the file source:", ("Local", "S3"))
        if selected_file_source == "Local":
            GEOM_HDF_PATH = st.file_uploader(
                "Geometry HDF File", type=["hdf"], accept_multiple_files=False
            )
            PLAN_HDF_PATH = st.file_uploader(
                "Plan HDF File", type=["hdf"], accept_multiple_files=False
            )
            NLCD_PATH = st.file_uploader(
                "NLCD File", type=["tif"], accept_multiple_files=False
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
            NLCD_PATH = st.text_input(
                "NLCD File",
                "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Reference/LandCover/Denton_LandCover.tif",
            )

    # Particles.js animation
    with col2:
        if "session_id" in st.session_state:
            components.html(particles_js, scrolling=False, height=1000, width=500)

    # Optional inputs
    with col3:
        st.subheader("Optional Input:")
        st.write(
            "The name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present."
        )
        DOMAIN_ID = st.text_input("Domain ID", None)
        st.write(
            "Filter to main streams that occur X times or more within the NHDPlus HR network"
        )
        STREAM_THRESHOLD = st.number_input("Stream Threshold", 20)
        st.write("National Inventory of Dams (NID) vertical height criteria")
        NID_DAM_HEIGHT = st.number_input("Height (ft)", 30)
        st.write("Spatial resolution of the NLCD data")
        WSE_ERROR_THRESHOLD = st.number_input("WSE Error Threshold (ft)", 0.2)
        st.write(
            "Number of bins for the histogram to plot with respect to cells within the model"
        )
        NUM_BINS = st.number_input("Number of Bins", 100)

    # Assets
    report_file = os.path.join(
        currDir, "assets", "FFRD-RAS-Report-Automated-Template.docx"
    )
    nid_parquet_file = os.path.join(currDir, "assets", "nid_inventory.parquet")

    # Create and set an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    col4, col5, col6 = st.columns(3)

    with col4:
        st.subheader("Generate Report")
        st.write("Click the button below to run the report.")
        if st.button("Begin Report Generation"):
            if GEOM_HDF_PATH is not None and PLAN_HDF_PATH is not None:
                try:
                    main_auto_report(
                        GEOM_HDF_PATH,
                        PLAN_HDF_PATH,
                        NLCD_PATH,
                        report_file,
                        DOMAIN_ID,
                        STREAM_THRESHOLD,
                        WSE_ERROR_THRESHOLD,
                        NUM_BINS,
                        nid_parquet_file,
                        NID_DAM_HEIGHT,
                        session_data_dir,
                        active_streamlit=True,
                    )
                    st.session_state["data_acquired"] = True
                    st.success("Report successfully generated!")
                except Exception as e:
                    st.error(f"Error: {e}")
                    st.stop()
            else:
                st.error(
                    "Please provide the required inputs before generating the report."
                )

        if st.session_state["data_acquired"]:
            # Provide a download link to the generated report
            st.subheader("Download Report")

            # give user option to download data
            if st.session_state["request_zip"] is True:
                request_zip_default = True
            else:
                request_zip_default = False

            request_zip = st.checkbox(
                "I want to download the data as a zip file", value=request_zip_default
            )

            if request_zip:
                st.session_state["request_zip"] = True

            if request_zip == True:
                # write session data before creating zip
                write_session_parameters(st.session_state)

                # create the zip file if it doesn't exists
                parent_dir = Path(session_data_dir).parent
                zip_name = f"{Path(session_data_dir).name}.zip"
                output_zip_file = os.path.join(parent_dir, zip_name)
                st.session_state["session_zip"] = output_zip_file
                print(f"zip file: {output_zip_file}")
                session_zip = compress_directory(
                    st.session_state["session_data_dir"], output_zip_file
                )

                # for unknown reasons, might have to create zip (might just be a development aberation)
                if not os.path.exists(session_zip):
                    with zipfile.ZipFile(session_zip, "w") as file:
                        pass

                with open(session_zip, "rb") as fp:
                    # with open(output_zip_file, "rb") as fp:
                    btn = st.download_button(
                        label="Download ZIP file",
                        data=fp,
                        file_name=zip_name,
                        mime="application/zip",
                    )
