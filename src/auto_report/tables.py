# -*- coding: utf-8 -*-

# Imports #####################################################################

import pandas as pd
import geopandas as gpd
from pygeohydro import NWIS
from hy_river import filter_nid

# Functions ###################################################################


def fill_proj_table(report_keywords: dict, proj_table: dict):
    """
    Update the report_keywords dictionary with the values from the proj_table dictionary.

    Parameters
    ----------
    report_keywords : dict
        Dictionary containing the report keywords.
    proj_table : dict
        Dictionary containing the projection details.

    Returns
    -------
    report_keywords : dict
        Updated dictionary containing the report keywords.
    """
    # Update Table 1: Projection Details
    report_keywords["table01_projcs"] = proj_table["projcs"]
    report_keywords["table01_geogcs"] = proj_table["geogcs"]
    report_keywords["table01_datum"] = proj_table["datum"]
    report_keywords["table01_ellipsoid"] = proj_table["ellipsoid"]
    report_keywords["table01_method"] = proj_table["method"]
    report_keywords["table01_authority"] = proj_table["authority"]
    report_keywords["table01_code"] = str(proj_table["code"])
    report_keywords["table01_unit"] = proj_table["unit"]
    return report_keywords


def fill_gage_table(report_keywords: dict, df_gages_usgs: pd.DataFrame):
    """
    Update the report_keywords dictionary with the values from the df_gages_usgs DataFrame.

    Parameters
    ----------
    report_keywords : dict
        Dictionary containing the report keywords.
    df_gages_usgs : pd.DataFrame
        DataFrame containing the USGS gage information.

    Returns
    -------
    report_keywords : dict
        Updated dictionary containing the report keywords.
    """
    df_gages_usgs = df_gages_usgs.reset_index(drop=True)
    nwis = NWIS()
    for idx, row in df_gages_usgs.iterrows():
        station_id = row["site_no"]  # 08059590
        station_name = row["station_nm"]  # Willow Creek at Highway 80
        begin_date = row["begin_date"].strftime("%Y-%m-%d")
        end_date = row["end_date"].strftime("%Y-%m-%d")
        # Update the report text
        report_keywords[f"table03_gage0{idx+1}_name"] = station_name
        report_keywords[f"table03_gage0{idx+1}_id"] = station_id
        report_keywords[f"table03_gage0{idx+1}_por"] = f"{begin_date}-{end_date}"
        try:
            site_info = nwis.get_info({"site": station_id}, expanded=True)
            drainage_area = site_info["drain_area_va"].values[0]  # square miles
            report_keywords[f"table03_gage0{idx+1}_area"] = f"{drainage_area:,}"
        except Exception as e:
            print(f"Error retrieving site info for {station_id}: {e}")
            report_keywords[f"table03_gage0{idx+1}_area"] = "Data Unavailable"
            continue

    return report_keywords


def fill_nid_dams_table(
    report_keywords: dict,
    nid_parquet_file_path: str,
    model_perimeter: gpd.GeoDataFrame,
    nid_dam_height: int,
):
    """
    Update the report_keywords dictionary with the values from the NID dams within the model perimeter.

    Parameters
    ----------
    report_keywords : dict
        Dictionary containing the report keywords.
    nid_parquet_file_path : str
        Path to the NID Parquet file.
    model_perimeter : gpd.GeoDataFrame
        GeoDataFrame containing the model perimeter.
    nid_dam_height : int
        Minimum dam height to consider.

    Returns
    -------
    report_keywords : dict
        Updated dictionary containing the report keywords
    """

    # Query all NID dams within the domain
    nid_df = filter_nid(nid_parquet_file_path, model_perimeter, nid_dam_height)
    # sort the dams by height
    nid_df = nid_df.sort_values(by="damHeight", ascending=False).reset_index(drop=True)
    for idx, row in nid_df.iterrows():
        # Update the report text
        report_keywords[f"table06_dam0{idx+1}_id"] = row["nidId"]
        report_keywords[f"table06_dam0{idx+1}_name"] = row["name"]
        report_keywords[f"table06_dam0{idx+1}_height"] = str(row["damHeight"])

    return report_keywords


def fill_computation_settings_table(
    report_keywords: dict, plan_params: dict, plan_attrs: dict, plan_idx: int
):
    """
    Update the report_keywords dictionary with the values from the plan_params and plan_attrs dictionaries.

    Parameters
    ----------
    report_keywords : dict
        Dictionary containing the report keywords.
    plan_params : dict
        Dictionary containing the plan parameters.
    plan_attrs : dict
        Dictionary containing the plan attributes.
    plan_idx : int
        Index of the plan. One of [1, 2, 3, 4, 5, 6].

    Returns
    -------
    report_keywords : dict
        Updated dictionary containing the report keywords.
    """

    # Update Table 9: 2D Comutational Solver Tolerances and Settings
    report_keywords[f"plan0{plan_idx}_iwf"] = str(round(plan_params["2D Theta"],2))
    report_keywords[f"plan0{plan_idx}_wst"] = str(round(plan_params["2D Water Surface Tolerance"],2))
    report_keywords[f"plan0{plan_idx}_volt"] = str(round(plan_params["2D Volume Tolerance"],2))
    report_keywords[f"plan0{plan_idx}_max_iter"] = str(int(plan_params["2D Maximum Iterations"]))
    report_keywords[f"plan0{plan_idx}_fts"] = plan_attrs["Computation Time Step Base"]
    report_keywords[f"plan0{plan_idx}_eqn"] = plan_params["2D Equation Set"]
    report_keywords[f"plan0{plan_idx}_output_interval"] = plan_attrs["Base Output Interval"]

    return report_keywords


def evaluate_metrics(x):
    """
    Evaluate the calibration metrics according to the USACE guidelines

    Parameters
    ----------
    x : pd.DataFrame
        DataFrame containing the calibration metrics. Columns include NSE, RSR, PBIAS, and R2. Indeces are the gage IDs.

    Returns
    -------
    df : pd.DataFrame
        DataFrame containing the evaluation of the calibration metrics. Columns include NSE, RSR, PBIAS, and R2. Indeces are the gage IDs.
    """
    # make a copy of the dataframe
    df = x.copy()
    df["R2"] = df["R2"].apply(
        lambda x: (
            "Very Good"
            if x > 0.65 and x <= 1.0
            else (
                "Good"
                if x > 0.55 and x <= 0.65
                else ("Satisfactory" if x > 0.4 and x <= 0.55 else "Unsatisfactory")
            )
        )
    )
    df["NSE"] = df["NSE"].apply(
        lambda x: (
            "Very Good"
            if x > 0.65 and x <= 1.0
            else (
                "Good"
                if x > 0.55 and x <= 0.65
                else ("Satifactory" if x > 0.4 and x <= 0.55 else "Unsatisfactory")
            )
        )
    )
    df["RSR"] = df["RSR"].apply(
        lambda x: (
            "Very Good"
            if x > 0 and x <= 0.6
            else (
                "Good"
                if x > 0.6 and x <= 0.7
                else ("Satisfactory" if x > 0.7 and x <= 0.8 else "Unsatisfactory")
            )
        )
    )
    df["PBIAS"] = df["PBIAS"].apply(
        lambda x: (
            "Very Good"
            if x <= 15
            else (
                "Good"
                if x >= 15 and x < 20
                else ("Satifactory" if x >= 20 and x < 30 else "Unsatisfactory")
            )
        )
    )
    return df


def fill_calibration_metrics_table(
    report_keywords: dict, plan_index: int, metrics_df: pd.DataFrame, parameter: str
):
    """
    Update the report_keywords dictionary with the values from the metrics_df DataFrame.

    Parameters
    ----------
    report_keywords : dict
        Dictionary containing the report keywords.
    plan_index : int
        Index of the plan. One of [1, 2, 3, 4, 5, 6].
    metrics_df : pd.DataFrame
        DataFrame containing the calibration metrics. Columns include NSE, RSR, PBIAS, and R2. Indeces are the gage IDs.
    parameter : str
        Parameter to be evaluated. One of 'Flow' or 'Stage'.
        
    Returns
    -------
    report_keywords : dict
        Updated dictionary containing the report keywords.
    """
    row_index = 1
    metrics_df = metrics_df.round(2)
    parameter = parameter.lower()
    for gage_id, row in metrics_df.iterrows():
        report_keywords[f"plan0{plan_index}_gage0{row_index}"] = gage_id
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_nse"] = str(
            row["NSE"]
        )
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_rsr"] = str(
            row["RSR"]
        )
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_pbias"] = str(
            row["PBIAS"]
        )
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_r2"] = str(row["R2"])
        row_index = row_index + 1

    row_index = 1
    eval_df = evaluate_metrics(metrics_df)
    for gage_id, row in eval_df.iterrows():
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_nse_eval"] = row[
            "NSE"
        ]
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_rsr_eval"] = row[
            "RSR"
        ]
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_pbias_eval"] = row[
            "PBIAS"
        ]
        report_keywords[f"plan0{plan_index}_gage0{row_index}_{parameter}_r2_eval"] = row["R2"]
        row_index = row_index + 1
    return report_keywords
