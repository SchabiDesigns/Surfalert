import streamlit as st
import streamlit.components.v1 as components
from datetime import time, timedelta
from numpy.random import randint

from src import telegram
import asyncio
import pickle
import os

st.set_page_config(
    page_title="Alarm",
    page_icon="🚨",
    layout="wide"
)

st.header("Alarm konfigurieren")
st.sidebar.subheader("Einstellungen")

#CONFIG PAGE

SURFSPOTS = [
    "Quiten",
    #"Tiefenwinkel",
    ]
CLIENTS = [
    "Wähle einen Nachrichtendienst aus...", "Telegram", #"E-Mail", "WhatsApp"
    ]
LEVELS = [
    "Anfänger", "Forgeschritten", "PRO!"
    ]

CONFIGURATION_DIR = "configurations/"

if 'verified' not in st.session_state:
    st.session_state["verified"] = False
if 'code' not in st.session_state:
    st.session_state["code"] = None
if 'test' not in st.session_state:
    st.session_state["test"] = ""
if 'phone' not in st.session_state:
    st.session_state["phone"] = ""
if 'email' not in st.session_state:
    st.session_state["email"] = ""


def send_verification_code():
    #generate verify number
    code  = "%05d" % randint(0,999999)
    st.session_state["code"] = code 
    asyncio.run(telegram.send_verification_code(st.session_state["phone"], code))
    st.experimental_rerun()
    
def send_verification_email():
    #generate verify number
    code  = "%05d" % randint(0,999999)
    st.session_state["code"] = code
    st.info("not implemented yet!")
    #asyncio.run(telegram.send_verification_code(st.session_state["email"], code))
    st.experimental_rerun()

def check_verification_code():
    if st.session_state["test"]==st.session_state["code"]:
        st.session_state["verified"]=True
        st.experimental_rerun()
    elif st.session_state["test"]!="":
        st.error("falscher Code!")
        if st.button("neuer Code senden"):
            send_verification_code()
            st.experimental_rerun()

def save_config():
    # Serialize data into file:
    id_file = st.session_state["phone"] + "_" + st.session_state["config_name"] # use phone as unique id
    config = {}
    for key, value in st.session_state.items():
        config[key]=value
    with open(CONFIGURATION_DIR + id_file + ".pickle", 'wb') as handle:
        pickle.dump(config, handle)
    st.session_state["config_selected"]=st.session_state["config_name"]

def delete_config():
    id_file = st.session_state["phone"] + "_" + st.session_state["config_selected"] # use phone as unique id
    os.remove(CONFIGURATION_DIR + id_file + ".pickle")
    for key in st.session_state.keys():
        if key not in ["verified","phone","email"]:
            del st.session_state[key]
    
def load_config():
    id_file = st.session_state["phone"] + "_" + st.session_state["config_selected"]
    with open(CONFIGURATION_DIR + id_file + ".pickle", 'rb') as handle:
        config = pickle.load(handle)
    for key, value in config.items():
        if key not in ["config_selected"]:
            st.session_state[key]=value


if st.session_state["verified"]:
    
    st.sidebar.info("Empfänger: " + st.session_state["phone"] + st.session_state["email"])
    configs = [file for file in os.listdir(CONFIGURATION_DIR) if file.startswith(st.session_state["phone"])]
    if len(configs)>0:
        st.sidebar.success("Alarm aktiv")
        st.sidebar.selectbox("Konfiguration", [config.split("_")[1].replace(".pickle","") for config in configs] ,
                            key="config_selected", on_change=load_config,
                            help="Du bekommst einen Alarm für jede Konfiguration")
        
        st.sidebar.button("Diese Konfiguration löschen", type="primary", on_click=delete_config)
    else:
        st.sidebar.warning("Alarm nicht konfiguriert")
   
    st.sidebar.divider()
    if st.sidebar.button("Log Out", type="secondary"):
        st.session_state["verified"]=False
        st.session_state["code"]=None
        st.session_state["test"]=""
        st.session_state["email"]=""
        st.session_state["phone"]=""
        st.experimental_rerun()
else:
    st.sidebar.error("Alarm deaktiviert!")




# CHOOSE ALERT CLIENT
col1, col2, _ = st.columns([.33,.33,.33], gap="large")
col3, _= st.columns([.655,.345])
if not st.session_state["verified"]:
    with col1:
        st.session_state["alert"] = st.selectbox("Alarmierungsdienst:", CLIENTS, disabled=st.session_state["verified"])
    with col2:
        if st.session_state["alert"] == "E-Mail":
            st.session_state["email"] = st.text_input("Deine E-Mail Addresse:", disabled=st.session_state["verified"], placeholder = "max.musterfrau@gmail.com")
        if st.session_state["alert"] in ("WhatsApp", "Telegram"):
            st.session_state["phone"] = st.text_input("Deine Mobiltelefonnummer:", disabled=st.session_state["verified"], placeholder = "+41 ...")
    with col3:
        # VERIFY
        if st.session_state["alert"]!="Deaktiviert" and not st.session_state["verified"]:
            if st.session_state["alert"] == "E-Mail":
                if st.session_state["email"]!="":
                    if st.session_state["code"] is None:
                        send_verification_email()
                    else:
                        st.text_input("Bestätige deine E-Mail Adresse mit dem gesendeten Verifikationscode", key="test")
                        check_verification_code()
            elif st.session_state["alert"] in ("WhatsApp", "Telegram"):
                if st.session_state["phone"]!="":
                    if st.session_state["code"] is None:
                        send_verification_code()
                    else:
                        st.text_input("Bestätige deine Telefonnummer mit dem gesendeten Verifikationscode", key="test")
                        check_verification_code()
 
if st.session_state["verified"]:
    col1, col2, _ = st.columns([.33 , .33, .33], gap="large")
    with col1:
        surfspot = st.selectbox("Surfspot:", SURFSPOTS, key="surfspot")
        st.text(" ")
    with col2:
        st.text_input("Dein Surfspot anfragen:", help="Es werden Stationsdaten von deinem Surfspot benötigt, um ein Modell trainieren zu können.")

    with st.expander("Wind"):
        col1, col2, _= st.columns([.33 , .33, .33], gap="large")
        with col1:
            st.selectbox("Surflevel basierte Einstellungen", ["Surflevel", "Custom"], key="surf_config")
        if st.session_state["surf_config"] == "Custom":
            st.session_state["custom"] = True
        else:
            st.session_state["custom"] = False
        
        with col2:
            st.select_slider("Dein Surflevel", LEVELS, disabled=st.session_state["custom"], key="surflevel",
                             help="Die Windgeschwindigkeiten werden nach Empfehlungen angepasst.")
            
        if st.session_state["surflevel"]=="Anfänger":
            wind_mean_init = (10, 30)
            wind_gust_init = (10, 50)
        elif st.session_state["surflevel"]=="Forgeschritten":
            wind_mean_init = (20, 40)
            wind_gust_init = (40, 60)
        elif st.session_state["surflevel"]=="PRO!":
            wind_mean_init = (25, 80)
            wind_gust_init = (40, 160)
        else:
            wind_mean_init = (0, 80)
            wind_gust_init = (0, 160)
            
        st.slider("mittlere Windgeschwindigkeit [km/h]:", 0, 80, 
                  wind_mean_init, step=1, disabled=not st.session_state["custom"], key="wind_mean")

        st.slider("maximale Windgeschwindigkeit [km/h]:", 0, 160, 
                  wind_gust_init, step=2, disabled=not st.session_state["custom"], key="wind_gust")

    with st.expander("Temperatur"):
        st.slider("Lufttemperatur [°C]:", -10, 40, (10, 40), 
                  step=1, key="temp_air")
        st.slider("Wassertemperatur [°C]:", 1, 30, (15, 30), 
                  step=1, disabled=True, help="noch nicht verfügbar", key="temp_water")


    with st.expander("Zeit"):
        st.slider("Montag:", time(7,00), time(20,00)
                  , value=(time(11, 30), time(12, 00)), step = timedelta(minutes= 10)
                  , key="monday")
        st.slider("Dienstag:", time(7,00), time(20,00)
                  , value=(time(11, 30), time(12, 00)), step = timedelta(minutes= 10)
                  , key="tuesday")
        st.slider("Mittwoch:", time(7,00), time(20,00)
                  , value=(time(11, 30), time(12, 00)), step = timedelta(minutes= 10)
                  , key="wednesday")
        st.slider("Donnerstag:", time(7,00), time(20,00)
                  , value=(time(11, 30), time(12, 00)), step = timedelta(minutes= 10)
                  , key="thursday")
        st.slider("Freitag:", time(7,00), time(20,00)
                  , value=(time(11, 30), time(19, 00)), step = timedelta(minutes= 10)
                  , key="friday")
        st.slider("Samstag:", time(7,00), time(20,00)
                  , value=(time(10, 00), time(18, 00)), step = timedelta(minutes= 10)
                  , key="saterday")
        st.slider("Sonntag:", time(7,00), time(20,00)
                  , value=(time(10, 00), time(12, 45)), step = timedelta(minutes= 10)
                  , key="sunday")
        
    with st.expander("Aktivität"):
        st.slider("minimale Zeitdauer der Session:", time(0,30),time(3,00), time(0,30)
                  , step = timedelta(minutes= 10), key="session")

    with st.expander("Anfahrt"):
        st.slider("Deine Anreisezeit:", time(0,10),time(2,00), time(0,30)
                  , step= timedelta(minutes=10), key="forcast"
                  , help = "Du wirst entsprechend früh benachrichtigt, damit du rechtzeitig am Spot bist.")
    st.divider()
    if st.button(label="Einstellungen speichern!", help="Die Einstellungen werden auf deine verifizierte Nummer gespeichert"
                , type="primary", disabled=False, use_container_width=False):
        
        st.text_input("Benenne deine Konfiguration", on_change=save_config, key="config_name")
