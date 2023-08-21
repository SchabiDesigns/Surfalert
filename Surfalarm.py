import streamlit as st

st.set_page_config(
    page_title="Surfalarm",
    page_icon="🏄‍♀️",
    layout="wide"
)

username = "Surfbuddy"

st.write("# Hallo Surfbuddy! 👋")

st.markdown(
    """
    Konfiguriere deinen persönlichen Surfalarm für den Walensee!
    
    ### Wie es funktioniert
    - Verifiziere deine Telefonnummer via Telegram
    - Konfiguriere deinen Surfalarm mit folgenden Parametern:
        - Windgeschwindigkeit
        - Temperatur
        - Freizeit
        - Anreisezeit
        ...
    - fertig!
    """
)