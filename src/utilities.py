# -*- coding: utf-8 -*-
"""utilities

Notes
"""

#_____ IMPORT _____
# core
import sys
import os
import datetime as dt

# other
import numpy as np
import geopandas as gpd
import pandas as pd
import folium


#_____ VARIABLES _____


#_____ FUNCTIONS _____

def get_actual_utc_time_on_10min():
    actual = dt.datetime.now(dt.timezone.utc).replace(second=0, microsecond=0)
    actual = actual.replace(minute=int(actual.minute/10)*10) #abrunden
    return actual


def get_utc_time_diff():
    utc = dt.datetime.now(dt.timezone.utc).hour
    local = dt.datetime.now().hour
    return dt.timedelta(hours=local - utc)


def get_coordinates_from_gdf(gdf:gpd.GeoDataFrame) -> list:
    """get unique coordinates from geodataframe

    Returns:
        coords (list): coords as list [(x1,y1), (x2,y2)] 
    """

    coords = list(gdf["geometry"].unique())
    coords = [(point.y, point.x) for point in coords]

    return coords


def convert_location_to_string(location:list) -> str:
    """convert list of positions to query stations from api.
    - get_stations_in_point_range

    Args:
        location (list): [(lat_1, lon_1), (lat_n, lon_n)]

    Returns:
        str: api compatible string
    """

    loc = location.copy()

    if not isinstance(loc, str):
        locs = [",".join([str(lat), str(lon)]) for lat, lon in np.round(loc,5)]
        return "_".join(locs)
    else:
        return loc


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]


def create_map(gdf:pd.DataFrame, name:str):
    """create a folium map with gdf points and name

    Args:
        gdf (pd.DataFrame): dataframe with geometry points
        name (str): description of points

    Returns:
        _type_: folium map
    """
    m = folium.Map()
    gdf.explore(m=m, name=name)
    folium.TileLayer('Stamen Terrain', control=True).add_to(m)  # use folium to add alternative tiles
    folium.LayerControl().add_to(m)  # use folium to add layer control
    m.fit_bounds(m.get_bounds(), padding=(30, 30))
    return m


def df_to_flat_index(df:pd.DataFrame)->pd.DataFrame:
    """convert dataframe to flat index by creating index out of multiindex

    Args:
        df (pd.DataFrame): multiindex dataframe

    Returns:
        pd.DataFrame: dataframe flat
    """
    
    if isinstance(df.index, pd.MultiIndex):
        df_ = df.copy()
        df_pivot = df_.reset_index().pivot_table(
            index=["validdate"],
            columns=["lat", "lon"]
            )
        df_flat = df_pivot.copy()
        df_flat.columns = df_flat.columns.to_flat_index()
        df_flat.columns = [','.join([col[0], "[" + str(col[1]) +","+ str(col[2]) + "]"]).strip() for col in df_flat.columns.values]
        return df_flat
    else:
        print("allready flat index")
        return df


class HiddenPrints:
    #https://stackoverflow.com/questions/8391411/how-to-block-calls-to-print
    def __enter__(self):
        self._original_stdout = sys.stdout
        sys.stdout = open(os.devnull, 'w')

    def __exit__(self, exc_type, exc_val, exc_tb):
        sys.stdout.close()
        sys.stdout = self._original_stdout