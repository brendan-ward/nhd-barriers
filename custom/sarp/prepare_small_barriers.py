import os
from time import time
import pandas as pd
import geopandas as gp

from nhdnet.io import serialize_gdf, deserialize_gdf, deserialize_sindex
from nhdnet.geometry.lines import snap_to_line

from constants import REGION_GROUPS, REGIONS, CRS, SNAP_TOLERANCE


src_dir = "/Users/bcward/projects/data/sarp"
os.chdir(src_dir)

all_sb = gp.read_file(
    "Blank_Schema_Road_Barriers_WebViewer_DraftTwo.gdb",
    layer="Road_Barriers_WebViewer_Metrics_Schema_11272018",
).rename(columns={"AnalysisId": "AnalysisID"})

print("Read {} small barriers".format(len(all_sb)))

# Filter by Potential_Project, based on guidance from Kat
keep = [
    "Severe Barrier",
    "Moderate Barrier",
    "Inaccessible",
    "Significant Barrier",
    "No Upstream Channel",
    "Indeterminate",
    "Potential Project",
    "Proposed Project",
]

all_sb = all_sb.loc[all_sb.Potential_Project.isin(keep)][
    ["AnalysisID", "HUC12", "geometry"]
].to_crs(CRS)

print("{} small barriers left after filtering".format(len(all_sb)))

all_sb["joinID"] = all_sb.AnalysisID
all_sb["HUC2"] = all_sb.HUC12.str[:2]

snapped = None

for group in REGION_GROUPS:
    print("\n----- {} ------\n".format(group))

    os.chdir("{0}/nhd/region/{1}".format(src_dir, group))

    sb = all_sb.loc[all_sb.HUC2.isin(REGION_GROUPS[group])].copy()
    print("Selected {0} small barriers in region {1}".format(len(sb), group))

    if len(sb):
        print("Reading flowlines")
        flowlines = deserialize_gdf("flowline.feather").set_index("lineID", drop=False)
        print("Read {0} flowlines".format(len(flowlines)))

        print("Reading spatial index on flowlines")
        sindex = deserialize_sindex("flowline.sidx")

        print("Snapping small barriers")
        sb = snap_to_line(sb, flowlines, SNAP_TOLERANCE, sindex=sindex)
        print("{} small barriers were successfully snapped".format(len(sb)))

        if snapped is None:
            snapped = sb
        else:
            snapped = snapped.append(sb, sort=False, ignore_index=True)

print("\n--------------\n")
print("Serializing {0} snapped barriers out of {1}".format(len(snapped), len(all_sb)))
serialize_gdf(snapped, "{}/snapped_small_barriers.feather".format(src_dir), index=False)