# -*- coding: utf-8 -*-
"""geometries

Notes
"""

#_____ IMPORT _____
# core
import os

# other
import geopandas as gpd
from shapely import Point
import pandas as pd
import fiona

# own


#_____ VARIABLES _____

SRC_SOURCE = os.path.join(os.path.dirname(__file__)) + "/data/"


#_____ FUNCTIONS _____

def create_point_with_radius(coords:list, distance:float, **kwargs) -> gpd.GeoDataFrame:
    """create geopandas dataframe with coords (lat, lon) and given radius in meter

    Args:
        coords (list): coords [(lat, lon)]
        distance (float): radius in meter

    Returns:
        gpd.GeoDataFrame: geopandas dataframe to join
    """
    if isinstance(coords, list):
        coords = coords[0]
    lat, lon = coords

    gdf = gpd.GeoDataFrame(index=[0], crs="EPSG:4326", geometry=[Point(lon, lat)])

    # convert to 7855 to add radius buffer im meter and convert back to 4326
    gdf["geometry"] = gdf.to_crs(epsg=7855).buffer(distance).to_crs(epsg=4326)

    return gdf


def read_kmls(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """read all files of type .kml in folder and return geo data frame

    Args:
        source (str, optional): folderpath. Defaults to SRC_SOURCE.

    Returns:
        gpd.GeoDataFrame: geopandas dataframe of files
    """

    kmls = gpd.GeoDataFrame()
    try:
        for file in os.listdir(source):
            if file.endswith(".kml"):
                name = file[:-4]
                gdf = gpd.read_file(source+file)
                if gdf.shape[0]>1:
                    gdf["Name"] = ["Walensee", "Chur", "Rheintal", "Glarus", "Zürich", "Flums"]
                else:
                    gdf["Name"] = name
                kmls = gpd.GeoDataFrame(pd.concat([kmls, gdf], ignore_index=True), crs=gdf.crs)
    except:
        gpd.io.file.fiona.drvsupport.supported_drivers['KML'] = 'rw'
        for file in os.listdir(source):
            if file.endswith(".kml"):
                name = file[:-4]
                gdf = gpd.read_file(source+file)
                if gdf.shape[0]>1:
                    gdf["Name"] = ["Walensee", "Chur", "Rheintal", "Glarus", "Zürich", "Flums"]
                else:
                    gdf["Name"] = name
                kmls = gpd.GeoDataFrame(pd.concat([kmls, gdf], ignore_index=True), crs=gdf.crs)
    return kmls.loc[:,["Name","geometry"]]


def df_to_gdf(df:pd.DataFrame, crs:str="EPSG:4326", drop_lat_lan=True, **kwargs) -> gpd.GeoDataFrame:
    """convert a dataframe to geometric dataframe by converting lat, lon to point with crs

    Args:
        df (pd.DataFrame): dataset with lat, lon
        crs (str, optional): coordinate refer system. Defaults to "EPSG:4326".

    Returns:
        gdf (gpd.GeoDataFrame): dataset in geopandas format with geometry
    """
    if isinstance(df, gpd.GeoDataFrame):
        print("allready geopandas!")
        return df.copy()
    else:
        gdf = gpd.GeoDataFrame(
            data    = df, 
            geometry= gpd.points_from_xy(df["lon"], df["lat"]),
            crs     = crs
        )
        if drop_lat_lan:
            gdf = gdf.drop(columns=["lat", "lon"])
        return gdf


def gdf_to_df(gdf:gpd.GeoDataFrame, **kwargs) -> pd.DataFrame:
    """convert a geodataframe to dataframe by converting geometry to lat, lon

    Args:
        gdf (gpd.GeoDataFrame): dataset with geometry

    Returns:
        df (pd.DataFrame): dataset in pandas with lat, lon
    """
    if "geometry" not in gdf.columns:
        print("allready pandas!")
        return gdf.copy()
    else:
        df = gdf.copy()
        df["lon"] = df.geometry.x
        df["lat"] = df.geometry.y
        df = df.drop(columns=["geometry"])
        return df


def get_countries(**kwargs) -> gpd.GeoDataFrame:
    """get country border from naturalearth_lowres
    """
    return gpd.read_file(gpd.datasets.get_path('naturalearth_lowres')).drop(columns=["pop_est","gdp_md_est"]).rename(columns={"name":"country"})


def get_switzerland(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """get switzerland border from swisstopo (local loaded)
    """
    return gpd.read_file(source + "swissBOUNDARIES3D_1_4_TLM_LANDESGEBIET.shp").to_crs(epsg=4326)


def get_cantons(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """get canton border from swisstopo (local loaded)
    """
    return gpd.read_file(source + "swissBOUNDARIES3D_1_4_TLM_KANTONSGEBIET.shp").to_crs(epsg=4326)


def get_regions(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """get regions border from swisstopo (local loaded)
    """
    return gpd.read_file(source + "swissBOUNDARIES3D_1_4_TLM_BEZIRKSGEBIET.shp").to_crs(epsg=4326)


def get_territories(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """get territories border from swisstopo (local loaded)
    """
    return gpd.read_file(source + "swissBOUNDARIES3D_1_4_TLM_HOHEITSGEBIET.shp").to_crs(epsg=4326)


def get_customs(source:str=SRC_SOURCE, **kwargs) -> gpd.GeoDataFrame:
    """load custom defined borders from sketch on swisstopo (local loaded)
    """
    return read_kmls(source=source)


