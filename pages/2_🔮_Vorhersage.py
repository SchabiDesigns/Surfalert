import streamlit as st
import pandas as pd
import datetime as dt

from src.prediction import create_forcast_plots

st.set_page_config(
    page_title="Vorhersage",
    page_icon="🔮",
    layout="wide"
)

st.header("Vorhersage für Quinten")
st.sidebar.header("Einstellungen")

df = pd.read_csv("src/predictions/all_forcasts.csv", index_col=0)
df.index = pd.to_datetime(df.index)

if df is not None:
    latest_update = pd.to_datetime(df.index.min()).replace(tzinfo=None)
    if (dt.datetime.now() - latest_update).total_seconds() / 60.0 <= 30:
        st.sidebar.success("Status: aktuell")
    elif (dt.datetime.now() - latest_update).total_seconds() / 60.0 <= 90:
        st.sidebar.warning("Status: nicht aktuell")
    else:
        st.sidebar.error("Letzte Vorhersage am " + (latest_update - dt.timedelta(minutes=10)).strftime('%d.%m um %H:%M'))

    st.sidebar.selectbox("Darstellung:", ["Standard","Vektoren"],key="display")

    figs = create_forcast_plots(df)

    if st.session_state["display"]=="Vektoren":
        st.plotly_chart(figs["Windvektoren"], use_container_width=True)
    else:
        st.plotly_chart(figs["Windgeschwindigkeit"], use_container_width=True)
        st.plotly_chart(figs["Windrichtung"].update_layout(height=350), use_container_width=True) 
            
    with st.expander("Datensatz"):
        df = df.reset_index().set_index(["validdate","model","criterion"]).round(1)
        st.dataframe(df, use_container_width=True)
        st.download_button("Download csv", df.to_csv(), "all_forcasts.csv",)