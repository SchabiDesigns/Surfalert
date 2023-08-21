# -*- coding: utf-8 -*-
"""prediction

Create predictions on new datasets
loading from Meteomatics API

"""



#_____ IMPORT _____
# core
import datetime as dt
import asyncio
import os
import time
import pickle

#other
import pandas as pd
import numpy as np
import plotly.express as px

import schedule

#own
from src import meteomatics_api
from src import geometries
from src import utilities
from src import etl
from src import processing
from src.caching import check_cache

#_____ VARIABLES _____

REL = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")
RESULTS_DIR     = REL + "/predictions/"
MODELS_DIR      = REL + "/models/"
PAR_STAT_DIR    = REL + "/data/"

API_PARAMS      = etl.ETL_PARAMS
UTC_TIMEDIFF    = utilities.get_utc_time_diff()

# best to get this information from model or preprocessing itself...
DATA_WINDOW     = 1 #ANN are wider -> should be in model
ROLLING_WINDOW  = 3
ROLLING_DIFF_WINDOW = 2

#_____ FUNCTIONS _____

# CORE

def load_param_stations(param_root=PAR_STAT_DIR):
    return geometries.df_to_gdf(pd.read_csv(param_root + "param_stations.zip", index_col=0))

PARAM_STATIONS  = load_param_stations()

def load_models(model_root=MODELS_DIR):
    print("loading models...")
    models = {}
    for model in os.listdir(model_root):
        if model.endswith(".pickle"):
            model_name = model.split(".")[0]
            print(model_name)
            if "ColumnTransformer" in model_name:
                with open(model_root + model, 'rb') as handle:
                    ct = pickle.load(handle)
            else:
                with open(model_root + model, 'rb') as handle:
                    models[model_name] = pickle.load(handle)
    return models, ct


# METHODS

def check_for_new_values(model, interval, testdate, param_stations=PARAM_STATIONS, **kwargs):    

    # only one parameter at one coordinate
    test = param_stations.iloc[0:1]
    coords = utilities.get_coordinates_from_gdf(test)
    parameters = list(test["parameter"])
    
    result = meteomatics_api.get_api_data_for_coords(parameters, model, coords, startdate=testdate, enddate=testdate, interval=interval)
    if result is None:
        return False
    else:
        return True


def get_latest_available_enddate(param_stations=PARAM_STATIONS, api_params=API_PARAMS, **kwargs):
    actual = utilities.get_actual_utc_time_on_10min()
    
    iteration=0
    while not check_for_new_values(testdate=actual, **API_PARAMS) and iteration < 6:
            actual -= dt.timedelta(minutes=10)
            iteration += 1

    if iteration>=6:
        print("failed to get last valid timestamp")
    else:
        return actual - dt.timedelta(minutes=10)


def calculate_startdate(enddate, rolling_window=ROLLING_WINDOW+ROLLING_DIFF_WINDOW, data_window=DATA_WINDOW, **kwargs):
    return enddate - dt.timedelta(minutes=(data_window + rolling_window - 2)*10)


def load_data_and_process(param_stations=PARAM_STATIONS, api_params=API_PARAMS, **kwargs):
    _, df = etl.get_api_data_for_param_stations(param_stations, **api_params)
    df = etl.structure_result(df)
    df = processing.convert_df_wind_to_vector(df)
    df = processing.add_bisendiagramm(df)
    df = processing.add_föhndiagramm(df)
    df = processing.add_time_transient_information(df, window=ROLLING_DIFF_WINDOW)
    df = processing.add_time_information(df)
    df = df.rolling(ROLLING_WINDOW).mean()
    df = df.dropna()
    df = processing.df_to_flat_columns(df)
    return df


def make_prediction(df, model, ct):
    try:
        X_prod = ct.transform(df)
        
        #check for same column names, order and check for shape
        X_prod = X_prod[model["X"].columns]
        print("")
        forcast = pd.DataFrame()
        
        for criterion in model["criterions"].keys():
            for time, submodels in model["criterions"][criterion]["submodels"].items():
                column = "_+".join([criterion, time])
                
                if "important" in model:
                    X_prod_ = X_prod.loc[:, model["important"][column]]
                
                #using all models for prediction!
                if "custom_y_hat" in model:
                    if "important" in model:
                        y_hats = df.loc[X_prod_.index, criterion]
                    else:
                        y_hats = df.loc[X_prod.index, criterion]
                    fold=None
                else: # predict with all submodels and building mean                
                    y_hats = pd.DataFrame()
                    for fold, sub_model in submodels.items():
                        if "important" in model:
                            y_hat = sub_model.predict(X_prod_)
                        else:
                            y_hat = sub_model.predict(X_prod)
                        if "pt_Y" in model: #transform back if pt_Y given
                            y_hat = model["pt_Y"].inverse_transform(y_hat.reshape(-1, 1))[:,0]      
                        y_hats["fold" + str(fold)] = y_hat
                    y_hats["mean"] = y_hats.mean(axis=1)
                    y_hats["std"] = y_hats.std(axis=1)
                    error = model['test_scores']
                    error = error[error["criterion"]==criterion]
                    y_hats["error"] = error[error["forcast time"]==time]["mean_absolute_error"].mean()
                    
                #add predictions
                y_hats["criterion"] = criterion
                y_hats.index = X_prod.index + pd.Timedelta(time)
            
                forcast = pd.concat([forcast, y_hats])
                
        forcast.index += pd.Timedelta(UTC_TIMEDIFF)

        return forcast

    except Exception as e:
        print("input not the same as during training!")
        print(e)
        return None
    

def convert_forcasts_to_winddir(df):
    df_ = df.reset_index().pivot(index=["model","validdate"], columns="criterion").melt(ignore_index=False)
    df_ = df_.reset_index().pivot(index=["model", None, "validdate"], columns="criterion")
    df_ = df_.droplevel(level=0, axis=1)
    
    df_ = processing.convert_df_vector_to_wind(df_)
    
    df_ = df_.melt(ignore_index=False).reset_index().pivot(index=["model", "validdate"],columns=["variable","level_1"]).droplevel(level=0, axis=1)
    return df_


def add_annotations(fig, enddate):
    fig.add_vline(x=dt.datetime.now().timestamp() * 1000, row="all", col="all", line_width=1, line_dash="dash", line_color="green", opacity=.5,
        annotation_text="actual time ", annotation_font_color="green", annotation_font_size=10, annotation_textangle=-90)
    
    fig.add_vline(x=enddate.timestamp() * 1000, row="all", col="all", line_width=1, line_dash="dash", line_color="red", opacity=.5,
        annotation_text="latest available dataset ", annotation_font_color="red", annotation_font_size=10, annotation_textangle=-90)
    return fig


def create_forcast_plots(forcasts):
    enddate = forcasts.index.min() - dt.timedelta(minutes=10) - UTC_TIMEDIFF #knowing the first prediction is +10min
    
    figs = {}
    
    title=None#"Vorhersage für Quinten"#<br><sub>" + model["model_name"] + "</sub>"
    df_set = forcasts.copy()
    #df_set["error_norm"] = ((df_set["error"] - df_set["error"].min())/(df_set["error"].max()-df_set["error"].min()))*100
    
    fig1 = px.scatter(df_set, y="mean", size="error", color="model", facet_col="criterion", title=title,
            labels={"mean":"wind gusts [km/h]", "validdate":""},trendline="lowess", trendline_options=dict(frac=0.3))

    fig1 = add_annotations(fig1, enddate)
    fig1.for_each_annotation(lambda a: a.update(text=a.text.split("=")[-1]))
    fig1.update_yaxes(range=[-40, 40])
    figs["Windvektoren"] = fig1
  
    #convert to wind and dir
    forcasts_dir = convert_forcasts_to_winddir(forcasts)
    for supcol in forcasts_dir.columns.get_level_values(0).unique():
        subtitle = "<br><sup>" + supcol + "<sup>"
        df_set = forcasts_dir.loc[:,supcol]
        df_set = df_set.reset_index().set_index("validdate")
        #df_set["error_norm"] = ((df_set["error"] - df_set["error"].min())/(df_set["error"].max()-df_set["error"].min()))*100
        


        if "wind_dir" in supcol:
            fig2 = px.scatter(df_set, y="mean", color="model", size="error", #error_y="std",
                    labels={"validdate":"", 
                            "mean":" ".join(supcol.split(", ")[1].split("_")[:-1]) + " [" + supcol.split(", ")[1].split(":")[1] + "]"},
                            title = title,# + subtitle)
                )
            
            
            fig2.update_layout(
                yaxis = dict(
                    tickmode = 'array',
                    tickvals = [0, 90, 180, 270, 360],
                    ticktext = ['N', 'O', 'S', 'W', 'N']
                )
            )
            fig2 = add_annotations(fig2, enddate)
            fig2.update_yaxes(range=[-45, 405])
            figs["Windrichtung"] = fig2
        else:
            
            fig3 = px.scatter(df_set, y="mean", color="model", size="error", #error_y="std",
                             labels={"validdate":"", 
                            "mean":" ".join(supcol.split(", ")[1].split("_")[:-1]) + " [" + supcol.split(", ")[1].split(":")[1] + "]"},
                            trendline="lowess", trendline_options=dict(frac=0.3),
                            title = title,# + subtitle)
                )
            fig3.update_yaxes(range=[0, 40])
            fig3 = add_annotations(fig3, enddate)
            figs["Windgeschwindigkeit"] = fig3

    return figs


# WHOLE PROCEDURE
def load_latest_datasets(models, ct, savedir=RESULTS_DIR):
        
    print("check for new datasets...")
    with utilities.HiddenPrints():
        enddate = get_latest_available_enddate()
        
    if API_PARAMS["enddate"]==enddate:
        print("already up to date!")
        return None
    else:
        
        API_PARAMS["enddate"] = enddate
        API_PARAMS["startdate"] = calculate_startdate(enddate)
        
        print("loading new data...")
        with utilities.HiddenPrints():
            df = load_data_and_process()
        
        print("make predictions...")
        all_forcasts = pd.DataFrame()
        for model_short_name, model in models.items():
            forcast = make_prediction(df, model, ct)
            if forcast is not None:
                forcast["model"] = model_short_name
                all_forcasts = pd.concat([all_forcasts, forcast])
                
        if all_forcasts.shape[0]>0:
            all_forcasts.to_csv(savedir + "all_forcasts.csv")
            print("update figures...")
            figs = create_forcast_plots(all_forcasts)
            for name, fig in figs.items():
                fig.write_html(savedir + name + ".html")
            return None
        else:
            print("no forcasts could build for dataset")
            return None
