# -*- coding: utf-8 -*-

# Imports #####################################################################

import sys
import os
import zipfile
import asyncio
import streamlit as st
from pathlib import Path
import warnings
warnings.filterwarnings("ignore")

from app_utilities import compress_directory, write_session_parameters, initialize_session

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

# Functions ###################################################################

if __name__ == "__main__":

    # setup a session data when app is first opened or browser reset
    if "session_id" not in st.session_state:
        initialize_session(dataDir)

    session_id = st.session_state["session_id"].strftime("%Y_%b_%d_%H_%M_%S_%f")

    st.set_page_config(layout="wide", page_icon=":globe_with_meridians:")

    # Title
    st.title("Welcome to the Automated Report Generator for FFRD hydraulic HEC-RAS models! 👋")
    st.write("""
             This tool is intended to automate the process of generating reports for hydraulic FFRD models created in HEC-RAS.
             
             Please reach out to us if you have any questions or need assistance with your projects.""")
    
    # Begin User Input
    st.subheader("Required:")
    st.write("file paths from the developed HEC-RAS model")
    GEOM_HDF_PATH = st.text_input("Geometry HDF File", "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/EaFT_Lavon.g06.hdf")
    PLAN_HDF_PATH = st.text_input("Plan HDF File", "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/EaFT_Lavon.p01.hdf")
    st.subheader("Optional:")
    st.write("the name of the 2D flow area within the HEC-RAS model. Only necessary if more than one 2D flow area is present.")
    DOMAIN_ID = st.text_input("Domain ID", None)
    st.write("filter to main streams that occur X times or more within the NHDPlus HR network")
    STREAM_THRESHOLD = st.number_input("Stream Threshold", 20)
    st.write("Spatial resolution of the NLCD data")
    NLCD_RES = st.number_input("NLCD Resolution", 30)
    st.write("NLCD Year")
    NLCD_YR = st.number_input("NLCD Year", 2019)
    st.write("Threshold for the histogram's x-axis for the water surface elevation error")
    WSE_ERROR_THRESHOLD = st.number_input("WSE Error Threshold", 0.2)
    st.write("Number of bins for the histogram to plot with respect to cells within the model")
    NUM_BINS = st.number_input("Number of Bins", 100)

    # Create and set an event loop
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)

    if st.button("Run Report"):
        try:
            main_auto_report(
                GEOM_HDF_PATH,
                PLAN_HDF_PATH,
                DOMAIN_ID,
                STREAM_THRESHOLD,
                NLCD_RES,
                NLCD_YR,
                WSE_ERROR_THRESHOLD,
                NUM_BINS,
                rootDir,
                session_id
            )
            st.session_state["data_acquired"] = True
            st.success("Report successfully generated!")
        except Exception as e:
            st.error(f"Error: {e}")
            st.stop()

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
            session_directory = st.session_state["session_data_dir"]
            parent_dir = Path(session_directory).parent
            zip_name = f"{Path(session_directory).name}.zip"
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

