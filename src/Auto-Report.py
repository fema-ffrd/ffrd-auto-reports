# -*- coding: utf-8 -*-

# Imports #####################################################################

import sys
import os
import zipfile
import asyncio
import numpy as np
import streamlit as st
from pathlib import Path
import warnings
import streamlit.components.v1 as components

warnings.filterwarnings("ignore")

from app_utilities import (
    compress_directory,
    write_session_parameters,
    initialize_session,
    list_s3_files,
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
# layout options: wide, centered, or full-width
st.set_page_config(layout="wide", page_icon="💧")

if __name__ == "__main__":
    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(rootDir)
    session_data_dir = st.session_state["session_data_dir"]

    st.title(
        "Welcome to the Automated Report Generator for FFRD hydraulic HEC-RAS models! 👋"
    )

    # Page Divider: Particles.js animation
    if "session_id" in st.session_state:
        components.html(particles_js, scrolling=False, height=300, width=1400)

    st.write(
        """This tool is intended to automate the process of generating reports for hydraulic FFRD models created in HEC-RAS. 
        Model geometry and plan HDF files may be uploaded locally or acquired from S3 with a provided URI. Afterwards, a multitude 
        of datasets and analyses are processed to generate a comprehensive report as a Word document. The following steps are 
        outlined for this tool to processes as it generates the report. A user may generate the entire report from the main page here, or 
        they may generate individual figures and tables from the respective pages in the sidebar. This tool is intended to standardize 
        and automated high quality report content such as figures and tables such that engineers may spend more time towards technical writing.
            """
    )

    col1, col2 = st.columns(2)
    with col1:
        st.write(
            """
                1. Processing for the HDF geometry data: model mesh, boundary, and 2D flow area datasets are acquired from the HDF file as spatially referenced geodataframes.
                2. Processing for the HDF plan data: model results, including water surface elevation (WSE) and flow are acquired from the HDF file and linked by cell ID to their geodataframe counterparts.
                3. Processing for USGS gage metadata: metadata for USGS gages within the model domain are acquired from the USGS NWIS API.
                4. Processing for the HUC04 pilot boundary: the HUC04 boundary is acquired from the NHDPlus HR dataset.
                5. Processing for the DEM dataset: a 30-meter DEM dataset is acquired from the USGS National Map.
                6. Processing for the NHD stream network: the NHDPlus HR stream network is acquired from the NHDPlus HR dataset.
                """
        )
    with col2:
        st.write(
            """
                7. Processing for the streamflow period of record: the period of record for streamflow data is acquired from the USGS NWIS API.
                8. Processing for the NLCD data: the provided NLCD dataset is used to generate a standardized report figure.
                9. Processing for the constructed model mesh: the final model mesh is acquired from the geometry HDF file.
                10. Processing for the max WSE errors: the max WSE errors are calculated for each cell within the model for quality control analytics.
                11. Processing for the WSE time to peak: the time to peak WSE is calculated for each cell within the model for quality control analytics.
                12. Processing for the calibration hydrographs: USGS gage calibration hydrographs are intersectected with model time series output at respective reference line locations.
                """
        )
    col3, col4 = st.columns(2)
    # Required inputs
    with col3:
        st.subheader("Required Input:")
        st.write("S3 bucket where the developed HEC-RAS model is stored.")
        S3_BUCKET_PATH = st.text_input(
            "S3 Bucket", "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/",

        )
        if S3_BUCKET_PATH is not None:
            try:
                available_geom_files = list_s3_files(S3_BUCKET_PATH, "g")
                available_plan_files = list_s3_files(S3_BUCKET_PATH, "p")
                # check if there is a / at the end of the bucket
                if S3_BUCKET_PATH[-1] != "/":
                    S3_BUCKET_PATH = S3_BUCKET_PATH + "/"
            except Exception as e:
                st.error(f"Error: The provided S3 bucket does not exist. Please verify the correct S3 bucket path.")
                st.stop()
        else:
            available_geom_files = []
            available_plan_files = []

        st.write("Select a single geometry file")
        GEOM_HDF_FILE = st.selectbox(
            label="Geometry HDF File",
            options=available_geom_files
        )
        st.write("Select one or more plan files")
        PLAN_HDF_FILES = st.multiselect(
            label="Plan HDF File(s)",
            options=available_plan_files,
            default=None,
            max_selections=6,
        )
        NLCD_PATH = st.text_input(
            "NLCD File",
            "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Reference/LandCover/Denton_LandCover.tif",
        )

    # Optional inputs
    with col4:
        st.subheader("Optional Input:")
        st.write(
            "The name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present."
        )
        DOMAIN_ID = st.text_input("Domain ID", None)
        st.write(
            "Filter to main streams that occur X times or more within the NHDPlus HR network"
        )
        st.write("Filter out old gages or process all available gage data.")
        GAGE_COLLECTION_METHOD = st.radio(
            "Gage Filter Method:",
            [
                "Collect all gages, old and current",
                "Only collect gages that provide current data",
            ],
            index=1,
        )
        STREAM_THRESHOLD = st.number_input("Stream Threshold", 20)
        st.write("National Inventory of Dams (NID) vertical height criteria")
        NID_DAM_HEIGHT = st.number_input("Height (ft)", 30)
        st.write("Threshold for the histogram's x-axis")
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

    with col3:
        # Generate Report
        st.subheader("Generate Report")
        st.write("Click the button below to run the report.")
        if st.button("Begin Report Generation"):
            if GEOM_HDF_FILE is not None and PLAN_HDF_FILES is not None:
                GEOM_HDF_PATH = S3_BUCKET_PATH + GEOM_HDF_FILE
                PLAN_HDF_PATHS = [S3_BUCKET_PATH + file for file in PLAN_HDF_FILES]
                try:
                    main_auto_report(
                        GEOM_HDF_PATH,
                        PLAN_HDF_PATHS,
                        NLCD_PATH,
                        report_file,
                        DOMAIN_ID,
                        GAGE_COLLECTION_METHOD,
                        STREAM_THRESHOLD,
                        WSE_ERROR_THRESHOLD,
                        NUM_BINS,
                        nid_parquet_file_path=nid_parquet_file,
                        nid_dam_height=NID_DAM_HEIGHT,
                        session_data_dir=session_data_dir,
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
