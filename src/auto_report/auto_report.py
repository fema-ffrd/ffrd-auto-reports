# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import shutil
import asyncio
import nest_asyncio
import pandas as pd
import geopandas as gpd
from docx import Document
from mailmerge import MailMerge
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


def get_report_keywords(report_path: str):
    """
    Get the keywords from the report template.

    Args:
        report_path (str): The path to the report template.

    Returns:
        keyword_dict (dict): A dictionary of the keywords with blank values to fill in.
    """
    # Load the template
    with MailMerge(report_path) as document:
        # Retrieve all merge fields in the document
        merge_fields = document.get_merge_fields()
        # Convert the set to a dictionary with blank values
        keyword_dict = dict.fromkeys(merge_fields, '')
        return keyword_dict


async def save_report_text(report_file_path: str, keyword_dict: dict, output_file_path: str):
    """
    Update the text in the report template. The output file has to be a new file as ZipFile
    cannot modify existing files.

    Args:
        report_file_path (str): The path to the report template file.
        keyword_dict (dict): A dictionary of the keywords with values to fill in.
        output_file_path (str): The path to save the updated report file.

    Returns:
        None
    """
    # Load the template
    with MailMerge(report_file_path) as document:
        # Update the merge fields in the document
        document.merge(**keyword_dict)
        # Save the updated document
        document.write(output_file_path)

async def save_report_figures(document_path, report_document):
    """
    Save the report document with the autogenerated figures.

    Args:
        document_path (str): The path to the report document.
        report_document (Document): The report document object.
    """
    # Save the report document
    print("Saving the report with the autogenerated figures...")
    if os.path.exists(document_path):
        report_document.save(document_path)
        print("Figures have been added to the report.")
    else:
        os.makedirs(os.path.dirname(document_path), exist_ok=True)
        report_document.save(document_path)
        print("Figures have been added to the report.")

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

async def auto_report(
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    nlcd_file_path: str,
    report_file_path: str,
    report_keywords: dict,
    input_domain_id: str,
    stream_frequency_threshold: int,
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
    nlcd_file_path : str
        The path to the NLCD file
    report_file_path : str
        The path to the template report file
    report_keywords : dict
        The keywords to fill in the report
    input_domain_id : str
        Optional input for the domain ID
    stream_frequency_threshold : int
        The threshold frequency for the stream names. Ex: filter to streams whose
        name occurs 20 times or more within the NHDPlus HR network.
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
    report_document = Document(report_file_path)
    report_keywords['Date'] = pd.Timestamp.now().strftime("%B %d, %Y")
    
    ####################################################################################################

    # Get the HDF geometry data
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
        proj_table,
    ) = get_hdf_geom(hdf_geom_file_path, input_domain_id)

    # Update Table 1: Projection Details
    report_keywords['table01_projcs'] = proj_table['projcs']
    report_keywords['table01_geogcs'] = proj_table['geogcs']
    report_keywords['table01_datum'] = proj_table['datum']
    report_keywords['table01_ellipsoid'] = proj_table['ellipsoid']
    report_keywords['table01_method'] = proj_table['method']
    report_keywords['table01_authority'] = proj_table['authority']
    report_keywords['table01_code'] = str(proj_table['code'])
    report_keywords['table01_unit'] = proj_table['unit']

    # Get the HDF plan data
    if active_streamlit:
        st.write("Step 2 / 12")
        st.write("Processing for the HDF plan data...")
    else:
        print("Step 2 / 12")
        print("Processing for the HDF plan data...")
    cell_points, dates, plan_params, plan_attrs = get_hdf_plan(hdf_plan_file_path, input_domain_id)

    # Update Table 9: 2D Comutational Solver Tolerances and Settings
    report_keywords['table09_iwf'] = str(plan_params["2D Theta"])
    report_keywords['table09_wst'] = str(plan_params["2D Water Surface Tolerance"])
    report_keywords['table09_volt'] = str(plan_params["2D Volume Tolerance"])
    report_keywords['table09_max_iter'] = str(plan_params["2D Maximum Iterations"])
    report_keywords['table09_fts'] = plan_attrs["Computation Time Step Base"]
    report_keywords['table09_eqn'] = plan_params["2D Equation Set"]
    report_keywords['table09_output_interval'] = plan_attrs["Base Output Interval"]

    # Collect all USGS gages located within the perimeter boundary
    if active_streamlit:
        st.write("Step 3 / 12")
        st.write("Processing for USGS gage metadata...")
    else:
        print("Step 3 / 12")
        print("Processing for USGS gage metadata...")
    try:
        df_gages_usgs = get_usgs_stations(perimeter, dates)
        report_keywords['Section01_GageSummary_Txt'] = f"""
        There are {len(df_gages_usgs)} U.S. Geological Survey (USGS) stream gages maintained within
        this modeling domain.
        """
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

    ####################################################################################################

    """
    Begin generating the report figures. Each figure will be generated in a separate function.
    If that function fails, the error will be caught but the report will continue to generate 
    the remaining figures starting with the proceeding figure.
    """

    # Generate the pilot study area figure
    if active_streamlit:
        st.write("Step 4 / 12")
        st.write("Processing for the HUC04 pilot boundary...")
    else:
        print("Step 4 / 12")
        print("Processing for the HUC04 pilot boundary...")
    try:
        report_document, report_keywords = plot_pilot_study_area(
            report_document,
            report_keywords,
            perimeter,
            stream_frequency_threshold,
            domain_id,
            session_data_dir,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the basin DEM figure
    if active_streamlit:
        st.write("Step 5 / 12")
        st.write("Processing for the DEM dataset...")
    else:
        print("Step 5 / 12")
        print("Processing for the DEM dataset...")
    try:
        report_document, report_keywords = plot_dem(
            report_document,
            report_keywords,
            perimeter,
            domain_id,
            session_data_dir
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the basin stream network figure
    if active_streamlit:
        st.write("Step 6 / 12")
        st.write("Processing for the NHD stream network...")
    else:
        print("Step 6 / 12")
        print("Processing for the NHD stream network...")
    try:
        report_document, report_keywords = plot_stream_network(
            report_document,
            report_keywords,
            perimeter,
            df_gages_usgs,
            domain_id,
            nid_parquet_file_path,
            nid_dam_height,
            session_data_dir,
            active_streamlit,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the streamflow period of record summary figure(s)
    if active_streamlit:
        st.write("Step 7 / 12")
        st.write("Processing for the streamflow period of record...")
    else:
        print("Step 7 / 12")
        print("Processing for the streamflow period of record...")
    try:
        report_document, report_keywords = plot_streamflow_summary(
            report_document,
            report_keywords,
            df_gages_usgs,
            dates,
            domain_id,
            session_data_dir,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the NLCD figure
    if active_streamlit:
        st.write("Step 8 / 12")
        st.write("Processing for the NLCD data...")
    else:
        print("Step 8 / 12")
        print("Processing for the NLCD data...")
    try:
        report_document, report_keywords = plot_nlcd(
            report_document,
            report_keywords,
            hdf_geom_file_path,
            nlcd_file_path,
            domain_id,
            session_data_dir,
            active_streamlit,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    #Generate the model mesh figure
    if active_streamlit:
        st.write("Step 9 / 12")
        st.write("Processing for the constructed model mesh...")
    else:
        print("Step 9 / 12")
        print("Processing for the constructed model mesh...")
    try:
        report_document, report_keywords = plot_model_mesh(
            report_document,
            report_keywords,
            perimeter,
            breaklines,
            cell_polygons,
            domain_id,
            session_data_dir,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the max WSE errors figure
    if active_streamlit:
        st.write("Step 10 / 12")
        st.write("Processing for the max WSE errors...")
    else:
        print("Step 10 / 12")
        print("Processing for the max WSE errors...")
    try:
        report_document, report_keywords = plot_wse_errors(
            report_document,
            report_keywords,
            cell_points,
            wse_error_threshold,
            num_bins,
            domain_id,
            session_data_dir,
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    # Generate the WSE time to peak figure
    if active_streamlit:
        st.write("Step 11 / 12")
        st.write("Processing for the WSE time to peak...")
    else:
        print("Step 11 / 12")
        print("Processing for the WSE time to peak...")
    try:
        report_document, report_keywords = plot_wse_ttp(
            report_document,
            report_keywords,
            cell_points,
            num_bins,
            domain_id,
            session_data_dir
        )
    except Exception as e:
        st.error(f"Error generating figure: {e}")
        report_document = report_document
        report_keywords = report_keywords
    if len(df_gages_usgs) > 0:
        # Generate the calibration hydrograph figure(s)
        if active_streamlit:
            st.write("Step 12 / 12")
            st.write("Processing for the calibration hydrographs...")
        else:
            print("Step 12 / 12")
            print("Processing for the calibration hydrographs...")
        try:
            report_document, report_keywords = plot_hydrographs(
                report_document,
                report_keywords,
                hdf_plan_file_path,
                df_gages_usgs,
                dates,
                domain_id,
                session_data_dir,
                active_streamlit,
            )
        except Exception as e:
            st.error(f"Error generating figure(s): {e}")
            report_document = report_document
            report_keywords = report_keywords
    ####################################################################################################

    """
    Begin saving the report document with the autogenerated figures and text.
    """
    document_path_figures = os.path.join(
        session_data_dir,
        "FFRD-RAS-Report-Automated-Figures.docx",
    )
    # Save the report document with the autogenerated figures
    await save_report_figures(document_path_figures, report_document)

    document_path_final = os.path.join(
        session_data_dir,
        "FFRD-RAS-Report-Automated-Updated.docx",
    )
    # Now save the report with the autogenerated text
    await save_report_text(document_path_figures, report_keywords, document_path_final)
    os.remove(document_path_figures)
    print("The report has been successfully generated.")


def main_auto_report(
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    nlcd_file_path: str,
    report_file_path: str,
    input_domain_id: str,
    stream_frequency_threshold: int,
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
    nlcd_file_path : str
        The path to the NLCD file
    report_file_path : str
        The path to the template report file
    input_domain_id : str
        Optional input for the domain ID
    stream_frequency_threshold : int
        The threshold frequency for the stream names. Ex: filter to streams whose
        name occurs 20 times or more within the NHDPlus HR network.
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
    report_keywords = get_report_keywords(report_file_path)
    # Apply the nest_asyncio patch
    nest_asyncio.apply()

    # Use asyncio.run if not in an already running event loop
    if not asyncio.get_event_loop().is_running():
        asyncio.run(
            auto_report(
                hdf_geom_file_path,
                hdf_plan_file_path,
                nlcd_file_path,
                report_file_path,
                report_keywords,
                input_domain_id,
                stream_frequency_threshold,
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
                nlcd_file_path,
                report_file_path,
                report_keywords,
                input_domain_id,
                stream_frequency_threshold,
                wse_error_threshold,
                num_bins,
                nid_parquet_file_path,
                nid_dam_height,
                session_data_dir,
                active_streamlit,
            )
        )
