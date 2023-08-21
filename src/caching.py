# -*- coding: utf-8 -*-
"""caching

Some methods to reduce bandwith or calculation time by caching method results as pickle files

"""

#_____ IMPORT _____
# core
import pickle
import datetime as dt
import os

# other
import numpy as np
import pandas as pd

# own
from src import utilities


#_____ VARIABLES _____

REL = os.path.dirname(os.path.abspath(__file__)).replace("\\","/")
CACHE_FOLDER = "cache"


#_____ FUNCTIONS _____

def caching(func):
    """wrap a given function to check for cache and store to cache. 
    function name and params will be taken to create id.

    Args:
        func (function): a function call which the result should be cached

    Returns:
        object: result of function
    """
    def wrapper(*args, **kwargs):
        id = func.__name__
        id += "(" + create_param_id(kwargs) + ")"
        #print("generated cache_id:", id)
        result = check_cache(id)
        if result is not None:
            return result
        else:
            result = func(*args, **kwargs)
            save = True
            
            # check if result exists
            if result is None:
                save= False
            if isinstance(result, pd.DataFrame):
                if result.empty:
                    save = False
            
            if save:
                if not save_to_cache(result, id):
                    print("error while saving",id)
                return result
            else:
                print("\nATTENTION: Will not cache result, because it is None or empty!\n")

    return wrapper


def create_param_id(params:dict) -> str:
    """try to create unique id for given parameters to cache locally

    Args:
        params (dict): set of parameters

    Returns:
        str: unique ide to cache
    """

    id = []
    
    for key, value in params.items():
        if isinstance(value, dt.datetime):
            s = value.strftime("%d.%m.%y")
            id.append(s)
        elif isinstance(value, dt.timedelta):
            s = str(int(value.seconds/60)) + "min"
            id.append(s)
        elif isinstance(value, (list,tuple)):
            if isinstance(value, tuple):
                value = [value]
            value.sort()
            if "coords" in key:
                s = utilities.convert_location_to_string(value)
            else:
                s = "],".join(value).replace(":","[").replace("_","-") + "]"
            id.append(s)
        elif isinstance(value, str):
            id.append(value)
        elif isinstance(value, (int, float)):
            id.append(str(np.round(value,0)))
        #else:
        #   if isinstance(value, pd.DataFrame):
        #       print("df has not been added to cache-id")
        #   else:
        #       print(str(value), "has not been added to cache-id")
    return "_".join(id).replace(":","-")


def check_cache(id:str, folder:str=CACHE_FOLDER):
    """check if id already exist in cache 

    Args:
        id (str): id of cache file
        folder (str, optional): dir to cache folder. Defaults to SRC_CACHE.

    Returns:
        object or None: returns object if id in cache.
    """

    try:
        filepath = "/".join([REL,folder,id]) + ".pickle"
        with open(filepath, 'rb') as handle:
            data = pickle.load(handle)
        print("load from cache")
        return data
    except:
        return None


def save_to_cache(to_cache, id:str, folder:str=CACHE_FOLDER) -> bool:
    """cache file as pickle to cache location dir

    Args:
        to_cache (object): object to cache
        id (str): id of object as name
        folder (str, optional): dir of cache folder. Defaults to SRC_CACHE.

    Returns:
        bool: cache success 
    """

    try:
        filepath = "/".join([REL,folder,id]) + ".pickle"
        with open(filepath, "wb") as handle:
            pickle.dump(to_cache, handle, protocol=pickle.HIGHEST_PROTOCOL)
        print("save to cache")
        return True
    except:
        return False


def load_credentials(application, folder:str=CACHE_FOLDER) -> dict:
    """load api credentials from local variable. 
    if the credentials cannot be found a variable will be created due input fields

    Args:
        folder (str, optional): dir where creds are saved. Defaults to SRC_CACHE.

    Returns:
        dict: credentials in form of dictionary
    """

    username = None
    password = None
    credentials = None
    
    filepath = "/".join([REL,folder,application.upper()]) + ".pickle"
    try:
        with open(filepath, 'rb') as handle:
            credentials = pickle.load(handle)
        return credentials
    
    except Exception as e:
        username = input("Credentials not found for API. Please enter username:")
        if username:
            password = input("Please enter password:")
            if password:
                credentials = {
                    "username":str(username),
                    "password":str(password)
                    }
                if save_to_cache(credentials, application.upper(), folder):
                    return credentials
            else:
                print("Input Escaped")
                return None
        else:
            print("Input Escaped")
            return None