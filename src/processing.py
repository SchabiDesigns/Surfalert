# -*- coding: utf-8 -*-
"""processing

Process data after ETL, adds time relevant features, convert to vectors,
build dataframes, ....

"""

#_____ IMPORT _____
# core
import datetime as dt

# other
import numpy as np
import pandas as pd
import ephem
from tqdm import tqdm

# own
from src import meteomatics_api
from src import utilities
from src import geometries
from src import etl


#_____ VARIABLES _____

sep_string      = ", "
std_params      = etl.ETL_PARAMS


#_____ FUNCTIONS _____

def df_to_flat_columns(df, sep_string=", "):
    if isinstance(df.columns, pd.MultiIndex):
        df_ = df.copy()
        df_.columns = [sep_string.join([n.replace(sep_string.strip(),"") for n in name if isinstance(n,str)]).strip() for name in df_.columns.values]
        df_.sort_index(axis=1)
        return df_
    else:
        print("no multiindex")
        return df


def df_to_stack_columns(df, sep_string=sep_string):
    if isinstance(df.columns, pd.Index):
        df_ = df.copy()
        df_.columns = df_.columns.str.split(sep_string, expand=True)
        df_.sort_index(axis=1)
        return df_
    else:
        print("no index")
        return df


def isNaN(num):
    return num != num


def round_on(x, n=1, mode=""):
    if isNaN(x):
        return x
    else:
        if mode=="up":
            return int(np.ceil(x))
        elif mode=="down":
            return int(np.floor(x))
        else:
            if n>=1:
                return int(np.round(x/n, 0)*n)
            else:
                return np.round(x,int(-np.log10(n)))


def convert_wind_to_vector(v_mag, v_dir):
    v_y = v_mag * np.sin(np.deg2rad(v_dir))
    v_x = v_mag * np.cos(np.deg2rad(v_dir))
    return v_y, v_x


def convert_vector_to_speed_and_dir(v_x, v_y):
    v_mag = np.round(np.linalg.norm([v_x, v_y]),1)
    v_dir = np.round(np.rad2deg(np.arctan(v_x/v_y)),0)
    if v_y<0:
        v_dir+=180
    elif v_x<0:
        v_dir+=360
    return v_mag, v_dir


def convert_df_wind_to_vector(df, sep_string=sep_string):
    transform_back=False
    
    #convert to Multiindex if not multiindex
    if not isinstance(df.columns, pd.MultiIndex):
        df = df_to_stack_columns(df, sep_string=sep_string)
        transform_back=True    
        
    for station in tqdm(df.columns.get_level_values(0).unique()):
        if "wind_dir_10m:d" in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1):
            for param in [column for column in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1) if column.endswith(":kmh")]:
                df[[(station,param+"_x"), (station, param+"_y")]] = df.apply(lambda x: convert_wind_to_vector(x[station, param],x[station, "wind_dir_10m:d"]), axis='columns', result_type='expand')
                df.drop(columns=(station, param), inplace=True)
            df.drop(columns = (station, "wind_dir_10m:d"), inplace=True)
    if transform_back:
        df = df_to_flat_columns(df)
    return df


def convert_df_vector_to_wind(df, sep_string=sep_string):
    transform_back=False
    
    #convert to Multiindex if not multiindex
    if not isinstance(df.columns, pd.MultiIndex):
        df = df_to_stack_columns(df, sep_string=sep_string)
        transform_back=True    
        
    for station in tqdm(df.columns.get_level_values(0).unique()): 
        if "wind_speed_10m:kmh_x" in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1):
            for param in [column for column in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1) if column.endswith(":kmh_x")]:
                df[[(station,param.replace("_x","")), (station, "wind_dir_10m:d")]] = df.apply(lambda x: convert_vector_to_speed_and_dir(x[station, param],x[station, param.replace("_x","_y")]), axis='columns', result_type='expand')
                df.drop(columns=[(station, param), (station, param.replace("_x","_y"))], inplace=True)
        if "wind_gusts_10m:kmh_x" in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1):
            for param in [column for column in df.iloc[:, df.columns.get_level_values(0)==station].columns.get_level_values(1) if column.endswith(":kmh_x")]:
                df[[(station,param.replace("_x","")), (station, "wind_dir_10m:d")]] = df.apply(lambda x: convert_vector_to_speed_and_dir(x[station, param],x[station, param.replace("_x","_y")]), axis='columns', result_type='expand')
                df.drop(columns=[(station, param), (station, param.replace("_x","_y"))], inplace=True)
    if transform_back:
        df = df_to_flat_columns(df)
    return df


def get_rad_of_year(date:dt.datetime) -> float:
    start = date.replace(month=1,day=1,hour=0,minute=0)
    end = start.replace(start.year+1)
    return (date-start).total_seconds() / (end-start).total_seconds() * np.pi * 2


def get_rad_of_day(date:dt.datetime) -> float:
    point = date.hour * 60 + date.minute
    end = 24*60-10
    return (point) / (end) *  np.pi * 2


def add_time_information(df, sep_string=", "):
    transform_back=False
    
    #convert to Multiindex if not multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df = df_to_flat_columns(df, sep_string)
        transform_back=True  
        
    df["datetime"] = df.index
    for period, p_f in {"day":get_rad_of_day, "year":get_rad_of_year}.items():
        df[period] = df["datetime"].apply(p_f)
        for name, f in {"cos":np.cos, "sin":np.sin}.items():
            df[sep_string.join(["time",name+"_"+period])] = df[period].apply(f)
        df.drop(columns=period, inplace=True)
    df.drop(columns="datetime", inplace=True)
    
    if transform_back:
        df = df_to_stack_columns(df, sep_string)
    
    return df


def add_bisendiagramm(df, api_params=std_params, parameters=["msl_pressure:hPa"], sep_string=", "):
    transform_back=False
    
    api_params["parameters"] = parameters
    locations = {
        "Genf"      : (46.1957, 6.09051), 
        "Konstanz"  : (47.6952, 9.1307)
        }
    
    #convert to FlatIndex if multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df = df_to_flat_columns(df, sep_string)
        transform_back=True

    #get data
    results = {}
    for name, coords in locations.items():
        stations_filt = meteomatics_api.filter_stations_by_distance(coords=coords, distance=5000, stations=meteomatics_api.get_all_stations())
        api_params["coords"] = [utilities.get_coordinates_from_gdf(gdf=stations_filt)[0]]
        result = meteomatics_api.get_api_data_for_coords(**api_params)
        result = result.reset_index().set_index("validdate")
        results[name] = result
    diff = results["Genf"].subtract(results["Konstanz"])
    diff.drop(columns=["lat", "lon"], inplace=True)
    
    for parameter in diff.columns:
        df["bise, "+parameter] = diff[parameter]
    
    if transform_back:
        df = df_to_stack_columns(df, sep_string)
        
    return df


def add_föhndiagramm(df, api_params=std_params, parameters=["msl_pressure:hPa"], sep_string=", "):
    transform_back=False
    
    api_params["parameters"] = parameters
    locations = {
        "Zürich"  : (47.3982, 8.5156),
        "Lugano"  : (45.9984, 8.9320)
        }
    
    #convert to FlatIndex if multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df = df_to_flat_columns(df, sep_string)
        transform_back=True

    #get data
    results = {}
    for name, coords in locations.items():
        stations_filt = meteomatics_api.filter_stations_by_distance(coords=coords, distance=5000, stations=meteomatics_api.get_all_stations())
        api_params["coords"] = [utilities.get_coordinates_from_gdf(gdf=stations_filt)[0]]
        result = meteomatics_api.get_api_data_for_coords(**api_params)
        result = result.reset_index().set_index("validdate")
        results[name] = result
    diff = results["Lugano"].subtract(results["Zürich"])
    diff.drop(columns=["lat", "lon"], inplace=True)
    
    for parameter in diff.columns:
        df["föhn, "+parameter] = diff[parameter]
    
    if transform_back:
        df = df_to_stack_columns(df, sep_string)
        
    return df


def add_time_transient_information(df, window=2, sep_string=", "):
    transform_back = False
    
    #convert to Flat if multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df = df_to_flat_columns(df, sep_string)
        transform_back=True
            
    df_diff = df.copy()
    df_diff = df_diff.diff().rolling(window).mean()
    df_diff.columns = [", ".join([col.split(", ")[0], "diff_"+col.split(", ")[1]]) for col in df_diff.columns]
    df_new = pd.concat([df, df_diff], join='inner', axis=1)
    #drop na values due diff and rolling
    df_new.dropna(axis=0, how="any", inplace=True)

    if transform_back:
        df_new = df_to_stack_columns(df_new, sep_string)
    df_new.sort_index(axis=1,level=[0,1],ascending=[True,True], inplace=True)

    return df_new

def get_observer(point_of_interest):
    obs = ephem.Observer()
    stations = meteomatics_api.get_all_stations()
    lat, lon, elevation = stations.loc[stations["Name"]==point_of_interest][["lat", "lon", "Elevation"]].iloc[0]
    obs.lat = str(lat)
    obs.lon = str(lon)
    obs.elevation = float(elevation.replace("m",""))
    return obs


def calculate_angle_of_element(date, obs, element, angle):
    obs.date = date
    element.compute(obs)
    if angle=="az":
        return element.az
    elif angle=="alt":
        return element.alt


def add_astral_information(df, point_of_interest, sep_string=sep_string):
    transform_back=False
    
    obs = get_observer(point_of_interest)
    sun = ephem.Sun()
    moon =  ephem.Moon()
    
    #convert to Multiindex if not multiindex
    if isinstance(df.columns, pd.MultiIndex):
        df = df_to_flat_columns(df, sep_string)
        transform_back=True  
    
    # create ephem date from DateTimeIndex
    df["ephem_date"] = df.index
    df["ephem_date"] = df["ephem_date"].apply(ephem.Date)
    
    # calculate sun and moon
    for e_name, e in {"sun":sun, "moon":moon}.items():
        for angle in ["alt", "az"]:
            for f_name, f in {"sin":np.sin, "cos":np.cos}.items():
                df["_".join([f_name, e_name, angle])] = df["ephem_date"].apply(lambda x: f(calculate_angle_of_element(x, obs, e, angle)))
    df.drop(columns="ephem_date", inplace=True)
    
    if transform_back:
        df = df_to_stack_columns(df, sep_string)
    
    return df


