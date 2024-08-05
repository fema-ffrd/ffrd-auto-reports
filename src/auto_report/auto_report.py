# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import shutil
import asyncio
import nest_asyncio
import geopandas as gpd
from ulmo_api import select_gages
from docx import Document

from hdf_utils import get_hdf_geom, get_hdf_plan

from figures import (
    plot_pilot_study_area,
    plot_dem,
    plot_stream_network,
    plot_streamflow_summary,
    plot_nlcd,
    plot_soil_porosity,
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


# Apply the nest_asyncio patch
nest_asyncio.apply()
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
    template_path: str,
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    input_domain_id: str,
    stream_frequency_threshold: int,
    nlcd_resolution: int,
    nlcd_year: int,
    wse_error_threshold: float,
    num_bins: int,
    root_dir: str,
    report_document: Document,
):
    """
    Generate the figures for the report

    Parameters
    ----------
    template_path : str
        The file path to the template document
    hdf_geom_file_path : str
        The path to the geometry HDF file
    hdf_plan_file_path : str
        The path to the plan HDF file
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
    root_dir : str
        The root directory
    report_document : Docx Document
        The document to modify

    Returns
    -------
    None
    """

    # Get the HDF data
    print("Processing for the HDF geometry data...")
    (
        perimeter,
        geojson_obj,
        domain_id,
        cell_polygons,
        breaklines,
    ) = get_hdf_geom(hdf_geom_file_path, input_domain_id)

    # Get the HDF plan data
    print("Processing for the HDF plan data...")
    cell_points, dates = get_hdf_plan(hdf_plan_file_path, input_domain_id)

    # Collect all USGS gages located within the perimeter boundary
    print("Processing for the USGS gages dataset...")
    try:
        df_gages_usgs = select_gages(
            selection_type="spatial_file",
            parameter="Streamflow",
            spatial_file=geojson_obj,
            filter_to_realtime=False,
        )
        # Convert df_gages_usgs to a geodataframe
        df_gages_usgs = gpd.GeoDataFrame(
            df_gages_usgs,
            geometry=gpd.points_from_xy(df_gages_usgs.lon, df_gages_usgs.lat),
            crs="EPSG:4326",
        )
        # Filter the gages to only include those within the model perimeter
        df_gages_usgs = df_gages_usgs[df_gages_usgs.within(perimeter.geometry.iloc[0])]
    except Exception as e:
        print(f"Error processing the USGS gages dataset: {e}")
        # Create an empty geodataframe if the gages dataset fails to process
        df_gages_usgs = gpd.GeoDataFrame(
                    [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
                )

    """
    Begin generating the report figures. Each figure will be generated in a separate function.
    If that function fails, the error will be caught but the report will continue to generate 
    the remaining figures starting with the proceeding figure.
    """
    if os.path.exists(template_path):
        # Generate the Section 01 Figure 01
        try:
            report_document = plot_pilot_study_area(
                report_document,
                perimeter,
                stream_frequency_threshold,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Section 01 Figure 01: {e}")
            report_document = report_document
        # Generate the Section 01 Figure 02
        try:
            report_document = plot_dem(report_document, perimeter, domain_id, root_dir)
        except Exception as e:
            print(f"Error generating Section 01 Figure 02: {e}")
            report_document = report_document
        # Generate the Section 04 Figure 03
        try:
            report_document = plot_stream_network(
                report_document, perimeter, df_gages_usgs, domain_id, root_dir
            )
        except Exception as e:
            print(f"Error generating Section 04 Figure 03: {e}")
            report_document = report_document
        # Generate the Section 04 Figure 04
        try:
            report_document = plot_streamflow_summary(
                report_document,
                df_gages_usgs,
                dates,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Section 04 Figure 04: {e}")
            report_document = report_document
        # Generate the Section 04 Figure 05
        try:
            report_document = plot_nlcd(
                report_document,
                perimeter,
                nlcd_resolution,
                nlcd_year,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Section 04 Figure 05: {e}")
            report_document = report_document
        # Generate the Section 04 Figure 06
        try:
            report_document = plot_soil_porosity(
                report_document,
                perimeter,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Section 04 Figure 06: {e}")
            report_document = report_document
        # Generate the Section 04 Figure 07
        try:
            report_document = plot_model_mesh(
                report_document,
                perimeter,
                breaklines,
                cell_polygons,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Section 04 Figure 07: {e}")
            report_document = report_document
        # Generate the Appendix A Figure 09
        try:
            report_document = plot_wse_errors(
                report_document,
                cell_points,
                wse_error_threshold,
                num_bins,
                domain_id,
                root_dir,
            )
        except Exception as e:
            print(f"Error generating Appendix A Figure 09: {e}")
            report_document = report_document
        # Generate the Appendix A Figure 10
        try:
            report_document = plot_wse_ttp(
                report_document, cell_points, num_bins, domain_id, root_dir
            )
        except Exception as e:
            print(f"Error generating Appendix A Figure 10: {e}")
            report_document = report_document
        
        if len(df_gages_usgs) > 0:
            # Generate the Appendix A Figure 11
            try:
                report_document = plot_hydrographs(
                    report_document,
                    hdf_plan_file_path,
                    df_gages_usgs,
                    dates,
                    domain_id,
                    root_dir,
                )
            except Exception as e:
                print(f"Error generating Appendix A Figure 11: {e}")
        # Save the document
        document_path = os.path.join(
            root_dir,
            "data",
            "2_production",
            "report",
            "FFRD-RAS-Report-Automated-Updated.docx",
        )
        if os.path.exists(document_path):
            report_document.save(document_path)
        else:
            raise FileNotFoundError("The output document path does not exist")
    else:
        raise FileNotFoundError("The input document path does not exist")

    return

def main_auto_report(
    hdf_geom_file_path: str,
    hdf_plan_file_path: str,
    input_domain_id: str,
    stream_frequency_threshold: int,
    nlcd_resolution: int,
    nlcd_year: int,
    wse_error_threshold: float,
    num_bins: int,
    root_dir: str,
):
    """
    Main function to run the auto report

    Parameters
    ----------
    hdf_geom_file_path : str
        The path to the geometry HDF file
    hdf_plan_file_path : str
        The path to the plan HDF file
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
    root_dir : str
        The root directory

    Returns
    -------
    None
    """

    # Clean the report folder and copy the template
    report_document = clean_report_folder()
    template_path = os.path.join(
        root_dir,
        "data",
        "2_production",
        "report",
        "FFRD-RAS-Report-Automated-Template.docx",
    )

    # Use asyncio.run if not in an already running event loop
    if not asyncio.get_event_loop().is_running():
        print("Running in a new event loop")
        asyncio.run(
            auto_report(
                template_path,
                hdf_geom_file_path,
                hdf_plan_file_path,
                input_domain_id,
                stream_frequency_threshold,
                nlcd_resolution,
                nlcd_year,
                wse_error_threshold,
                num_bins,
                root_dir,
                report_document,
            )
        )
    else:
        # If already in an event loop, use create_task
        print("Running in an existing event loop")
        asyncio.create_task(
            auto_report(
                template_path,
                hdf_geom_file_path,
                hdf_plan_file_path,
                input_domain_id,
                stream_frequency_threshold,
                nlcd_resolution,
                nlcd_year,
                wse_error_threshold,
                num_bins,
                root_dir,
                report_document,
            )
        )
