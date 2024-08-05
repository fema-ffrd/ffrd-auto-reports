# -*- coding: utf-8 -*-

# Imports #####################################################################

from datetime import datetime
import os
import pandas as pd
from typing import Optional
import ulmo

# Functions ###################################################################

def determine_bbox(json_obj: dict):
    """Determine the bounding box of a GeoJSON object

    Args:
        json_obj (dict): GeoJSON object

    Returns:
        bbox (list): bounding box of the GeoJSON object.
        bbox = [westernmost longitude, southernmost latitude, easternmost longitude, northernmost latitude]

    """
    coords = json_obj["features"][0]["geometry"]["coordinates"][0]
    min_x = round(min([coord[0] for coord in coords]), 6)
    min_y = round(min([coord[1] for coord in coords]), 6)
    max_x = round(max([coord[0] for coord in coords]), 6)
    max_y = round(max([coord[1] for coord in coords]), 6)

    bbox = [str(min_x), str(min_y), str(max_x), str(max_y)]
    return bbox


def select_gages(
    selection_type: str,
    parameter: str,
    filter_to_realtime: bool = False,
    site_list: Optional[list] = None,
    spatial_file: Optional[str] = None,
) -> pd.DataFrame:
    """using the ulmo wrapper for the usgs waterservice api,
    return a list of sites based on user define selection type
    and parameters

    Args
        selection_type (str): one of [site_list, spatial_file, state_county]
        parameter (str): one of [Streamflow, Precipitation]
        filter_to_realtime (bool): whether to limit search to only gages currently
            producing real-time measurements
        spatial_file (str): path to a .shp or .gpkg to filter results
        site_list (list): list of site_no identifiers
        state (str): Two-letter state code used in stateCd parameter
        county_list (list): list of county fips codes as strings

    Returns
        df (pd.DataFrame): sites with their associated information
    """
    # initiate query parameters as None
    service = None  # instantaneous or daily, defaults to all
    input_file = None
    sites = None
    state_code = None
    huc = None
    bounding_box = None
    county_code = None
    siteStatus = "all"  # either all, active, or inactive. setting default to all

    if parameter == "Streamflow":
        site_type = "ST"
        parameter_code = "00060"
    elif parameter == "Precipitation":
        site_type = None
        parameter_code = "00045"

    # filter to realtime
    if filter_to_realtime:
        siteStatus = "active"  # hardcoding only active stream sites for now

    # based on selection type, build out query string
    if selection_type == "site_list":
        sites = site_list
    elif selection_type == "spatial_file":
        bounding_box = determine_bbox(spatial_file)
    else:
        return [
            "your selection method must match one of [site_list, spatial_file, state_county]"
        ]

    # execute query
    sites = ulmo.usgs.nwis.get_sites(
        service=service,
        input_file=input_file,
        sites=sites,
        state_code=state_code,
        huc=huc,
        bounding_box=bounding_box,
        county_code=county_code,
        parameter_code=parameter_code,
        site_type=site_type,
        siteStatus=siteStatus,
    )

    # convert to dictionary
    df1 = pd.DataFrame()
    for key in sites.keys():
        location = sites[key].pop("location")  # pop and store nested dictionary
        timezone_info = sites[key].pop(
            "timezone_info"
        )  # pop and store nested dictionary
        latitude = location["latitude"]
        longitude = location["longitude"]
        uses_dst = timezone_info["uses_dst"]
        dst_tz = timezone_info["dst_tz"]["abbreviation"]
        dst_tz_offset = timezone_info["dst_tz"]["offset"]
        default_tz = timezone_info["default_tz"]["abbreviation"]
        default_tz_offset = timezone_info["default_tz"]["offset"]

        df_temp = pd.DataFrame(data=sites[key], index=[0])
        df_temp["latitude"] = latitude
        df_temp["longitude"] = longitude
        df_temp["uses_dst"] = uses_dst
        df_temp["dst_tz"] = dst_tz
        df_temp["dst_tz_offset"] = dst_tz_offset
        df_temp["default_tz"] = default_tz
        df_temp["default_tz_offset"] = default_tz_offset

        df_temp["lat"] = df_temp["latitude"].astype(
            float
        )  # adding explicitly for mapping applications
        df_temp["lon"] = df_temp["longitude"].astype(
            float
        )  # adding explicitly for mapping applications

        df1 = pd.concat([df1, df_temp], ignore_index=True)

    # get additional data for each returned site
    # https://ulmo.readthedocs.io/en/latest/api.html#module-ulmo.usgs.nwis
    # ulmo.usgs.nwis.get_site_data

    return df1
