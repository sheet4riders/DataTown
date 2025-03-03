import streamlit as st
import requests
import pandas as pd
import traceback

# Configuration de la page
st.set_page_config(
    page_title="Chatbot Événements Orléans",
    page_icon="🎭",
    layout="wide"
)

# Titre et introduction
st.title("🎭 Chatbot - Événements à Orléans Métropole")
st.markdown("Posez des questions sur les événements à venir à Orléans Métropole.")

# Fonction pour récupérer les données de l'API
def fetch_data():
    """Interroge l'API pour récupérer l'agenda des événements d'Orléans Métropole."""
    API_URL = "https://data.orleans-metropole.fr/api/explore/v2.1/catalog/datasets/agenda-orleans-metropole/records"
    
    params = {
        "limit": 50  # Récupérer plus d'événements pour une meilleure recherche
    }
    
    headers = {
        "Accept": "application/json"
    }
    
    try:
        with st.spinner("Récupération des événements en cours..."):
            response = requests.get(API_URL, params=params, headers=headers, timeout=10)
            response.raise_for_status()
            
            data = response.json()
            if isinstance(data, dict) and "results" in data:
                return data["results"]
            else:
                st.error("⚠️ Structure de données inattendue dans la réponse de l'API.")
                return []
    except requests.exceptions.HTTPError as e:
        st.error(f"❌ Erreur HTTP ({response.status_code}): {e}")
    except requests.exceptions.ConnectionError:
        st.error("❌ Erreur de connexion : Impossible d'atteindre l'API")
    except requests.exceptions.Timeout:
        st.error("❌ Erreur de délai d'attente : L'API met trop de temps à répondre")
    except Exception as e:
        st.error(f"❌ Erreur inattendue : {str(e)}")
        st.code(traceback.format_exc())
    return []

# Fonction pour rechercher des événements
def search_events(data, query):
    """Recherche des événements correspondant à la requête de l'utilisateur."""
    if not data:
        return pd.DataFrame()
    
    df = pd.DataFrame(data)
    
    # Colonnes à conserver
    columns_to_keep = ["title_fr", "firstdate_begin", "lastdate_end", "location_name", "canonicalurl", "description_fr"]
    
    # Vérification des colonnes disponibles
    available_columns = [col for col in columns_to_keep if col in df.columns]
    
    if not available_columns:
        st.warning("⚠️ Aucune colonne utile trouvée dans les données")
        st.write("Colonnes disponibles:", ", ".join(df.columns))
        return pd.DataFrame()
    
    df_filtered = df[available_columns].copy()
    
    # Recherche multi-colonnes
    mask = pd.Series(False, index=df.index)
    
    # Recherche dans le titre
    if "title_fr" in df.columns:
        mask |= df["title_fr"].astype(str).str.contains(query, case=False, na=False)
    
    # Recherche dans la description si disponible
    if "description_fr" in df.columns:
        mask |= df["description_fr"].astype(str).str.contains(query, case=False, na=False)
    
    # Recherche dans le lieu si disponible
    if "location_name" in df.columns:
        mask |= df["location_name"].astype(str).str.contains(query, case=False, na=False)
    
    return df_filtered[mask]

# Formatage des dates
def format_date(date_str):
    """Formate les dates pour un affichage plus lisible."""
    if not date_str:
        return "Date non précisée"
    
    try:
        # Format attendu: 2023-03-15T19:00:00+01:00
        date_parts = date_str.split("T")
        date = date_parts[0]
        time = date_parts[1].split("+")[0] if len(date_parts) > 1 else ""
        
        # Convertir YYYY-MM-DD en DD/MM/YYYY
        year, month, day = date.split("-")
        formatted_date = f"{day}/{month}/{year}"
        
        # Ajouter l'heure si disponible
        if time:
            hour, minute, _ = time.split(":")
            formatted_date += f" à {hour}h{minute}"
        
        return formatted_date
    except:
        return date_str

# Initialisation de la session state
if "messages" not in st.session_state:
    st.session_state.messages = []
    # Message d'accueil
    st.session_state.messages.append({
        "role": "assistant", 
        "content": "Bonjour ! Je suis votre assistant pour les événements à Orléans Métropole. Que souhaitez-vous rechercher ? (ex: concerts, expositions, théâtre...)"
    })

# Affichage des messages précédents
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie pour l'utilisateur
user_input = st.chat_input("Tapez votre recherche ici...")

# Traitement de l'entrée utilisateur
if user_input:
    # Afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Récupérer les données et chercher des événements
    data = fetch_data()
    
    if data:
        results_df = search_events(data, user_input)
        
        if not results_df.empty:
            # Construire la réponse
            events_list = []
            
            for _, row in results_df.iterrows():
                event_text = f"**{row.get('title_fr', 'Événement sans titre')}**\n"
                
                # Dates
                if 'firstdate_begin' in row and 'lastdate_end' in row:
                    event_text += f"📅 {format_date(row.get('firstdate_begin'))} → {format_date(row.get('lastdate_end'))}\n"
                
                # Lieu
                if 'location_name' in row:
                    event_text += f"📍 {row.get('location_name', 'Lieu non précisé')}\n"
                
                # Description courte (si disponible)
                if 'description_fr' in row:
                    description = row.get('description_fr', '')
                    if description and len(description) > 200:
                        description = description[:200] + "..."
                    event_text += f"{description}\n"
                
                # Lien
                if 'canonicalurl' in row:
                    event_text += f"🔗 [Plus d'informations]({row.get('canonicalurl', '#')})\n"
                
                events_list.append(event_text)
            
            response = f"J'ai trouvé {len(events_list)} événement(s) correspondant à votre recherche \"{user_input}\" :\n\n"
            response += "\n\n---\n\n".join(events_list)
            
            # Si trop d'événements, suggérer d'affiner la recherche
            if len(events_list) > 5:
                response += "\n\n❓ Voulez-vous affiner votre recherche pour obtenir des résultats plus précis ?"
        else:
            response = f"Désolé, je n'ai trouvé aucun événement correspondant à \"{user_input}\". Essayez avec d'autres termes comme \"concert\", \"exposition\", ou \"théâtre\"."
    else:
        response = "Je n'ai pas pu récupérer les informations sur les événements. Veuillez réessayer plus tard."
    
    # Afficher la réponse
    st.session_state.messages.append({"role": "assistant", "content": response})
    with st.chat_message("assistant"):
        st.markdown(response)

# Pied de page
st.markdown("---")
st.caption("Données fournies par l'Open Data d'Orléans Métropole")
