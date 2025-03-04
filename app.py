import streamlit as st
import requests
import pandas as pd
import traceback
import json
import os
from datetime import datetime

# Configuration de la page
st.set_page_config(
    page_title="IA Chatbot Événements Orléans",
    page_icon="🎭",
    layout="wide"
)

# Titre et introduction
st.title("🎭 IA Chatbot - Événements à Orléans Métropole")
st.markdown("Posez des questions sur les événements à venir à Orléans Métropole. Notre IA vous aidera à trouver ce que vous cherchez.")

# Configuration de l'API Claude
CLAUDE_API_KEY = st.secrets.get("CLAUDE_API_KEY", os.environ.get("CLAUDE_API_KEY", ""))
CLAUDE_API_URL = "https://api.anthropic.com/v1/messages"

# Si la clé API n'est pas disponible, afficher un avertissement
if not CLAUDE_API_KEY:
    st.warning("⚠️ Clé API Claude non trouvée. Le chatbot fonctionnera en mode basique.")

# Fonction pour récupérer les données de l'API Orléans Métropole
def fetch_data():
    """Interroge l'API pour récupérer l'agenda des événements d'Orléans Métropole."""
    API_URL = "https://data.orleans-metropole.fr/api/explore/v2.1/catalog/datasets/agenda-orleans-metropole/records"
    
    params = {
        "limit": 100  # Récupérer plus d'événements pour une meilleure recherche
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
    except Exception as e:
        st.error(f"❌ Erreur lors de la récupération des données: {str(e)}")
        return []

# Fonction pour formater les données d'événements
def prepare_events_data(events_data):
    if not events_data:
        return "Aucun événement disponible."
    
    df = pd.DataFrame(events_data)
    
    # Sélectionner et renommer les colonnes pertinentes
    columns_mapping = {
        "title_fr": "titre",
        "description_fr": "description",
        "firstdate_begin": "date_debut",
        "lastdate_end": "date_fin",
        "location_name": "lieu",
        "location_address": "adresse",
        "canonicalurl": "lien",
        "tags_fr": "categories"
    }
    
    # Filtrer les colonnes disponibles
    available_columns = {k: v for k, v in columns_mapping.items() if k in df.columns}
    
    if not available_columns:
        return "Données d'événements dans un format inattendu."
    
    # Créer un dataframe avec les colonnes renommées
    events_df = df[list(available_columns.keys())].rename(columns=available_columns)
    
    # Convertir en format JSON pour Claude
    events_json = events_df.to_dict(orient="records")
    
    return json.dumps(events_json, ensure_ascii=False, indent=2)

# Fonction pour interroger Claude API directement avec requests
def ask_claude(user_query, events_data, conversation_history):
    if not CLAUDE_API_KEY:
        return "Mode IA désactivé. Utilisez une recherche par mots-clés à la place."
    
    # Construire le prompt avec le contexte
    system_prompt = f"""
    Tu es un assistant spécialisé dans les événements culturels d'Orléans Métropole. 
    Tu as accès aux données d'événements à jour du {datetime.now().strftime('%d/%m/%Y')}.
    
    DONNÉES DES ÉVÉNEMENTS:
    {events_data}
    
    INSTRUCTIONS:
    1. Réponds aux questions de l'utilisateur sur les événements à Orléans Métropole.
    2. Propose des événements pertinents basés sur la demande de l'utilisateur.
    3. Si tu ne trouves pas d'information spécifique, propose des alternatives.
    4. Mentionne les dates, lieux et liens des événements quand disponibles.
    5. Sois concis mais informatif.
    6. Ne mentionne pas que tu utilises des données au format JSON dans ta réponse.
    7. Si l'utilisateur demande des informations qui ne se trouvent pas dans les données, indique poliment que tu n'as pas cette information.
    8. Ne prétends pas avoir accès à des informations qui ne sont pas dans les données fournies.
    9. Comprends que l'utilisateur parle en français et réponds-lui toujours en français.
    """
    
    # Construire les messages
    messages = []
    
    # Ajouter l'historique de conversation (jusqu'à 10 derniers messages pour limiter le contexte)
    for msg in conversation_history[-10:]:
        role = "user" if msg["role"] == "user" else "assistant"
        messages.append({"role": role, "content": msg["content"]})
    
    # Ajouter la nouvelle question
    messages.append({"role": "user", "content": user_query})
    
    # Préparer le payload pour l'API
    payload = {
        "model": "claude-3-haiku-20240307",
        "system": system_prompt,
        "messages": messages,
        "max_tokens": 1000,
        "temperature": 0.7
    }
    
    headers = {
        "x-api-key": CLAUDE_API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    try:
        response = requests.post(
            CLAUDE_API_URL,
            headers=headers,
            json=payload,
            timeout=30
        )
        
        response.raise_for_status()
        response_data = response.json()
        
        # Extraire la réponse de l'IA
        if "content" in response_data and len(response_data["content"]) > 0:
            return response_data["content"][0]["text"]
        else:
            raise Exception("Format de réponse inattendu")
            
    except Exception as e:
        st.error(f"Erreur lors de l'appel à Claude API: {str(e)}")
        # Fallback à la recherche simple en cas d'échec
        return fallback_search(user_query, events_data)

# Fonction de recherche de base (fallback) si Claude échoue
def fallback_search(query, events_data):
    try:
        # Convertir les données JSON en DataFrame
        if isinstance(events_data, str):
            events_list = json.loads(events_data)
            df = pd.DataFrame(events_list)
        else:
            df = pd.DataFrame(events_data)
        
        # Champs de recherche
        search_fields = ["titre", "description", "lieu", "categories"]
        available_fields = [f for f in search_fields if f in df.columns]
        
        if not available_fields:
            return "Je ne peux pas effectuer de recherche dans ce format de données."
        
        # Recherche simple
        query = query.lower()
        results = []
        
        for _, event in df.iterrows():
            for field in available_fields:
                if field in event and isinstance(event[field], str) and query in event[field].lower():
                    results.append(event)
                    break
        
        if not results:
            return f"Aucun événement trouvé pour '{query}'. Essayez avec d'autres termes."
        
        # Formater les résultats
        response = f"J'ai trouvé {len(results)} événement(s) pour '{query}':\n\n"
        
        for event in results[:5]:  # Limiter à 5 résultats
            response += f"**{event.get('titre', 'Événement')}**\n"
            if 'date_debut' in event:
                response += f"📅 {format_date(event.get('date_debut', ''))}\n"
            if 'lieu' in event:
                response += f"📍 {event.get('lieu', '')}\n"
            if 'lien' in event:
                response += f"🔗 [Plus d'infos]({event.get('lien', '#')})\n"
            response += "\n"
        
        if len(results) > 5:
            response += f"...et {len(results) - 5} autres événements."
            
        return response
    except Exception as e:
        return f"Erreur lors de la recherche: {str(e)}"

# Fonction pour formater les dates
def format_date(date_str):
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
        "content": "Bonjour ! Je suis votre assistant IA pour les événements à Orléans Métropole. Comment puis-je vous aider aujourd'hui ?"
    })

# Chargement et préparation des données (une seule fois par session)
if "events_data" not in st.session_state:
    raw_events = fetch_data()
    st.session_state.events_data = prepare_events_data(raw_events)

# Affichage des messages précédents
for message in st.session_state.messages:
    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# Zone de saisie pour l'utilisateur
user_input = st.chat_input("Posez votre question ici...")

# Traitement de l'entrée utilisateur
if user_input:
    # Afficher le message de l'utilisateur
    st.session_state.messages.append({"role": "user", "content": user_input})
    with st.chat_message("user"):
        st.markdown(user_input)
    
    # Obtenir la réponse de l'IA
    ai_response = ask_claude(user_input, st.session_state.events_data, st.session_state.messages)
    
    # Afficher la réponse
    st.session_state.messages.append({"role": "assistant", "content": ai_response})
    with st.chat_message("assistant"):
        st.markdown(ai_response)

# Pied de page
st.markdown("---")
st.caption("Propulsé par l'IA Claude d'Anthropic • Données: Open Data Orléans Métropole")

# Sidebar avec informations et paramètres
with st.sidebar:
    st.header("À propos")
    st.markdown("""
    Ce chatbot utilise l'intelligence artificielle Claude pour comprendre vos questions et vous fournir des informations pertinentes sur les événements à Orléans Métropole.
    
    Exemples de questions:
    - "Y a-t-il des concerts ce week-end ?"
    - "Quelles expositions sont organisées ce mois-ci ?"
    - "Je cherche des activités pour enfants"
    - "Où sont les événements gratuits ?"
    """)
    
    # Option pour effacer l'historique
    if st.button("Effacer la conversation"):
        st.session_state.messages = []
        st.session_state.messages.append({
            "role": "assistant", 
            "content": "Conversation effacée. Comment puis-je vous aider aujourd'hui ?"
        })
        st.rerun()
