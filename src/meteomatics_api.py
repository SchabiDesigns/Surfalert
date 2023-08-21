# -*- coding: utf-8 -*-
"""geometries

Notes
"""

#_____ IMPORT _____
# core
import datetime as dt

# other

import pandas as pd
import geopandas as gpd
import numpy as np
from meteomatics import api

# own
from src.caching import caching, load_credentials
from src import geometries
from src import utilities


#_____ VARIABLES _____

CREDS = load_credentials("meteomatics")

MODELS = pd.DataFrame(data={
    "mix-obs":          [np.NaN, 10, np.NaN, np.NaN, np.NaN, "station"],
    "mix":              [np.NaN, np.NaN, np.NaN, np.NaN, np.NaN, "global"],
    #"mm-euro1k":        [0.0012, 20, 24*60, 24, np.NaN, "global"],             nicht verfügbar wegen eingeschränkter Lizenz
    "ecmwf-ifs":        [0.0012, 60, 10*24*60, 4, np.NaN, "global"],
    "ecmwf-ens":        [0.0012, 3*60, 15*24*60, 4, 50, "global"],
    "ecmwf-ens-cluster":[1.5, 12*60, 15*24*60, 2, np.NaN, "global"],
    "ecmwf-vareps":     [0.0012, 3*60, 46*24*60, 2/7, np.NaN, "global"],
    "ecmwf-mmsf":       [0.0012, 6*60, 7*30.5*24*60, 1/30.5, np.NaN, "global"],
    "cmc-gem":          [0.0012, 3*60, 6*24*60, 2, np.NaN, "global"],
    "ncep-gfs":         [0.0012, 3*60, 16*24*60, 4, np.NaN, "global"],
    "ncep-gfs-ens":     [0.5, 3*60, 16*24*60, 4, 31, "global"],
    "ukmo-um10":        [0.0012, 1*60, 7*24*60, 4, np.NaN, "global"],
    "mm-swiss1k":       [0.0012, 20, 3*24*60, 4, np.NaN, "Switzerland"],
    "mf-arome":         [0.01, 60, 42*60, 5, np.NaN, "France+"],
    "dwd-icon-eu":      [0.0012, 60, 78*60, 4, np.NaN, "Europe"],
}).T.set_axis(labels=["spatial resolution [°]", "temporal resolution [min]", "lead time [min]", "updates per day", "ensemble [n]", "region"],axis=1).reset_index(names="model")

MEASUREMENTS = {
    "t_2m:C":                   "Temperatur 2m über Boden",
    "relative_humidity_2m:p":   "rel. Luftfeuchtigkeit 2m über Boden",
    "dew_point_2m:C":           "Taupunkt 2m über Boden",
    "precip_10min:mm":          "Niederschlag 10min",
    "global_rad:W":             "Strahlungsleistung",
    "sun_zenit:d":              "Sonnenstand",
    "wind_speed_10m:kmh":       "Windgeschwindigkeit 10m über Boden (mean 10min)",
    "wind_gusts_10m:kmh":       "Windgeschwindigkeit 10m über Boden (max 10min)",
    "wind_dir_10m:d":           "Windrichtung 10m über Boden (mean 10min)",
    "msl_pressure:hPa":         "Luftdruck reduziert auf Meereshöhe",
    "msl_pressure_icao:hPa":    "Luftdruck reduziert auf Meereshöhe nach ICAO",
    "sfc_pressure:hPa":         "Luftdruck auf Oberfläche",
    "number_lightnings:x":      "Anzahl Blitze",                    # muss alternativ geladen werden!
    "t_sea_sfc:C":              "Wasseroberflächentemperatur",
    "total_cloud_cover:p":      "Bewölkung",
    "ceiling_height_agl:m":     "Höhe der Wolkendecke",
    "visibility:m":             "Sichtbereich"
}

ERRORCODES = {
    -999: np.nan,   #data is not available (this rarely occurs, if so, try another source)
    -888: np.nan,   #parameter specific reserved value (check the description of the corresponding parameter, e.g. sunset if the sun does not set at the queried location and time)
    -777: np.nan,   #parameter specific reserved value (check the description of the corresponding parameter, e.g. sunset if the sun does not set at the queried location and time)
    -666: np.nan    #data not applicable (e.g. cloud top temperature if there are no clouds)
}


#_____ FUNCTIONS _____

# stations


def get_all_stations() -> pd.DataFrame:
    """fetch all stations from meteomatics

    Returns:
        pd.DataFrame: metematics stations
    """

    try:
        stations = api.query_station_list(**CREDS)
        stations = stations.replace(ERRORCODES).dropna(how="all", axis=1)
        return stations
    except Exception as e:
        print("Failed, the exception is {}".format(e))
        return None


def get_stations_for_parameter(parameter:list or str, **kwargs) -> pd.DataFrame:
    """fetch all stations from meteomatics which measure the given parameter
    ATTENTION: Iterating over parameter will not give same as when passing list!
    When passing list only stations which measure all parameters in list will returned

    Args:
        parameter (str): parameter looking for

    Returns:
        pd.DataFrame: dataframe with requested parameter
    """

    try:
        stations = api.query_station_list(
            parameters  = parameter,
            **CREDS
        )
        stations = stations.replace(ERRORCODES).dropna(how="all", axis=1)
        return stations
    
    except Exception as e:
        print("Failed, the exception is {}".format(e))
        return None


def get_stations_for_parameter_in_time(parameter:str, startdate:dt.datetime, enddate:dt.datetime, **kwargs) -> pd.DataFrame:
    """fetch all stations from meteomatics which measure the given parameter dict
    
    Args:
        parameter (str): parameter looking for
        startdate (dt.datetime): start datetime
        enddate (dt.datetime): end datetime

    Returns:
        pd.DataFrame: dataframe with requested parameter
    """

    try:
        stations = api.query_station_list(
            startdate   = startdate,
            enddate     = enddate,
            parameters  = parameter,
            **CREDS
        )
        stations = stations.replace(ERRORCODES).dropna(how="all", axis=1)
        return stations
    
    except Exception as e:
        print("Failed, the exception is {}".format(e))
        return None


def filter_stations_by_distance(stations:pd.DataFrame, coords:list, distance:float, **kwargs) -> gpd.GeoDataFrame:
    """filter stations by given point and distance

    Args:
        stations (pd.DataFrame): stations to be filtered
        coords (list): point of interest
        distance (float): distance from point in m

    Returns:
        gdf (gpd.GeoDataFrame): filtered dataset in geopandas format with geometry
    """

    stations_geo = geometries.df_to_gdf(stations)
    
    area = geometries.create_point_with_radius(coords, distance)
    gdf = stations_geo.sjoin(area).drop(columns="index_right")

    return gdf


def filter_stations_by_country(stations:pd.DataFrame, country:str, **kwargs) -> gpd.GeoDataFrame:
    """filter stations by given country name

    Args:
        stations (pd.DataFrame): stations to be filtered
        country (str): country name like "Switzerland"

    Returns:
        gdf (gpd.GeoDataFrame): filtered dataset in geopandas format with geometry
    """
    
    stations_geo = geometries.df_to_gdf(stations)
    
    countries = geometries.get_countries()
    area = countries[countries["country"]==country]

    gdf = stations_geo.sjoin(area).drop(columns="index_right")
    
    return gdf


def filter_stations_by_custom(stations:pd.DataFrame, name:str, **kwargs) -> gpd.GeoDataFrame:
    """filter stations by given custom region

    Args:
        stations (pd.DataFrame): stations to be filtered
        name (str): custom name

    Returns:
        gdf (gpd.GeoDataFrame): filtered dataset in geopandas format with geometry
    """
    
    stations_geo = geometries.df_to_gdf(stations)
    
    customs = geometries.get_customs()
    area = customs[customs["Name"]==name]

    gdf = stations_geo.sjoin(area).drop(columns="index_right")
    
    return gdf


def filter_stations_by_other_gdf(stations:pd.DataFrame, other:gpd.GeoDataFrame, **kwargs):
    """filter stations by given geometries in other geodataframe

    Args:
        stations (pd.DataFrame): stations to be filtered
        other (gpd.GeoDataFrame): gdf with geometries to join with

    Returns:
        gdf (gpd.GeoDataFrame): filtered dataset in geopandas format with geometry
    """

    stations_geo = geometries.df_to_gdf(stations)
    
    gdf = stations_geo.sjoin(other).drop(columns="index_right")
    
    return gdf

# data


def get_api_data_for_coords(parameters:list, model:pd.DataFrame or str, coords:list, startdate:dt.datetime, enddate:dt.datetime, interval:dt.timedelta, **kwargs) -> pd.DataFrame:
    """get data from meteomatics api depending on inputs. Iterate through models

    Args:
        parameters (list): parameters see also api documentation
        model (pd.DataFrame or str): use column "model" in dataframe or string
        coords (list): list of coordinates or single location
        startdate (dt.datetime): start datetime
        enddate (dt.datetime): end datetime
        interval (dt.timedelta): time resolution

    Returns:
        pd.DataFrame: return a multi index data frame
    """

    try:
        df = api.query_time_series(
            coordinate_list = coords,
            startdate       = startdate,
            enddate         = enddate,
            interval        = interval,
            model           = model,
            parameters      = parameters,
            **CREDS
        )
        return df
  
    except Exception as e:
        if len(parameters)>1:
            print("Loading all parameter at once failed! The exception is {}".format(e))
            print("Auto checking parameters")
            df = pd.DataFrame()
            for parameter in parameters:
                try:
                    df[parameter] = api.query_time_series(
                        coordinate_list = coords,
                        startdate       = startdate,
                        enddate         = enddate,
                        interval        = interval,
                        model           = model,
                        parameters      = [parameter],
                        **CREDS
                    )
                    print(parameter, "passed")
                except Exception as e:
                    print("Error with parameter", parameter)
                    print("-> Failed, the exception is {}".format(e))
            return df
        else:
            print(e)
            return None  
