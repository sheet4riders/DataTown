import requests
import pandas as pd

def fetch_data():
    """Interroge l'API pour récupérer l'agenda des événements d'Orléans Métropole et gère les erreurs."""
    # URL basée sur ce qui est affiché dans votre capture d'écran
    API_URL = "https://data.orleans-metropole.fr/api/explore/v2.1/catalog/datasets/agenda-orleans-metropole/records"
    
    # Paramètres de requête (comme indiqué dans la capture d'écran)
    params = {
        "limit": 20  # Comme montré dans l'URL de l'exemple
    }
    
    # En-têtes simplifiés
    headers = {
        "Accept": "application/json"
    }
    
    try:
        response = requests.get(API_URL, params=params, headers=headers, timeout=10)
        response.raise_for_status()
        
        data = response.json()
        if isinstance(data, dict) and "results" in data:
            return data["results"]
        else:
            print("⚠️ Aucune donnée récupérée. Vérifie la structure de l'API.")
            return []
    except requests.exceptions.HTTPError as e:
        print(f"❌ Erreur HTTP ({response.status_code}): {e}")
    except requests.exceptions.ConnectionError:
        print("❌ Erreur de connexion : Impossible d'atteindre l'API")
    except requests.exceptions.Timeout:
        print("❌ Erreur de délai d'attente : L'API met trop de temps à répondre")
    except requests.exceptions.RequestException as e:
        print(f"❌ Erreur inattendue : {e}")
    return []

def main(user_query="concert"):
    print("🎤 Bienvenue dans le Chatbot - Événements à Orléans Métropole 🎭")
    
    data = fetch_data()
    if data:
        df = pd.DataFrame(data)
        columns_to_keep = ["title_fr", "firstdate_begin", "lastdate_end", "location_name", "canonicalurl"]
        
        # Vérification si toutes les colonnes existent
        for col in columns_to_keep:
            if col not in df.columns:
                print(f"⚠️ Colonne manquante dans la réponse API: {col}")
                print(f"Colonnes disponibles: {', '.join(df.columns)}")
                # Utiliser uniquement les colonnes disponibles
                columns_to_keep = [c for c in columns_to_keep if c in df.columns]
                break
        
        if columns_to_keep:
            df_filtered = df[columns_to_keep].copy()
            
            # Filtre sans plantage si certaines colonnes sont manquantes
            if "title_fr" in df.columns:
                df_results = df_filtered[df_filtered["title_fr"].str.contains(user_query, case=False, na=False)]
                
                if not df_results.empty:
                    print("\n🎯 Résultats correspondants :")
                    for _, row in df_results.iterrows():
                        print(f"- {row.get('title_fr', 'Sans titre')}")
                        if "firstdate_begin" in row and "lastdate_end" in row:
                            print(f"  📅 {row.get('firstdate_begin', 'N/A')} ➡ {row.get('lastdate_end', 'N/A')}")
                        if "location_name" in row:
                            print(f"  📍 {row.get('location_name', 'Lieu non précisé')}")
                        if "canonicalurl" in row:
                            print(f"  🔗 {row.get('canonicalurl', '#')}")
                        print()
                else:
                    print("🔍 Aucun événement trouvé correspondant à votre recherche.")
            else:
                print("⚠️ Impossible de filtrer sans la colonne 'title_fr'")
                print("Voici les premières données disponibles :")
                print(df_filtered.head())
        else:
            print("⚠️ Aucune colonne correspondante trouvée dans la réponse API")
    else:
        print("🚫 Aucune donnée disponible ou requête invalide.")

if __name__ == "__main__":
    main()
