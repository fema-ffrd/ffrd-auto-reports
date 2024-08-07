# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import shutil
import asyncio
import nest_asyncio
import geopandas as gpd
from docx import Document
import streamlit as st

from hy_river import get_usgs_stations
from hdf_utils import get_hdf_geom, get_hdf_plan

from figures import (
    plot_pilot_study_area,
    plot_dem,
    plot_stream_network,
    plot_streamflow_summary,
    plot_nlcd,
    plot_model_mesh,
    plot_wse_errors,
    plot_wse_ttp,
    plot_hydrographs,
)

# TODO


def model_unit_name():
    return


def report_date():
    return


def report_header():
    return


def report_footer():
    return


def Section01_GageSummary_Txt():
    return


def Section02_Table01():
    return


def Section03_Table03():
    return


# # Apply the nest_asyncio patch
# nest_asyncio.apply()
"""
By design asyncio does not allow its event loop to be nested.
This presents a practical problem: When in an environment where
the event loop is already running it’s impossible to run tasks
and wait for the result. Trying to do so will give the error
“RuntimeError: This event loop is already running”. The issue pops 
up in various environments, such as web servers, GUI applications 
and in Jupyter notebooks.
"""

# Functions ###################################################################


def clean_report_folder():
    """
    Clean the report folder by deleting all files except for the Template
    Afterwards make a copy of the Template to and rename it to FFRD-RAS-Report-Automated-Updated.docx

    Returns
    -------
    document : Docx Document
        A copy of the Template document
    """
    directory = r"/workspaces/ffrd-auto-reports/data/2_production/report"
    source_file = os.path.join(directory, "FFRD-RAS-Report-Automated-Template.docx")
    # Delete all other files within the report folder except for the Template
    for file in os.listdir(directory):
        if file != "FFRD-RAS-Report-Automated-Template.docx":
            os.remove(os.path.join(directory, file))

    # ensure the destination directory exists
    destination_file = os.path.join(directory, "FFRD-RAS-Report-Automated-Updated.docx")
    destination_dir = os.path.dirname(destination_file)
    os.makedirs(destination_dir, exist_ok=True)

    # copy the file
    shutil.copyfile(source_file, destination_file)

    # Open the document
    document = Document(destination_file)
    return document


async def auto_report(
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    report_document: Document,
    input_domain_id: str,
    stream_frequency_threshold: int,
    nlcd_resolution: int,
    nlcd_year: int,
    wse_error_threshold: float,
    num_bins: int,
    nid_parquet_file_path: str,
    nid_dam_height: int,
    session_data_dir: str,
    active_streamlit: bool,
):
    """
    Generate the figures for the report

    Parameters
    ----------
    hdf_geom_file_path : str
        The path to the geometry HDF file
    hdf_plan_file_path : str
        The path to the plan HDF file
    report_document : Docx Document
        The document to modify
    input_domain_id : str
        Optional input for the domain ID
    stream_frequency_threshold : int
        The threshold frequency for the stream names. Ex: filter to streams whose
        name occurs 20 times or more within the NHDPlus HR network.
    nlcd_resolution : int
        The resolution of the NLCD data to retrieve in meters (30)
    nlcd_year : int
        The year of the NLCD data to retrieve (2019)
    wse_error_threshold : float
        The threshold for the WSE error
    num_bins : int
        The number of bins for the histogram
    nid_parquet_file_path : str
        The path to the parquet file containing the backup NID data
    nid_dam_height : int
        The dam height threshold for the NID inventory
    session_data_dir : str
        The session data directory path
    active_streamlit : bool
        If true, print statements will be displayed in the Streamlit app
        If false, print statements will be displayed in the terminal

    Returns
    -------
    None
    """

    # Get the HDF data
    if active_streamlit:
        st.write("Step 1 / 12")
        st.write("Processing for the HDF geometry data...")
    else:
        print("Step 1 / 12")
        print("Processing for the HDF geometry data...")
    (
        perimeter,
        geojson_obj,
        domain_id,
        cell_polygons,
        breaklines,
    ) = get_hdf_geom(hdf_geom_file_path, input_domain_id)

    # Get the HDF plan data
    if active_streamlit:
        st.write("Step 2 / 12")
        st.write("Processing for the HDF plan data...")
    else:
        print("Step 2 / 12")
        print("Processing for the HDF plan data...")
    cell_points, dates = get_hdf_plan(hdf_plan_file_path, input_domain_id)

    # Collect all USGS gages located within the perimeter boundary
    if active_streamlit:
        st.write("Step 3 / 12")
        st.write("Processing for USGS gage metadata...")
    else:
        print("Step 3 / 12")
        print("Processing for USGS gage metadata...")
    try:
        df_gages_usgs = get_usgs_stations(perimeter, dates)
        st.success("Complete!")
    except Exception as e:
        """
        403 Client Error: You are being blocked by the USGS API due to too many requests.
        Blocking access to a service should only occur if the USGS believes that your use
        of the service is so excessive that it is seriously impacting others using the service.

        To get unblocked, send us the URL you are using along with the IP using this form.
        We may require changes to your query and frequency of use in order to give you access
        to the service again.

        Contact USGS: https://answers.usgs.gov/
        """
        st.error(f"Error processing the USGS gages dataset: {e}")
        # Create an empty geodataframe if the gages dataset fails to process
        df_gages_usgs = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )

    """
    Begin generating the report figures. Each figure will be generated in a separate function.
    If that function fails, the error will be caught but the report will continue to generate 
    the remaining figures starting with the proceeding figure.
    """

    # Generate the Section 01 Figure 01
    if active_streamlit:
        st.write("Step 4 / 12")
        st.write("Processing for the HUC04 pilot boundary...")
    else:
        print("Step 4 / 12")
        print("Processing for the HUC04 pilot boundary...")
    try:
        report_document = plot_pilot_study_area(
            report_document,
            perimeter,
            stream_frequency_threshold,
            domain_id,
            session_data_dir,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Section 01 Figure 02
    if active_streamlit:
        st.write("Step 5 / 12")
        st.write("Processing for the DEM dataset...")
    else:
        print("Step 5 / 12")
        print("Processing for the DEM dataset...")
    try:
        report_document = plot_dem(
            report_document, perimeter, domain_id, session_data_dir
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Section 04 Figure 03
    if active_streamlit:
        st.write("Step 6 / 12")
        st.write("Processing for the NHD stream network...")
    else:
        print("Step 6 / 12")
        print("Processing for the NHD stream network...")
    try:
        report_document = plot_stream_network(
            report_document,
            perimeter,
            df_gages_usgs,
            domain_id,
            nid_parquet_file_path,
            nid_dam_height,
            session_data_dir,
            active_streamlit,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Section 04 Figure 04
    if active_streamlit:
        st.write("Step 7 / 12")
        st.write("Processing for the streamflow period of record...")
    else:
        print("Step 7 / 12")
        print("Processing for the streamflow period of record...")
    try:
        report_document = plot_streamflow_summary(
            report_document,
            df_gages_usgs,
            dates,
            domain_id,
            session_data_dir,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Section 04 Figure 05
    if active_streamlit:
        st.write("Step 8 / 12")
        st.write("Processing for the NLCD data...")
    else:
        print("Step 8 / 12")
        print("Processing for the NLCD data...")
    try:
        report_document = plot_nlcd(
            report_document,
            perimeter,
            nlcd_resolution,
            nlcd_year,
            domain_id,
            session_data_dir,
            active_streamlit,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Section 04 Figure 07
    if active_streamlit:
        st.write("Step 9 / 12")
        st.write("Processing for the constructed model mesh...")
    else:
        print("Step 9 / 12")
        print("Processing for the constructed model mesh...")
    try:
        report_document = plot_model_mesh(
            report_document,
            perimeter,
            breaklines,
            cell_polygons,
            domain_id,
            session_data_dir,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Appendix A Figure 09
    if active_streamlit:
        st.write("Step 10 / 12")
        st.write("Processing for the max WSE errors...")
    else:
        print("Step 10 / 12")
        print("Processing for the max WSE errors...")
    try:
        report_document = plot_wse_errors(
            report_document,
            cell_points,
            wse_error_threshold,
            num_bins,
            domain_id,
            session_data_dir,
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    # Generate the Appendix A Figure 10
    if active_streamlit:
        st.write("Step 11 / 12")
        st.write("Processing for the WSE time to peak...")
    else:
        print("Step 11 / 12")
        print("Processing for the WSE time to peak...")
    try:
        report_document = plot_wse_ttp(
            report_document, cell_points, num_bins, domain_id, session_data_dir
        )
        st.success("Complete!")
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
    if len(df_gages_usgs) > 0:
        # Generate the Appendix A Figure 11
        if active_streamlit:
            st.write("Step 12 / 12")
            st.write("Processing for the calibration hydrographs...")
        else:
            print("Step 12 / 12")
            print("Processing for the calibration hydrographs...")
        try:
            report_document = plot_hydrographs(
                report_document,
                hdf_plan_file_path,
                df_gages_usgs,
                dates,
                domain_id,
                session_data_dir,
                active_streamlit,
            )
            st.success("Complete!")
        except Exception as e:
            st.error(f"Error generating figure(s): {e}")

    # Save the report document
    document_path = os.path.join(
        session_data_dir,
        "FFRD-RAS-Report-Automated-Updated.docx",
    )

    if os.path.exists(document_path):
        report_document.save(document_path)
    else:
        os.makedirs(os.path.dirname(document_path), exist_ok=True)
        report_document.save(document_path)

    st.write("Report Generation Complete!")
    return


def main_auto_report(
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    report_document: Document,
    input_domain_id: str,
    stream_frequency_threshold: int,
    nlcd_resolution: int,
    nlcd_year: int,
    wse_error_threshold: float,
    num_bins: int,
    nid_parquet_file_path: str,
    nid_dam_height: int,
    session_data_dir: str,
    active_streamlit: bool,
):
    """
    Main function to run the auto report

    Parameters
    ----------
    hdf_geom_file_path : str
        The path to the geometry HDF file
    hdf_plan_file_path : str
        The path to the plan HDF file
    report_document : Docx Document
        The document to modify
    input_domain_id : str
        Optional input for the domain ID
    stream_frequency_threshold : int
        The threshold frequency for the stream names. Ex: filter to streams whose
        name occurs 20 times or more within the NHDPlus HR network.
    nlcd_resolution : int
        The resolution of the NLCD data to retrieve in meters (30)
    nlcd_year : int
        The year of the NLCD data to retrieve (2019)
    wse_error_threshold : float
        The threshold for the WSE error
    num_bins : int
        The number of bins for the histogram
    nid_parquet_file_path : str
        The path to the parquet file containing the backup NID data
    nid_dam_height : int
        The dam height threshold for the NID inventory
    session_data_dir : str
        The session data directory path
    active_streamlit : bool
        If true, print statements will be displayed in the Streamlit app
        If false, print statements will be displayed in the terminal

    Returns
    -------
    None
    """
    # Apply the nest_asyncio patch
    nest_asyncio.apply()

    # Use asyncio.run if not in an already running event loop
    if not asyncio.get_event_loop().is_running():
        asyncio.run(
            auto_report(
                hdf_geom_file_path,
                hdf_plan_file_path,
                report_document,
                input_domain_id,
                stream_frequency_threshold,
                nlcd_resolution,
                nlcd_year,
                wse_error_threshold,
                num_bins,
                nid_parquet_file_path,
                nid_dam_height,
                session_data_dir,
                active_streamlit,
            )
        )
    else:
        # If already in an event loop, use create_task
        asyncio.create_task(
            auto_report(
                hdf_geom_file_path,
                hdf_plan_file_path,
                report_document,
                input_domain_id,
                stream_frequency_threshold,
                nlcd_resolution,
                nlcd_year,
                wse_error_threshold,
                num_bins,
                nid_parquet_file_path,
                nid_dam_height,
                session_data_dir,
                active_streamlit,
            )
        )
