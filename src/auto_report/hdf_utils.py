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


def get_hdf_plan(hdf_file_path: str, input_domain_id: str):
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

    # Get the simulation start and end times
    plan_attr = plan_hdf.get_plan_info_attrs()
    start_time = plan_attr["Simulation Start Time"]
    end_time = plan_attr["Simulation End Time"]
    dates = (start_time, end_time)

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

    return (cell_points, dates)


def get_hdf_geom(hdf_file_path: str, input_domain_id: str):
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
    # Convert the perimeter to a geo json object
    geojson_str = perimeter.to_json()
    perimeter_geojson = json.loads(geojson_str)
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
        perimeter_geojson,
        domain_id,
        cell_polygons,
        breaklines,
    )


def get_domain_names(hdf_file_path: h5py.File):
    """
    Get all domain flow area names from the HDF file

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file

    Returns
    -------
    flow_areas
        A list of domain names
    """
    flow_areas = []
    omit = [
        "Attributes",
        "Cell Info",
        "Cell Points",
        "Polygon Info",
        "Polygon Parts",
        "Polygon Points",
    ]
    # open hdf from s3 uri
    if hdf_file_path.startswith("s3://"):
        with fsspec.open(hdf_file_path, mode="rb") as f:
            hdf = h5py.File(f, "r")
            hdf_path = hdf["Geometry/2D Flow Areas/"]
            for key in hdf_path:
                if key not in omit:
                    flow_areas.append(key)
                    print(key)
        if len(flow_areas) == 1:
            return flow_areas[0]
        else:
            print(
                "Multiple 2D flow areas found within HDF file. Please select one from the returned list."
            )
            return flow_areas

    else:
        # open hdf from local file path
        with h5py.File(hdf_file_path, "r") as hdf:
            hdf_path = hdf["Geometry/2D Flow Areas/"]
            for key in hdf_path:
                if key not in omit:
                    flow_areas.append(key)
                    print(key)
        if len(flow_areas) == 1:
            return flow_areas[0]
        else:
            print(
                "Multiple 2D flow areas found within HDF file. Please select one from the returned list."
            )
            return flow_areas


def decode_hdf_projection(hdf: h5py.File):
    """
    Decode the projection from the HDF file

    Parameters
    ----------
    hdf : h5py.File
        The HDF file object

    Returns
    -------
    str
        The decoded projection
    """
    proj_wkt = hdf.attrs.get("Projection")
    if proj_wkt is None:
        print("No projection found in HDF file.")
        return None
    if type(proj_wkt) == bytes or type(proj_wkt) == np.bytes_:
        proj_wkt = proj_wkt.decode("utf-8")
    return CRS.from_wkt(proj_wkt)


def get_projection(hdf_file_path: str):
    """
    Get the projection coordinate reference system from the HDF plan file

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file

    Returns
    -------
    hdf_proj
        The projection of the HDF file
    """
    # open hdf from s3 uri
    if hdf_file_path.startswith("s3://"):
        with fsspec.open(hdf_file_path, mode="rb") as f:
            hdf = h5py.File(f, "r")
            hdf_proj = decode_hdf_projection(hdf)
            return hdf_proj
    # open hdf from local file path
    else:
        with h5py.File(hdf_file_path, "r") as hdf:
            hdf_proj = decode_hdf_projection(hdf)
            return hdf_proj


def create_xy_gdf(coords: np.array, crs: CRS):
    """
    Create a GeoDataFrame from x and y coordinates

    Parameters
    ----------
    coords : np.array
        An array of x and y coordinates
    crs : CRS
        The coordinate reference system of the GeoDataFrame
    """
    # assign to a dataframe
    df = pd.DataFrame(coords)
    cells = df.index
    # rename the columns to x and y
    df.columns = ["x", "y"]
    # convert both columns to numeric
    df["x"] = pd.to_numeric(df["x"])
    df["y"] = pd.to_numeric(df["y"])
    # convert to a spatial geopandas dataframe
    gdf = gpd.GeoDataFrame(df, geometry=gpd.points_from_xy(df["x"], df["y"]), crs=crs)
    gdf["Cell"] = cells
    # drop th x and y columns
    gdf = gdf.drop(columns=["x", "y"])
    return gdf


def get_cell_pts(hdf_file_path: str, domain_name: str):
    """
    Get the cell center points of the specified domain as a GeoDataFrame

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    domain_name : str
        The name of the domain in the HDF file

    Returns
    -------
    gdf : gpd.GeoDataFrame
        A geopandas dataframe with the geometry of the computational cells
    """
    # get the projection
    hdf_crs = get_projection(hdf_file_path)
    # open hdf from s3 uri
    if hdf_file_path.startswith("s3://"):
        with fsspec.open(hdf_file_path, mode="rb") as f:
            hdf = h5py.File(f, "r")
            hdf_path = hdf[
                f"Geometry/2D Flow Areas/{domain_name}/Cells Center Coordinate"
            ]
            # assign to a dataframe
            gdf = create_xy_gdf(hdf_path, hdf_crs)
            return gdf
    # open hdf from local file path
    else:
        with h5py.File(hdf_file_path, "r") as hdf:
            # navigate to the key path
            hdf_path = hdf[
                f"Geometry/2D Flow Areas/{domain_name}/Cells Center Coordinate"
            ]
            # assign to a dataframe
            gdf = create_xy_gdf(hdf_path, hdf_crs)
            return gdf


def get_perimeter(hdf_file_path: str, domain_name: str):
    """
    Get the perimeter of the specified domain as a GeoDataFrame

    Parameters
    ----------
    hdf_file_path : str
        The file path to the HDF file
    domain_name : str
        The name of the domain in the HDF file

    Returns
    -------
    gdf
        A GeoDataFrame containing the perimeter of the domain
    """
    # get the projection
    hdf_crs = get_projection(hdf_file_path)
    # open hdf from s3 uri
    if hdf_file_path.startswith("s3://"):
        with fsspec.open(hdf_file_path, mode="rb") as f:
            hdf = h5py.File(f, "r")
            perimeter_polygon = Polygon(
                hdf[f"Geometry/2D Flow Areas/{domain_name}/Perimeter"][()]
            )
            gdf = gpd.GeoDataFrame(
                {"geometry": [perimeter_polygon], "name": [domain_name]}, crs=hdf_crs
            )
            return gdf
    # open hdf from local file path
    else:
        with h5py.File(hdf_file_path, "r") as hdf:
            perimeter_polygon = Polygon(
                hdf[f"Geometry/2D Flow Areas/{domain_name}/Perimeter"][()]
            )
            gdf = gpd.GeoDataFrame(
                {"geometry": [perimeter_polygon], "name": [domain_name]}, crs=hdf_crs
            )
            return gdf


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
