# -*- coding: utf-8 -*-

# Imports #####################################################################

import os
import io
from typing import Optional
import requests
import numpy as np
import pandas as pd

# Functions ###################################################################

def acquire_usgs_datum(site_id):
    """Acquire the datum of a USGS gage from the USGS NWIS API

    Parameters
    ----------
    site_id : str
        The USGS site ID of the gage

    Returns
    -------
    datum : str
        The datum of the gage
    """

    # Define the base URL of the USGS NWIS API
    url = f"https://waterservices.usgs.gov/nwis/site/?format=rdb&sites={site_id}&siteStatus=all"
    r = requests.get(url)
    # check that api call worked
    if r.status_code == 200:
        # decode results
        df = pd.read_table(
            io.StringIO(r.content.decode("utf-8")), comment="#", skip_blank_lines=True
        )
        df = df.iloc[1:].copy()
        # datum_df = df[['site_no','alt_datum_cd', 'alt_va', 'alt_acy_va']]
        df.columns = [
            "Agency",
            "SiteID",
            "Name",
            "SiteType",
            "Lat",
            "Lon",
            "CoordinateAccuracy",
            "Coordinate Datum",
            "Altitude",
            "Accuracy",
            "Datum",
            "HUC",
        ]
        df.drop(
            columns=[
                "Agency",
                "Name",
                "SiteType",
                "Lat",
                "Lon",
                "CoordinateAccuracy",
                "Coordinate Datum",
                "HUC",
            ],
            inplace=True,
        )
        return df
    else:
        print(f"Server response {r.status_code}: Returning None")
        return None


def retrieveAnnualPeaks(
    site: str,
    non_zero_peak_criteria: int,
    write_file: Optional[bool] = False,
    output_format: Optional[str] = "txt",
    output_directory: Optional[str] = None,
    yearType: Optional[str] = "calendar",
):
    """retrieve peak annual data for a usgs site, write to a file (optional) and return as dataframe
    Note: currently limits to USGS sites only

    peakflow webscraping to allow format type configuration:
    https://nwis.waterdata.usgs.gov/nwis/peak?site_no=09040500&agency_cd=USGS&format=hn2 # watstore (peakfq) file
    https://nwis.waterdata.usgs.gov/nwis/peak?site_no=09040500&agency_cd=USGS&format=rdb # tab-separated file

    Args
        site (str): gage id
        write_file (boolean): default to False
        output_format (str): txt, watstore, or gif (usgs peak graph).
        output_directory (str): path to an output directory
        yearType (str): "calendar'  or 'water'. Water year refers to October 1 - September 30th time frame.
    Return
        df (pd.DataFrame): formatted dataframe of peak data
    """

    if write_file == True:
        file_name = f"{site}_peak.{output_format}"
        output_file = os.path.join(output_directory, file_name)

    # define input parameters for api call
    if output_format == "txt":
        output_format = "rdb"
    elif output_format == "watstore":
        output_format = "hn2"
    elif output_format == "gif":
        output_format == "gif"
    else:
        output_format = "rdb"  # default to txt
        print("Output format must be one of ['txt', 'watstore', 'gif']")

    try:
        # build url and make call
        if yearType == "calendar":
            url = f"https://nwis.waterdata.usgs.gov/nwis/peak?site_no={str(site)}&agency_cd=USGS&format={output_format}"
        elif yearType == "water":
            url = f"https://nwis.waterdata.usgs.gov/nwis/peak?site_no={str(site)}&agency_cd=USGS&statYearType=water&format={output_format}"
        else:
            url = f"https://nwis.waterdata.usgs.gov/nwis/peak?site_no={str(site)}&agency_cd=USGS&format={output_format}"  # default to calendar
            print("malformed yearType in api call")

        r = requests.get(url)

        # check that api call worked
        if r.status_code != 200:
            print(f"Server response {r.status_code}: Returning None")
            return None

        # decode results
        if output_format == "rdb":
            df = pd.read_table(
                io.StringIO(r.content.decode("utf-8")),
                comment="#",
                skip_blank_lines=True,
            )
            df = df.iloc[1:].copy()
            non_zero_peaks = [i for i in df["peak_va"].values.astype("float") if i != 0]
            # when gage not found, logic returns dataframe with single column
            if (
                "No sites/data found using the selection criteria specified "
                in df.columns.values
            ):
                return None

            # a site can still be active and instantaneous with data, but the data may not be usable if under a zero flow condition (ZFL)
            # if this is the case then the primary data column peak_va will provide all zeros
            # Example Site: 07103784
            elif df["peak_va"].values.astype("float").sum() == 0:
                print("Zero flow condition: Returning None")
                return None
            elif len(non_zero_peaks) < non_zero_peak_criteria:
                print("Annual flow data has too few peaks for analysis: Returning None")
                return None

        elif output_format == "hn2":
            # print(r.content.decode('utf-8'))
            pass
        elif output_format == "gif":
            # print(r)
            pass

        if write_file == True:
            if output_format == "rdb":
                lines = r.content.decode("utf-8")
                with open(output_file, "wb") as f:
                    f.write(bytes(lines, "UTF-8"))
            elif output_format == "hn2":
                pass
            elif output_format == "gif":
                pass

        return df

    # when an incorrect gage number is sent to the api, we end up at usgs url (nothing to return)
    except:
        return None


def formatHistoricDatetime(val: str):
    """handle unexpected usgs datetime formats (1932-00-00)

    Args
        val (str): hyphen separated date format
    Returns
        val (str): hyphen separated date format where any 0 month, 0 day
            dates have been replaced with YYYY-01-01
    """

    try:
        if "-00-" in val:
            val = val.replace("-00-", "-01-")
        if val.endswith("-00"):
            val = val[0:-2]
            val = f"{val}{'01'}"
        return val
    except:
        return val


def bulkRetrieveAnnualPeaks(
    sites: list,
    non_zero_peak_criteria: int,
    write_file: Optional[bool] = False,
    output_format: Optional[str] = "txt",
    output_directory: Optional[str] = None,
    yearType: Optional[str] = "calendar",
):
    """wrapper for retriveAnnualPeaks to pull gage data for multiple
    sites in one call and return a concatenated dataframe - optionally
    write the results (txt, watstore, gif) to a directory

    Args:
        sites (list): list of usgs sites in string format
        write_file (boolean): default to False
        output_format (str): one of txt, watstore, or gif (usgs peak graph).
        output_directory (str): path to an output directory
        yearType (str): "calendar'  or 'water'. Water year refers to October 1 - September 30th time frame.
    Returns:
        df_peaks (pd.DataFrame): concatenated peak data for all sites
        df_summary (pd.DataFrame): summary of station and beginning, end dates
    """

    # loop through all sites, getting dataframe of peaks
    peaks = []
    for site in sites:
        df_temp = retrieveAnnualPeaks(
            site,
            non_zero_peak_criteria,
            write_file=write_file,
            output_format=output_format,
            output_directory=output_directory,
            yearType=yearType,
        )
        if type(df_temp) != None:
            peaks.append(df_temp)

    # concat results, convert to datetimes, handling unexpected historic date formats (i.e. 1932-00-00)
    df = pd.concat(peaks, ignore_index=True)
    df["peak_dt_datetime"] = df["peak_dt"].apply(formatHistoricDatetime)
    df["peak_dt_datetime"] = pd.to_datetime(df["peak_dt_datetime"], errors="coerce")

    return df


def retrieveInstantaneousData(
    site: str,
    parameter: str,
    start_date: str,
    end_date: str,
    write_file: Optional[bool] = False,
    output_format: Optional[str] = "txt",
    output_directory: Optional[str] = None,
):
    """retrieve instantaneous data for a usgs site, write to a file (optional, and return as a dataframe

    Note: currently limits to USGS sites only, all sites (regardless of active status), and stream discharge only
    Note: api call built from USGS api builder: https://waterservices.usgs.gov/rest/IV-Test-Tool.html

    Args
        site (str): gage id
        start_date (str): formatted to 'YYYY-MM-DD'
        end_date (str): formatted to 'YYYY-MM-DD'
        write_file (boolean): default to False
        output_format (str): one of [txt, waterML-2.0, json].
        output_directory (str): path to an output directory
    Return
        df (pd.DataFrame): formatted dataframe of peak data
    """

    if write_file == True:
        file_name = f"{site}_instantaneous.{output_format}"
        output_file = os.path.join(output_directory, file_name)

    # define input parameters for api call
    if output_format == "txt":
        output_format = "rdb"
    elif output_format == "waterML-2.0":
        output_format = "waterml,2.0"
    elif output_format == "json":
        output_format == "json"
    else:
        print("Output format must be one of ['txt', 'waterML-2.0', 'json']")

    if parameter == "Streamflow":
        param_id = "00060"
        try:
            # build url and make call only for USGS funded sites
            url = f"https://waterservices.usgs.gov/nwis/iv/?format={output_format}&sites={site}&startDT={start_date}&endDT={end_date}&parameterCd={param_id}&siteType=ST&agencyCd=usgs&siteStatus=all"
            r = requests.get(url)

            # check that api call worked
            if r.status_code != 200:
                print(f"Server response {r.status_code}: Returning None")
                return None

            # decode results
            if output_format == "rdb":
                df = pd.read_table(
                    io.StringIO(r.content.decode("utf-8")),
                    comment="#",
                    skip_blank_lines=True,
                )
                df = df.iloc[1:].copy()

            elif output_format == "waterml,2.0":
                # print(r.content.decode('utf-8'))
                pass
            elif output_format == "json":
                # print(r.content.decode('utf-8'))
                pass

            if df[df.columns[4]].values[0] == "ZFL":
                print("Zero flow condition: Return None")
                return None

            if df[df.columns[4]].values[0] == "***":
                print("Data temporarily unavailable for the time period specified")
                return None
            elif set(df["site_no"].isnull()) == {True}:
                return None

            # format the final dataframe to represent the observed rainfall following a datetime index
            final_df = pd.DataFrame(df[df.columns[4]].astype("float"))
            final_df["agency_cd"] = ["agency_cd"] * len(final_df)
            final_df["site_no"] = [site] * len(final_df)
            final_df.index = pd.to_datetime(df[df.columns[2]].values)

            # write the file to disk if data frame has sites populated
            null_sites = df["site_no"].isnull()
            if write_file == True and set(null_sites) == {False}:
                if output_format == "rdb":
                    print(f"writing {output_file}")
                    final_df.to_csv(output_file)
                    # lines = r.content.decode('utf-8')
                    # with open(output_file, 'wb') as f:
                    #     f.write(bytes(lines, "UTF-8"))
                elif output_format == "hn2":
                    pass
                elif output_format == "gif":
                    pass

            return final_df

        # when an incorrect gage number is sent to the api, we end up at usgs url (second failure mechanism)
        except:
            return None

    elif parameter == "Precipitation":
        param_id = "00045"
        try:
            # build url and make call for all available rain gage sites for CONUS
            url = f"https://waterservices.usgs.gov/nwis/iv/?format={output_format}&sites={site}&startDT={start_date}&endDT={end_date}&parameterCd={param_id}&siteStatus=all"
            r = requests.get(url)

            # check that api call worked
            if r.status_code != 200:
                print(f"Server response {r.status_code}: Returning None")
                return None

            # decode results
            if output_format == "rdb":
                df = pd.read_table(
                    io.StringIO(r.content.decode("utf-8")),
                    comment="#",
                    skip_blank_lines=True,
                )
                df = df.iloc[1:].copy()

            elif output_format == "waterml,2.0":
                # print(r.content.decode('utf-8'))
                pass
            elif output_format == "json":
                # print(r.content.decode('utf-8'))
                pass

            if df[df.columns[4]].values[0] == "***":
                print("Data temporarily unavailable for the time period specified")
                return None
            elif set(df["site_no"].isnull()) == {True}:
                return None

            # format the final dataframe to represent the observed rainfall following a datetime index
            final_df = pd.DataFrame(df[df.columns[4]].astype("float"))
            final_df["agency_cd"] = ["agency_cd"] * len(final_df)
            final_df["site_no"] = [site] * len(final_df)
            final_df.index = pd.to_datetime(df[df.columns[2]].values)

            # write the file to disk if data frame has sites populated
            if write_file == True:
                if output_format == "rdb":
                    print(f"writing {output_file}")
                    final_df.to_csv(output_file)
                    # with open(output_file, 'wb') as f:
                    # f.write(bytes(lines, "UTF-8"))
                elif output_format == "hn2":
                    pass
                elif output_format == "gif":
                    pass

            return final_df

        # when an incorrect gage number is sent to the api, we end up at usgs url (second failure mechanism)
        except:
            return None

    elif parameter == "Stage":
        param_id = "00065"
        try:
            # build url and make call only for USGS funded sites
            url = f"https://waterservices.usgs.gov/nwis/iv/?format={output_format}&sites={site}&startDT={start_date}&endDT={end_date}&parameterCd={param_id}&siteType=ST&agencyCd=usgs&siteStatus=all"
            r = requests.get(url)

            # check that api call worked
            if r.status_code != 200:
                print(f"Server response {r.status_code}: Returning None")
                return None

            # decode results
            if output_format == "rdb":
                df = pd.read_table(
                    io.StringIO(r.content.decode("utf-8")),
                    comment="#",
                    skip_blank_lines=True,
                )
                df = df.iloc[1:].copy()

            elif output_format == "waterml,2.0":
                # print(r.content.decode('utf-8'))
                pass
            elif output_format == "json":
                # print(r.content.decode('utf-8'))
                pass

            if df[df.columns[4]].values[0] == "ZFL":
                print("Zero flow condition: Return None")
                return None

            if df[df.columns[4]].values[0] == "***":
                print("Data temporarily unavailable for the time period specified")
                return None
            elif set(df["site_no"].isnull()) == {True}:
                return None

            # format the final dataframe to represent the observed rainfall following a datetime index
            final_df = pd.DataFrame(df[df.columns[4]].astype("float"))
            final_df["agency_cd"] = ["agency_cd"] * len(final_df)
            final_df["site_no"] = [site] * len(final_df)
            final_df.index = pd.to_datetime(df[df.columns[2]].values)

            # write the file to disk if data frame has sites populated
            null_sites = df["site_no"].isnull()
            if write_file == True and set(null_sites) == {False}:
                if output_format == "rdb":
                    print(f"writing {output_file}")
                    final_df.to_csv(output_file)
                    # lines = r.content.decode('utf-8')
                    # with open(output_file, 'wb') as f:
                    #     f.write(bytes(lines, "UTF-8"))
                elif output_format == "hn2":
                    pass
                elif output_format == "gif":
                    pass

            return final_df

        # when an incorrect gage number is sent to the api, we end up at usgs url (second failure mechanism)
        except:
            return None

    else:
        print(
            "Only gaged Streamflow and Precipitation are available parameters for analysis at this point in time"
        )
        return
