import requests
import pandas as pd
import streamlit as st

def fetch_data():
    """Interroge l'API pour récupérer l'agenda des événements d'Orléans Métropole et gère les erreurs."""
    API_URL = "https://data.orleans-metropole.fr/api/explore/v2.1/catalog/datasets/agenda-orleans-metropole/records"
    params = {"limit": 50}  # Augmenter le nombre de résultats affichés
    try:
        response = requests.get(API_URL, params=params)
        response.raise_for_status()
        data = response.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        else:
            return []  # Retourne une liste vide si la structure n'est pas correcte
    except requests.exceptions.RequestException as e:
        st.error(f"Erreur lors de la récupération des données : {e}")
        return []

# Interface Chatbot avec Streamlit
st.title("Chatbot - Événements à Orléans Métropole")
user_query = st.text_input("Posez votre question (ex: événements gratuits, concerts, expositions) :")

if user_query:
    data = fetch_data()
    if data:
        df = pd.DataFrame(data)
        columns_to_keep = ["title_fr", "firstdate_begin", "lastdate_end", "location_name", "canonicalurl"]
        df_filtered = df[columns_to_keep].dropna()
        
        # Recherche simple basée sur les mots-clés entrés par l'utilisateur
        df_results = df_filtered[df_filtered["title_fr"].str.contains(user_query, case=False, na=False)]
        
        if not df_results.empty:
            st.write("### Résultats correspondants :")
            st.dataframe(df_results)
        else:
            st.warning("Aucun événement trouvé correspondant à votre recherche.")
    else:
        st.warning("Aucune donnée disponible ou requête invalide.")
