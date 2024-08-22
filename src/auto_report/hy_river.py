# -*- coding: utf-8 -*-

# Imports #####################################################################
from typing import Optional
import requests
import pandas as pd
from shapely.geometry import Point
import geopandas as gpd
import py3dep
from pygeohydro import (
    NWIS,
    DataNotAvailableError,
    ServiceUnavailableError,
    ServiceError,
)
from pygeoutils import EmptyResponseError
import xml.etree.ElementTree as ET
import pygeohydro as gh
from pynhd import HP3D, WaterData, NHDPlusHR

# Functions ###################################################################


def get_dem_data(model_perimeter: gpd.GeoDataFrame):
    """
    Get the DEM data within the model perimeter

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model

    Returns
    -------
    gpd.GeoDataFrame
        The DEM data within the model perimeter
    """
    # Get the bounding box of the model perimeter
    bbox = tuple(model_perimeter.bounds.values[0])
    # Check for DEM availability
    dem_availability = py3dep.check_3dep_availability(bbox)
    if dem_availability["60m"]:
        print("60 m DEM is available")
        res = 60
        dem = py3dep.get_dem(bbox, res)
        return dem
    elif dem_availability["30m"]:
        print("30 m DEM is available")
        res = 30
        dem = py3dep.get_dem(bbox, res)
        return dem
    elif dem_availability["10m"]:
        print("10 m DEM is available")
        res = 10
        dem = py3dep.get_dem(bbox, res)
        return dem
    elif dem_availability["5m"]:
        print("5 m DEM is available")
        res = 5
        dem = py3dep.get_dem(bbox, res)
        return dem
    elif dem_availability["3m"]:
        print("3 m DEM is available")
        res = 3
        dem = py3dep.get_dem(bbox, res)
        return dem
    else:
        print("No DEM available")
        dem = None


def get_nhd_flowlines(model_perimeter: gpd.GeoDataFrame):
    """
    Get the NHD flowlines within the model perimeter

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model

    Returns
    -------
    gpd.GeoDataFrame
        The NHD flowlines within the model perimeter
    """
    try:
        # Create an instance of the NHDPlus MR class
        nhd_mr = WaterData("nhdflowline_network")
        # Query the NHD flowlines that intersect the model perimeter
        flowlines = nhd_mr.bygeom(model_perimeter.geometry.iloc[0], model_perimeter.crs)
        return flowlines
    except Exception as e:
        print(f"Failed retrieving flowlines from NHD")
        print("Attempting to retrieve flowlines from the local NHDPlus HR dataset...")
    try:
        # Create an instance of the NHDPlus HR class
        nhd_hr = NHDPlusHR("flowline")
        # Query the NHDPlus HR flowlines that intersect the model perimeter
        flowlines = nhd_hr.bygeom(model_perimeter.geometry.iloc[0], model_perimeter.crs)
        return flowlines
    except Exception as e:
        print(f"Failed retrieving flowlines from NHDPlus HR:")
        print("Attempting to retrieve flowlines from 3DHP...")
    try:
        # Create an instance of the 3DHP class
        hp3d = HP3D("flowline")
        # Query the 3DHP flowlines that intersect the model perimeter
        flowlines = hp3d.bygeom(model_perimeter.geometry.iloc[0], model_perimeter.crs)
        return flowlines
    except Exception as e:
        return_statement = f"Data Unavailable: {e}"
        return return_statement


def get_nid_dams(model_perimeter: gpd.GeoDataFrame):
    """
    Get the NID dams within the model perimeter

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model

    Returns
    -------
    gpd.GeoDataFrame
        The NID dams within the model perimeter
    """
    # First check if the NID server is available
    url = "https://nid.sec.usace.army.mil/api/nation/gpkg"
    response = requests.get(url)
    response.status_code
    if response.status_code != 200:
        print(
            f"NID server is currently unavailable. Server Code: {response.status_code}"
        )
        return None
    else:
        print(f"NID server is available. Server Code: {response.status_code}")
        try:
            # Create an instance of the NID class
            nid = gh.NID()
            # Query the NID dams that intersect the model perimeter
            dams = nid.get_bygeom(model_perimeter.geometry.iloc[0], model_perimeter.crs)
            return dams
        except ServiceError as e:
            print(
                f"Failed retrieving dams from NID. The server is currently unavailable: {e}"
            )
            return None
        except EmptyResponseError as e:
            print(f"No dams found within the model perimeter: {e}")
            return None
        except Exception as e:
            print(f"Failed retrieving dams from NID: {e}")
            return None


def filter_nid(
    parquet_file_path: str,
    model_perimeter: gpd.GeoDataFrame,
    height_threshold: int = 50,
):
    """
    Filter the National Inventory of Dams (NID) data to only include points
    within the specified state and above the specified height threshold.

    Parameters
    ----------
    parquet_file_path : str
        The path to the Parquet file containing the NID data.
    model_perimeter : gpd.GeoDataFrame
        The GeoDataFrame representing the model perimeter.
    height_threshold : int
        The vertical dam height threshold to filter the NID data by.

    Returns
    -------
    filtered_nid_gdf : gpd.GeoDataFrame
        A GeoDataFrame containing the filtered NID data.
    """

    # Read the Parquet file containing point data
    nid_df = pd.read_parquet(parquet_file_path)
    # Columns in the Parquet file: ['name', 'latitude', 'longitude', 'nidId', 'damHeight']

    # Filter to the points with a height greater or equal to the threshold
    nid_df = nid_df[nid_df["damHeight"] >= height_threshold]
    # Remove any dams with missing height values
    nid_df = nid_df.dropna(subset=['damHeight'])

    # Ensure the point data has 'latitude' and 'longitude' columns
    if "latitude" not in nid_df.columns or "longitude" not in nid_df.columns:
        raise ValueError(
            "The Parquet file must contain 'latitude' and 'longitude' columns."
        )

    # Filter to only the core columns of interest
    nid_df = nid_df[["latitude", "longitude", "damHeight", "nidId", "name"]]

    if len(nid_df) == 0:
        return None
    else:
        # Convert the point data to a GeoDataFrame
        nid_gdf = gpd.GeoDataFrame(
            nid_df,
            geometry=[Point(xy) for xy in zip(nid_df.longitude, nid_df.latitude)],
            crs="EPSG:4326",  # Assuming the coordinates are in WGS84
        )
        # Perform a spatial join to filter points within the polygon
        filtered_nid_gdf = gpd.sjoin(nid_gdf, model_perimeter, predicate="within")

        return filtered_nid_gdf


def get_nlcd_data(model_perimeter: gpd.GeoDataFrame, resolution: int, year: int):
    """
    Get the NLCD data within the model perimeter

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model
    resolution : int
        The resolution of the NLCD data to retrieve
    year : int
        The year of the NLCD data to retrieve

    Returns
    -------
    gpd.GeoDataFrame
        The NLCD data within the model perimeter
    """
    # First test if the NLCD server is available
    url = f"https://www.mrlc.gov/geoserver/mrlc_display/NLCD_{year}_Land_Cover_L48/wms?"
    response = requests.get(url)

    if response.status_code != 200:
        return_statement = (
            f"NLCD server is currently unavailable. Server Code: {response.status_code}"
        )
        return return_statement
    else:
        print(f"NLCD server is available. Server Code: {response.status_code}")
        try:
            # Retrieve the NLCD data at the specified resolution and year
            nlcd = gh.nlcd_bygeom(model_perimeter, resolution, years={"cover": year})[0]
            return nlcd
        except ServiceUnavailableError as e:
            return_statement = f"Failed retrieving NLCD data. {e}"
            return return_statement
        except ServiceError as e:
            return_statement = f"Failed retrieving NLCD data. {e}"
            return return_statement
        except DataNotAvailableError as e:
            return_statement = f"Failed retrieving NLCD data. {e}"
            return return_statement
        except ET.ParseError as e:
            return_statement = f"Failed retrieving NLCD data. {e}"
            return return_statement


def get_usgs_stations(model_perimeter: gpd.GeoDataFrame, variable_type: str, dates: Optional[tuple] = None):
    """
    Get the USGS gage stations within the model perimeter

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model
    variable_type : str
        The type of variable to retrieve (e.g., "flow", "stage")
    dates : tuple
        The start and end dates for the gage station data retrieval

    Returns
    -------
    stations: list
        The USGS gage stations within the model perimeter
    """
    # Create an instance of the NWIS class
    nwis = NWIS()

    # Get the bounding box of the model perimeter
    bbox = tuple(model_perimeter.bounds.values[0])  # (minx, miny, maxx, maxy)
    if variable_type is "flow":
        parameter_cd = "00060"
    elif variable_type is "stage":
        parameter_cd = "00065"
    # Query gage stations with daily values
    query_dv = {
        "bBox": ",".join(f"{b:.06f}" for b in bbox),
        "hasDataTypeCd": "dv",
        "outputDataTypeCd": "dv",
        "parameterCd": parameter_cd,
    }
    info_box_dv = nwis.get_info(query_dv)

    # Query gage stations with instantaneous values
    query_iv = {
        "bBox": ",".join(f"{b:.06f}" for b in bbox),
        "hasDataTypeCd": "iv",
        "outputDataTypeCd": "iv",
        "parameterCd": parameter_cd,
    }
    info_box_iv = nwis.get_info(query_iv)

    if dates is None:
        # Don't filter the gage stations by date
        df_gages_usgs = pd.concat([info_box_dv, info_box_iv]).drop_duplicates(
            subset=["site_no"]
        )
    else:
        # Filter the gage stations by date
        dv_gages = info_box_dv[
            (info_box_dv.begin_date <= dates[0]) & (info_box_dv.end_date >= dates[1])
        ]
        iv_gages = info_box_iv[
            (info_box_iv.begin_date <= dates[0]) & (info_box_iv.end_date >= dates[1])
        ]
        # Combine the gage stations with daily and instantaneous values
        df_gages_usgs = pd.concat([dv_gages, iv_gages]).drop_duplicates(
            subset=["site_no"]
        )

    # Convert df_gages_usgs to a geodataframe
    df_gages_usgs = gpd.GeoDataFrame(
        df_gages_usgs,
        geometry=gpd.points_from_xy(
            df_gages_usgs.dec_long_va, df_gages_usgs.dec_lat_va
        ),
        crs="EPSG:4326",
    )
    # Filter the gages to only include those within the model perimeter
    # This is necesarry since the NWIS() class only support query by rectangular bbox
    df_gages_usgs = df_gages_usgs[
        df_gages_usgs.within(model_perimeter.geometry.iloc[0])
    ]
    return df_gages_usgs.reset_index(drop=True)


def get_nwis_streamflow(df_gages_usgs: gpd.GeoDataFrame, dates: tuple):
    """
    Get the streamflow data for the USGS gage stations from the NWIS server

    Parameters
    ----------
    df_gages_usgs : gpd.GeoDataFrame
        The USGS gage stations metadata
    dates : tuple
        The start and end dates for the streamflow data retrieval

    Returns
    -------
    xr.Dataset
        The streamflow data for the USGS gage stations
    """
    # Create an instance of the NWIS class
    nwis = NWIS()
    stations = df_gages_usgs.site_no.values
    # Get all available streamflow data within the specified date range for the gage stations
    try:
        qobs_ds = nwis.get_streamflow(
            stations, dates, mmd=False, to_xarray=True, freq="iv"
        )
        return qobs_ds
    except DataNotAvailableError as e:
        print(f"Failed to get instantaneous values for the gage stations: {e}")
        print("Attempting to get daily values instead...")
    try:
        qobs_ds = nwis.get_streamflow(
            stations, dates, mmd=False, to_xarray=True, freq="dv"
        )
        return qobs_ds
    except DataNotAvailableError as e:
        return_statement = (
            f"Failed to get daily and instantaneous values for the gage stations: {e}"
        )
        return return_statement
