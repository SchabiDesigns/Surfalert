# -*- coding: utf-8 -*-
"""etl

Notes
"""

#_____ IMPORT _____
# core
import datetime as dt
from tqdm import tqdm

# other

import pandas as pd
import geopandas as gpd
import numpy as np

# own
from src.caching import caching, load_credentials
from src import geometries
from src import utilities
from src import meteomatics_api



#_____ VARIABLES _____

CREDS = load_credentials("meteomatics")

ETL_PARAMS = {
    "interval"          : dt.timedelta(minutes=10),
    "model"             : "mix-obs",
    "point_of_interest" : [(47.12885, 9.21567)],  #Quinten
    "distance"          : 50 * 1000, #m
    "startdate"         : dt.datetime(year=2021, month=1, day=1), #max 2 years!
    "enddate"           : dt.datetime(year=2023, month=1, day=1),
    "parameters"        : [m for m in meteomatics_api.MEASUREMENTS.keys() if m.endswith(":kmh") or m in ("msl_pressure:hPa", "t_2m:C", "wind_dir_10m:d", "global_rad:W")]
}


def get_stations_for_parameters_in_range(parameters, **kwargs):
    near_range = geometries.create_point_with_radius(coords=kwargs["point_of_interest"], **kwargs)
    
    df = pd.DataFrame()

    for param in tqdm(parameters):
        stations = meteomatics_api.get_stations_for_parameter_in_time(parameter=param, **kwargs)
        
        if stations is not None:
            stations_filtered = meteomatics_api.filter_stations_by_other_gdf(stations, near_range)
            stations_filtered["parameter"] = param
            df = pd.concat([df, stations_filtered])
        else:
            print("no stations found for", param)
    return geometries.df_to_gdf(df).reset_index()


def get_api_data_for_param_stations(param_stations, **kwargs):
    
    kwargs.pop("parameters")
    if "coords" in kwargs:
        kwargs.pop("coords")
    
    results = pd.DataFrame()
    failed = pd.DataFrame()
    
    for coords in tqdm(param_stations["geometry"].unique()):
        df_set = param_stations[param_stations["geometry"]==coords][["Name","geometry","parameter"]]
        df_set = df_set.drop_duplicates()
        
        coord = utilities.get_coordinates_from_gdf(df_set)
        params = list(df_set["parameter"])
        station_name = df_set["Name"].iloc[0]
        print(station_name,"...")
        print(params)
        try:
            result = meteomatics_api.get_api_data_for_coords(parameters=params, coords=coord, **kwargs)
            #rename to station name
            result = result.reset_index().drop(columns=["lat", "lon"])
            result["station:name"] = station_name
            #add to existing dataframe
            results = pd.concat([results, result])
        except:
            for param in params:
                result = meteomatics_api.get_api_data_for_coords(parameters=[param], coords=coord, **kwargs)
                if result is not None:
                    if result.shape[0]>0:
                        #rename to station name
                        result = result.reset_index().drop(columns=["lat", "lon"])
                        result["station:name"] = station_name
                        #add to existing dataframe
                        results = pd.concat([results, result])
                    else:
                        fail = df_set[df_set["parameter"]==param]
                        failed = pd.concat([failed, fail])
                else:
                    fail = fail = df_set[df_set["parameter"]==param]
                    failed = pd.concat([failed, fail])
                
    param_stations_ = param_stations.copy()
    param_stations_.drop(index=failed.index, inplace=True)
    return param_stations_, results


def structure_result(results):
    # create multiindex
    df = results.pivot_table(index=["validdate"],
                             columns=["station:name"])
    df = df.swaplevel(axis="columns").sort_index(level=0, axis="columns")
    # check for nans
    for column in df.columns:
        nas = df[df[column].isna()]
        if nas.shape[0]>0:
            print("NaN detected in", column)
            print(nas)
    return df