import os
from auto_report import main_auto_report

if __name__ == "__main__":
    # Determine where the script is located
    currDir = os.path.dirname(os.path.realpath(__file__))
    # Shift one level up to the local root directory
    rootDir = os.path.abspath(os.path.join(currDir, "..", ".."))

    ####### Begin User Input #######
    # Example paths to GEOM and PLAN HDF files for the Trinity Pilot Study

    # EaFT Lavon
    GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/EaFT_Lavon.g06.hdf"
    PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/EaFT_Lavon.p01.hdf"

    # R-Chambers Creek
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/R-ChambersCr/R-ChambersCr/Trinity_1203_R_Ch_Cr.g01.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/R-ChambersCr/R-ChambersCr/Trinity_1203_R_Ch_Cr.p01.hdf"

    # Denton
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.g01.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.p03.hdf"

    # C Mill Creek
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/C-MillCrk/Model/C_MillCrk_1203_Upper_New/C_MillCrk_1203_Upper_New.g02.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/C-MillCrk/Model/C_MillCrk_1203_Upper_New/C_MillCrk_1203_Upper_New.p03.hdf"

    # LT Below Richland
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/LT-BelowRichlandChambers/Model/LT-BelowRichlandCha.g02.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/LT-BelowRichlandChambers/Model/LT-BelowRichlandCha.p01.hdf"

    DOMAIN_ID = None  # Optional input for the domain ID. If multiple domains are found, the user must specify a domain ID.
    STREAM_THRESHOLD = 20  # Filter to main streams that occur X times or more within the NHDPlus HR network
    NLCD_RES = 30  # 30-meter resolution of the NLCD data
    NLCD_YR = 2019  # 2019 NLCD data
    WSE_ERROR_THRESHOLD = 0.2  # Threshold for the histogram's x-axis
    NUM_BINS = 100  # Number of bins for the histogram
    ####### End User Input #######

    # Main function to run the auto report
    main_auto_report(
        GEOM_HDF_PATH,
        PLAN_HDF_PATH,
        DOMAIN_ID,
        STREAM_THRESHOLD,
        NLCD_RES,
        NLCD_YR,
        WSE_ERROR_THRESHOLD,
        NUM_BINS,
        rootDir,
    )
