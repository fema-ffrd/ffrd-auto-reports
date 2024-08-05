# -*- coding: utf-8 -*-

# Imports #####################################################################

import geopandas as gpd
import py3dep
from pygeohydro import NWIS, DataNotAvailableError
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
            flowlines = nhd_hr.bygeom(
                model_perimeter.geometry.iloc[0], model_perimeter.crs
            )
            return flowlines
        except Exception as e:
            print(f"Failed retrieving flowlines from NHDPlus HR:")
            print("Attempting to retrieve flowlines from 3DHP...")
            try:
                # Create an instance of the 3DHP class
                hp3d = HP3D("flowline")
                # Query the 3DHP flowlines that intersect the model perimeter
                flowlines = hp3d.bygeom(
                    model_perimeter.geometry.iloc[0], model_perimeter.crs
                )
                return flowlines
            except Exception as e:
                print(f"Failed retrieving flowlines from 3DHP: {e}")
                return None


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
    try:
        # Create an instance of the NID class
        nid = gh.NID()
        # Query the NID dams that intersect the model perimeter
        dams = nid.get_bygeom(model_perimeter.geometry.iloc[0], model_perimeter.crs)
        return dams
    except Exception as e:
        print(f"Failed retrieving dams from NID: {e}")
        return None


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
    try:
        # Retrieve the NLCD data at the specified resolution and year
        nlcd = gh.nlcd_bygeom(model_perimeter, resolution, years={"cover": year})[0]
        return nlcd
    except Exception as e:
        print(f"Failed retrieving NLCD data: {e}")
        return None


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
    stations = df_gages_usgs.code.values
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
        raise ValueError(f"Failed to get daily values for the gage stations: {e}")
