import os
import sys

# Determine where the script is located
currDir = os.path.dirname(os.path.realpath(__file__))
# Shift one level up to the local root directory
rootDir = os.path.abspath(os.path.join(currDir, ".."))
# Add the src directory to sys.path
srcDir = os.path.join(rootDir, "src", "auto_report")
sys.path.append(srcDir)

from auto_report import main_auto_report

if __name__ == "__main__":
    ####### Begin User Input #######
    # Example paths to GEOM and PLAN HDF files for the Trinity Pilot Study

    # Denton
    GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Trinity_1203_Denton.g01.hdf"
    PLAN_HDF_FILES = [".p01.hdf", ".p02.hdf", ".p03.hdf", ".p04.hdf"]
    NLCD_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/Denton/Trinity_1203_Denton/Reference/LandCover/Denton_LandCover.tif"

    # EaFT Lavon
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/EaFT_Lavon.g06.hdf"
    # PLAN_HDF_FILES = [".p01.hdf", ".p02.hdf", ".p05.hdf", ".p06.hdf"]
    # NLCD_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/EaFT-Lavon/Model/Land Classification/NLCD_2021_Trinity_ClipLavon.tif"

    # R-Chambers Creek
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/R-ChambersCr/R-ChambersCr/Trinity_1203_R_Ch_Cr.g01.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/R-ChambersCr/R-ChambersCr/Trinity_1203_R_Ch_Cr.p01.hdf"

    # C Mill Creek
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/C-MillCrk/Model/C_MillCrk_1203_Upper_New/C_MillCrk_1203_Upper_New.g02.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/C-MillCrk/Model/C_MillCrk_1203_Upper_New/C_MillCrk_1203_Upper_New.p03.hdf"

    # LT Below Richland
    # GEOM_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/LT-BelowRichlandChambers/Model/LT-BelowRichlandCha.g02.hdf"
    # PLAN_HDF_PATH = "s3://trinity-pilot/Checkpoint1-ModelsForReview/Hydraulics/LT-BelowRichlandChambers/Model/LT-BelowRichlandCha.p01.hdf"

    DOMAIN_ID = None  # Optional input for the domain ID. If multiple domains are found, the user must specify a domain ID.
    STREAM_THRESHOLD = 20  # Filter to main streams that occur X times or more within the NHDPlus HR network
    WSE_ERROR_THRESHOLD = 0.2  # Threshold for the histogram's x-axis
    NUM_BINS = 100  # Number of bins for the histogram
    NID_DAM_HEIGHT = 20  # Dam height threshold for the NID inventory
    GAGE_COLLECTION_METHOD = "Only collect gages that provide current data" # or "Collect all gages, old and current"
    ####### End User Input #######

    REPORT_PATH = r"/workspaces/ffrd-auto-reports/src/assets/FFRD-RAS-Report-Automated-Template.docx"
    NID_PARQUET_PATH = r"/workspaces/ffrd-auto-reports/src/assets/nid_inventory.parquet"
    os.makedirs(r"/workspaces/ffrd-auto-reports/session/test", exist_ok=True)
    OUTPUT_PATH = r"/workspaces/ffrd-auto-reports/session/test"

    # Main function to run the auto report
    main_auto_report(
        GEOM_HDF_PATH,
        PLAN_HDF_FILES,
        NLCD_PATH,
        REPORT_PATH,
        DOMAIN_ID,
        GAGE_COLLECTION_METHOD,
        STREAM_THRESHOLD,
        WSE_ERROR_THRESHOLD,
        NUM_BINS,
        NID_PARQUET_PATH,
        NID_DAM_HEIGHT,
        OUTPUT_PATH,
        active_streamlit=False,
    )
