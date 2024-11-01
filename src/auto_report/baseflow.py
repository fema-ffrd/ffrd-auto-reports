# -*- coding: utf-8 -*-

# Imports #####################################################################
import os
import numpy as np
from numba import njit, prange
import pandas as pd
import geopandas as gpd
from pynhd import WaterData
from hydrosignatures import baseflow_recession

# Functions ###################################################################

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
        return None


@njit
def linear_interpolation(Q, idx_turn, return_exceed=False):
    if return_exceed:
        b = np.zeros(Q.shape[0] + 1)
    else:
        b = np.zeros(Q.shape[0])

    n = 0
    for i in range(idx_turn[0], idx_turn[-1] + 1):
        if i == idx_turn[n + 1]:
            n += 1
            b[i] = Q[i]
        else:
            b[i] = Q[idx_turn[n]] + (Q[idx_turn[n + 1]] - Q[idx_turn[n]]) / \
                (idx_turn[n + 1] - idx_turn[n]) * (i - idx_turn[n])
        if b[i] > Q[i]:
            b[i] = Q[i]
            if return_exceed:
                b[-1] += 1
    return b


@njit
def Local_turn(Q, inN):
    idx_turn = np.zeros(Q.shape[0], dtype=np.int64)
    for i in prange(np.int64((inN - 1) / 2), np.int64(Q.shape[0] - (inN - 1) / 2)):
        if Q[i] == np.min(Q[np.int64(i - (inN - 1) / 2):np.int64(i + (inN + 1) / 2)]):
            idx_turn[i] = i
    return idx_turn[idx_turn != 0]


def hysep_interval(area: float):
    """
    The duration of surface runoff is calculated from the empirical relation:
    N=A^0.2, (1) where N is the number of days after which surface runoff ceases,
    and A is the drainage area in square miles (Linsley and others, 1982, p. 210).
    The interval 2N* used for hydrograph separations is the odd integer between
    3 and 11 nearest to 2N (Pettyjohn and Henning, 1979, p. 31).

    Parameters
    ----------
    area : float
        The drainage area in square miles

    Returns
    -------
    int
        The interval 2N* used for hydrograph separations
    """
    if area is None:
        N = 5
    else:
        N = np.power(0.3861022 * area, 0.2)
    inN = np.ceil(2 * N)
    if np.mod(inN, 2) == 0:
        inN = np.ceil(2 * N) - 1
    inN = np.int64(min(max(inN, 3), 11))
    return inN


def Local(Q, b_LH, area=None, return_exceed=False):
    """Local minimum graphical method from HYSEP program (Sloto & Crouse, 1996)

    Args:
        Q (np.array): streamflow
        area (float): basin area in km^2
    """
    idx_turn = Local_turn(Q, hysep_interval(area))
    if idx_turn.shape[0] < 3:
        raise IndexError('Less than 3 turning points found. Please try a different baseflow separation method.')
    b = linear_interpolation(Q, idx_turn, return_exceed=return_exceed)
    b[:idx_turn[0]] = b_LH[:idx_turn[0]]
    b[idx_turn[-1] + 1:] = b_LH[idx_turn[-1] + 1:]
    return b


@njit
def LH(Q, beta=0.925, return_exceed=False):
    """LH digital filter (Lyne & Hollick, 1979)

    Args:
        Q (np.array): streamflow
        beta (float): filter parameter, 0.925 recommended by (Nathan & McMahon, 1990)
    """
    if return_exceed:
        b = np.zeros(Q.shape[0] + 1)
    else:
        b = np.zeros(Q.shape[0])

    # first pass
    b[0] = Q[0]
    for i in range(Q.shape[0] - 1):
        b[i + 1] = beta * b[i] + (1 - beta) / 2 * (Q[i] + Q[i + 1])
        if b[i + 1] > Q[i + 1]:
            b[i + 1] = Q[i + 1]
            if return_exceed:
                b[-1] += 1

    # second pass
    b1 = np.copy(b)
    for i in range(Q.shape[0] - 2, -1, -1):
        b[i] = beta * b[i + 1] + (1 - beta) / 2 * (b1[i + 1] + b1[i])
        if b[i] > b1[i]:
            b[i] = b1[i]
            if return_exceed:
                b[-1] += 1
    return b


@njit
def Chapman(Q, b_LH, a, return_exceed=False):
    """Chapman filter (Chapman, 1991)

    Args:
        Q (np.array): streamflow
        a (float): recession coefficient
    """
    if return_exceed:
        b = np.zeros(Q.shape[0] + 1)
    else:
        b = np.zeros(Q.shape[0])
    b[0] = b_LH[0]
    for i in range(Q.shape[0] - 1):
        b[i + 1] = (3 * a - 1) / (3 - a) * b[i] + (1 - a) / (3 - a) * (Q[i + 1] + Q[i])
        if b[i + 1] > Q[i + 1]:
            b[i + 1] = Q[i + 1]
            if return_exceed:
                b[-1] += 1
    return b


@njit
def CM(Q, b_LH, a, return_exceed=False):
    """CM filter (Chapman & Maxwell, 1996)

    Args:
        Q (np.array): streamflow
        a (float): recession coefficient
    """
    if return_exceed:
        b = np.zeros(Q.shape[0] + 1)
    else:
        b = np.zeros(Q.shape[0])
    b[0] = b_LH[0]
    for i in range(Q.shape[0] - 1):
        b[i + 1] = a / (2 - a) * b[i] + (1 - a) / (2 - a) * Q[i + 1]
        if b[i + 1] > Q[i + 1]:
            b[i + 1] = Q[i + 1]
            if return_exceed:
                b[-1] += 1
    return b


@njit
def Eckhardt(Q, b_LH, a, BFImax, return_exceed=False):
    """Eckhardt filter (Eckhardt, 2005)

    Args:
        Q (np.array): streamflow
        a (float): recession coefficient
        BFImax (float): maximum value of baseflow index (BFI)
    """
    if return_exceed:
        b = np.zeros(Q.shape[0] + 1)
    else:
        b = np.zeros(Q.shape[0])
    b[0] = b_LH[0]
    for i in range(Q.shape[0] - 1):
        b[i + 1] = ((1 - BFImax) * a * b[i] + (1 - a) * BFImax * Q[i + 1]) / (1 - a * BFImax)
        if b[i + 1] > Q[i + 1]:
            b[i + 1] = Q[i + 1]
            if return_exceed:
                b[-1] += 1
    return b


def get_bfi(model_perimeter: gpd.GeoDataFrame):
    """
    Get the baseflow index (BFI) for the catchment area
    based on the NHD flowlines COMID.

    Parameters
    ----------
    model_perimeter : gpd.GeoDataFrame
        The perimeter of the model

    Returns
    -------
    float
        The maximum baseflow index (BFI) value for the catchment area
    """
    # Get the NHD flowlines within the model perimeter
    flowlines = get_nhd_flowlines(model_perimeter)
    if flowlines is None:
        # Maximum baseflow index (BFI) value for the catchment area
        bfi = 0.33
    else:
        # Local path to the BFI data
        curDir = os.path.dirname(__file__)
        srcDir = os.path.abspath(os.path.join(curDir, ".."))
        bfi_path = os.path.join(srcDir, "assets", "bfi.parquet")
        # Load the BFI data and filter it to the NHD flowlines within the model perimeter
        bfi = pd.read_parquet(bfi_path,
                            engine="pyarrow",
                            filters=[('COMID', 'in', flowlines.comid.tolist())]).max()['CAT_BFI']
    return np.float64(bfi)


def get_bfr_k(gage_daily_por: pd.DataFrame, station_id: str):
    """
    Get the baseflow recession coefficient (K) for the catchment area

    Parameters
    ----------
    gage_daily_por : pd.DataFrame
        The period of record of daily data for a stream gage
    station_id : str
        The USGS station ID for the stream gage

    Returns
    -------
    float
        The baseflow recession coefficient (K) representing the 
        proportion of remaining streamflow on the next time step
    """
    
    # Fill any NaN values with the previous value
    gage_daily_por = gage_daily_por.fillna(method='ffill')
    # Calculate the baseflow recession coefficient (K)
    mrc, bfrec_k = baseflow_recession(gage_daily_por[station_id].values)
    return np.float64(bfrec_k)


def separate_baseflow(Q: pd.Series, bfr_k: float, bfi: float, da: float, method: str):
    """
    Seperate the baseflow from the observed and simulated hydrographs

    Parameters
    ----------
    Q : pd.Series
        The hydrograph time series
    bfr_k : float
        The baseflow recession coefficient (K) representing the 
        proportion of remaining streamflow on the next time step
    bfi : float
        The maximum baseflow index (BFI) value for the catchment area
    da : float
        The drainage area of the catchment at the gage location
    method : str
        The baseflow seperation method to use
    """
    Q = Q.to_numpy(dtype=np.float64)
    if method == "Chapman":
        b_LH = LH(Q)
        baseflow = Chapman(Q, b_LH, a=bfr_k)
    elif method == "Chapman & Maxwell":
        b_LH = LH(Q)
        baseflow = CM(Q, b_LH, a=bfr_k)
    elif method == "Eckhardt":
        b_LH = LH(Q)
        baseflow = Eckhardt(Q, b_LH, a=bfr_k, BFImax=bfi)
    elif method == "Local":
        b_LH = LH(Q)
        baseflow = Local(Q, b_LH, area=da)
    elif method == "None":
        baseflow = np.zeros(Q.shape[0])

    return baseflow


def calc_runoff(obs_df: pd.DataFrame,
                sim_df: pd.DataFrame,
                bfr_k: float,
                bfi: float,
                da: float,
                method: str):
    """
    Seperate the baseflow from the observed and simulated hydrographs

    Parameters
    ----------
    obs_q : pd.DataFrame
        The observed hydrograph time series
    sim_q : pd.DataFrame
        The simulated hydrograph time series
    bfr_k : float
        The baseflow recession coefficient (K) representing the 
        proportion of remaining streamflow on the next time step
    bfi : float
        The maximum baseflow index (BFI) value for the catchment area
    da : float
        The drainage area of the catchment at the gage location
    method : str
        The baseflow seperation method to use

    Returns
    -------
    obs_df : pd.DataFrame
        The observed hydrograph with the baseflow seperated and calculated runoff
    sim_df : pd.DataFrame
        The simulated hydrograph with the baseflow seperated and calculated runoff
    """

    # Add the baseflow to the observed and simulated hydrographs
    obs_df['Observed Baseflow'] = separate_baseflow(obs_df['Observed Hydrograph'], bfr_k, bfi, da, method)
    sim_df['Modeled Baseflow'] = separate_baseflow(sim_df['Modeled Hydrograph'], bfr_k, bfi, da, method)

    # Calculate the storm runoff
    obs_df['Observed Runoff'] = obs_df['Observed Hydrograph'] - obs_df['Observed Baseflow']
    sim_df['Modeled Runoff'] = sim_df['Modeled Hydrograph'] - sim_df['Modeled Baseflow']

    return obs_df, sim_df
