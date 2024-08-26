# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import json
import h5py
import fsspec
import pandas as pd
import numpy as np
import geopandas as gpd
from shapely.geometry import Polygon
from rashdf import RasPlanHdf, RasGeomHdf
from pyproj import CRS
import fsspec
from typing import Optional

# Functions ###################################################################


def init_s3_keys():
    """
    Initialize the os environment variables for AWS S3
    """
    from dotenv import load_dotenv

    load_dotenv(".env")
    # Set the new environment variables
    os.environ["AWS_ACCESS_KEY_ID"] = os.getenv("AWS_ACCESS_KEY_ID")
    os.environ["AWS_SECRET_ACCESS_KEY"] = os.getenv("AWS_SECRET_ACCESS_KEY")


def get_model_perimeter(
    hdf_file_path: str, input_domain_id: Optional[str], project_to_4326: bool
):
    """
    Get the HDF data

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    input_domain_id : str
        A user specified domain ID
    project_to_4326 : bool
        A flag to project the data to EPSG:4326

    Returns
    -------
    perimeter : gpd.GeoDataFrame
        The perimeter of the mesh
    """
    new_crs = "EPSG:4326"
    simplify_threshold = 300  # distance in feet

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            geom_hdf = RasGeomHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        geom_hdf = RasGeomHdf(hdf_file_path)

    # First try to get the mesh areas. If this fails, exit the function
    try:
        perimeter = geom_hdf.mesh_areas()
    except Exception as e:
        raise ValueError(f"Error getting the mesh areas: {e}")

    # Check if there is only one domain
    domain_id = perimeter["mesh_name"].unique()
    if len(domain_id) > 1:
        if input_domain_id not in domain_id:
            raise ValueError(
                f"Input Domain ID {input_domain_id} not found in the HDF file. {domain_id}"
            )
        else:
            perimeter = perimeter[perimeter["mesh_name"] == input_domain_id]
            # Simplify the perimeter to avoid issues with overlapping vertices
            perimeter_geom = perimeter.simplify(simplify_threshold).union_all()
            perimeter.geometry.iloc[0] = perimeter_geom
            if project_to_4326:
                perimeter = perimeter.to_crs(new_crs)
            return perimeter
    elif len(domain_id) == 1:
        # Simplify the perimeter to avoid issues with overlapping vertices
        perimeter_geom = perimeter.simplify(simplify_threshold).union_all()
        perimeter.geometry.iloc[0] = perimeter_geom
        if project_to_4326:
            perimeter = perimeter.to_crs(new_crs)
        return perimeter


def get_model_breaklines(hdf_file_path: str, project_to_4326: bool):
    """
    Get the model breaklines from the HDF file

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    project_to_4326 : bool
        A flag to project the data to EPSG:4326

    Returns
    -------
    breaklines : gpd.GeoDataFrame
        The breaklines GeoDataFrame
    """
    new_crs = "EPSG:4326"

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            geom_hdf = RasGeomHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        geom_hdf = RasGeomHdf(hdf_file_path)

    # Get the breaklines
    try:
        breaklines = geom_hdf.breaklines()
    except Exception as e:
        # If the breaklines are not available, create an empty GeoDataFrame
        print(f"Error getting the breaklines: {e}")
        print("Creating an empty GeoDataFrame for the breaklines")
        breaklines = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )
    if project_to_4326:
        # Convert the CRS to EPSG:4326
        breaklines = breaklines.to_crs(new_crs)

    return breaklines


def get_model_cell_polygons(hdf_file_path: str, project_to_4326: bool):
    """
    Get the model cell polygons from the HDF file

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    project_to_4326 : bool
        A flag to project the data to EPSG:4326

    Returns
    -------
    cell_polygons : gpd.GeoDataFrame
        The cell polygons GeoDataFrame
    """
    new_crs = "EPSG:4326"

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            geom_hdf = RasGeomHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        geom_hdf = RasGeomHdf(hdf_file_path)

    # Get the mesh cell polygons
    try:
        cell_polygons = geom_hdf.mesh_cell_polygons()
    except Exception as e:
        # If the mesh cell polygons are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell polygons: {e}")
        print("Creating an empty GeoDataFrame for the cell polygons")
        cell_polygons = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )
    if project_to_4326:
        # Convert the CRS to EPSG:4326
        cell_polygons = cell_polygons.to_crs(new_crs)

    return cell_polygons


def get_plan_cell_pts(hdf_file_path: str):
    """
    Get the HDF solution point data

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file

    Returns
    -------
    cell_points : gpd.GeoDataFrame
        The cell points GeoDataFrame
    """

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            plan_hdf = RasPlanHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        plan_hdf = RasPlanHdf(hdf_file_path)

    # First get the mesh areas. If this fails, exit the function
    try:
        perimeter = plan_hdf.mesh_areas()
    except Exception as e:
        raise ValueError(f"Error getting the mesh areas: {e}")

    # Get the mesh cell points
    try:
        cell_points = plan_hdf.mesh_cell_points()
    except Exception as e:
        # If the mesh cell points are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell points: {e}")
        print("Creating an empty GeoDataFrame for the cell points")
        cell_points = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )
    return cell_points


def get_plan_params_attrs(hdf_file_path: str):
    """
    Get the simulation plan info attributes and parameters

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file

    Returns
    -------
    plan_params : dict
        The plan parameters
    plan_attrs : dict
        The plan attributes
    """
    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            plan_hdf = RasPlanHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        plan_hdf = RasPlanHdf(hdf_file_path)

    # Get the simulation plan info attributes
    plan_params = plan_hdf.get_plan_param_attrs()
    plan_attrs = plan_hdf.get_plan_info_attrs()

    return plan_params, plan_attrs


def get_plan_cell_points(hdf_file_path: str):
    """
    Get the cell point solution data from the plan HDF file

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file

    Returns
    -------
    cell_points : gpd.GeoDataFrame
        The cell points GeoDataFrame
    """
    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            plan_hdf = RasPlanHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        plan_hdf = RasPlanHdf(hdf_file_path)

    # Get the mesh cell points
    try:
        cell_points = plan_hdf.mesh_cell_points()
    except Exception as e:
        # If the mesh cell points are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell points: {e}")
        print("Creating an empty GeoDataFrame for the cell points")
        cell_points = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )

    return cell_points


def get_bulk_hdf_plan(hdf_file_path: str, input_domain_id: str):
    """
    Get the HDF data

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    input_domain_id : str
        A user specified domain ID

    Returns
    -------
    cell_points : gpd.GeoDataFrame
        The cell points GeoDataFrame
    plan_params : dict
        The plan parameters
    plan_attrs : dict
        The plan attributes
    """
    new_crs = "EPSG:4326"

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            plan_hdf = RasPlanHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        plan_hdf = RasPlanHdf(hdf_file_path)

    # First get the mesh areas. If this fails, exit the function
    try:
        perimeter = plan_hdf.mesh_areas()
    except Exception as e:
        raise ValueError(f"Error getting the mesh areas: {e}")

    # Get the mesh cell points
    try:
        cell_points = plan_hdf.mesh_cell_points()
    except Exception as e:
        # If the mesh cell points are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell points: {e}")
        print("Creating an empty GeoDataFrame for the cell points")
        cell_points = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )

    # Get the simulation plan info attributes
    plan_params = plan_hdf.get_plan_param_attrs()
    plan_attrs = plan_hdf.get_plan_info_attrs()

    # Convert the CRS to EPSG:4326
    cell_points = cell_points.to_crs(new_crs)
    # Check if there is only one domain
    domain_id = perimeter["mesh_name"].unique()
    if len(domain_id) > 1:
        if input_domain_id not in domain_id:
            raise ValueError(
                f"Input Domain ID {input_domain_id} not found in the HDF file. {domain_id}"
            )
        else:
            domain_id = input_domain_id
            print(f"Domain ID: {domain_id}")
    else:
        domain_id = domain_id[0]

    return (cell_points, plan_params, plan_attrs)


def get_bulk_hdf_geom(hdf_file_path: str, input_domain_id: str):
    """
    Get the HDF data

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    input_domain_id : str
        A user specified domain ID

    Returns
    -------
    perimeter : gpd.GeoDataFrame
        The perimeter of the mesh
    perimeter_geojson : dict
        The geojson object
    domain_id : str
        The domain ID
    cell_polygons : gpd.GeoDataFrame
        The cell polygons GeoDataFrame
    breaklines : gpd.GeoDataFrame
        The breaklines GeoDataFrame
    """
    new_crs = "EPSG:4326"

    # Open the HDF file from the S3 bucket
    if hdf_file_path.startswith("s3://"):
        # initialize the S3 keys
        try:
            init_s3_keys()
            geom_hdf = RasGeomHdf.open_uri(hdf_file_path)
        except Exception as e:
            raise ValueError(
                f"Error initializing the S3 keys. Check your AWS credentials. {e}"
            )
    else:
        # Open the HDF file from the local file path
        geom_hdf = RasGeomHdf(hdf_file_path)

    # First get the mesh areas. If this fails, exit the function
    try:
        perimeter = geom_hdf.mesh_areas()
    except Exception as e:
        raise ValueError(f"Error getting the mesh areas: {e}")

    # Get the mesh cell points
    try:
        cell_points = geom_hdf.mesh_cell_points()
    except Exception as e:
        # If the mesh cell points are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell points: {e}")
        print("Creating an empty GeoDataFrame for the cell points")
        cell_points = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )

    # Get the mesh cell polygons
    try:
        cell_polygons = geom_hdf.mesh_cell_polygons()
    except Exception as e:
        # If the mesh cell polygons are not available, create an empty GeoDataFrame
        print(f"Error getting the mesh cell polygons: {e}")
        print("Creating an empty GeoDataFrame for the cell polygons")
        cell_polygons = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )

    # Get the breaklines
    try:
        breaklines = geom_hdf.breaklines()
    except Exception as e:
        # If the breaklines are not available, create an empty GeoDataFrame
        print(f"Error getting the breaklines: {e}")
        print("Creating an empty GeoDataFrame for the breaklines")
        breaklines = gpd.GeoDataFrame(
            [], columns=["x", "y"], geometry=[], crs="EPSG:4326"
        )
    # Simplify the perimeter to avoid issues with overlapping vertices
    simplify_threshold = 300  # distance in feet
    perimeter_geom = perimeter.simplify(simplify_threshold).union_all()
    perimeter.geometry.iloc[0] = perimeter_geom

    # Convert the CRS to EPSG:4326
    cell_points = cell_points.to_crs(new_crs)
    cell_polygons = cell_polygons.to_crs(new_crs)
    perimeter = perimeter.to_crs(new_crs)
    breaklines = breaklines.to_crs(new_crs)
    # Get the projection information
    proj_table = hdf_projection_table(geom_hdf)
    # Check if there is only one domain
    domain_id = perimeter["mesh_name"].unique()
    if len(domain_id) > 1:
        if input_domain_id not in domain_id:
            raise ValueError(
                f"Input Domain ID {input_domain_id} not found in the HDF file. {domain_id}"
            )
        else:
            domain_id = input_domain_id
            print(f"Domain ID: {domain_id}")
    else:
        domain_id = domain_id[0]

    return (
        perimeter,
        domain_id,
        cell_polygons,
        breaklines,
        proj_table,
    )


def hdf_projection_table(plan_hdf: h5py.File):
    """
    This function reads the projection information from the HDF file and returns it as a dictionary.

    Parameters
    ----------

    plan_hdf : h5py.File. The HDF file object.

    Returns
    -------
    proj_table_items : dict. Dictionary containing the projection information.

    """

    # Read the projection from the hdf file
    proj = plan_hdf.projection()
    proj = proj.to_json_dict()

    # Extract the projection information
    projcs = proj["name"]
    geogcs = proj["base_crs"]["name"]
    datum = proj["base_crs"]["datum"]["name"]
    ellipsoid = proj["base_crs"]["datum"]["ellipsoid"]["name"]
    method = proj["conversion"]["method"]["name"]
    authority = proj["conversion"]["method"]["id"]["authority"]
    code = proj["conversion"]["method"]["id"]["code"]
    unit = proj["coordinate_system"]["axis"][0]["unit"]["name"]

    # Create a dictionary with the projection information
    proj_table_items = {
        "projcs": projcs,
        "geogcs": geogcs,
        "datum": datum,
        "ellipsoid": ellipsoid,
        "method": method,
        "authority": authority,
        "code": code,
        "unit": unit,
    }

    return proj_table_items
