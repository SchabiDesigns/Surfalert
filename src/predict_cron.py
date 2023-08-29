# -*- coding: utf-8 -*-
"""cronjob for predictions

load dataset from meteomatics process them and make predictions
"""

#_____ IMPORT _____
# core
import time

#others
import schedule

#own
from src import prediction


# MAIN

if __name__ == "__main__":

    first = True
    while True:
        if first:
            print("load models...")
            ML_MODELS, CT = prediction.load_models()
            print("define jobs...")
            schedule.every(2).minutes.do(prediction.load_latest_datasets, models=ML_MODELS, ct=CT)
            first = False
            print("start loop every 2min...")
            
        schedule.run_pending()
        time.sleep(1)