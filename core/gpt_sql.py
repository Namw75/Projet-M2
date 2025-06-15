import openai
import os
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_sql_from_gpt(user_query, conversation_history=None):
    # Préparer l'historique de conversation
    history_context = ""
    if conversation_history and len(conversation_history) > 1:
        recent_history = conversation_history[-6:]  # 3 derniers échanges
        history_context = "=== HISTORIQUE RÉCENT ===\n"
        for msg in recent_history:
            role = "Utilisateur" if msg["role"] == "user" else "Assistant"
            content = msg["content"][:150] + "..." if len(msg["content"]) > 150 else msg["content"]
            history_context += f"{role}: {content}\n"
        history_context += "=== FIN HISTORIQUE ===\n\n"

    prompt = f"""
Tu es un assistant SQL pour une base SQLite contenant deux tables :

1. `contacts` (10 colonnes) :
   - Nom, Prénom, Email, Société, Domaine, Secteur d'activité, Poste, Linkedin, Téléphone, Commentaire

2. `companies` (1 colonne) :
   - Société

{history_context}COMPORTEMENTS ATTENDUS :

1. Tu as accès à l'historique de conversation ci-dessus, utilise-le pour comprendre le contexte
2. Si l'utilisateur fait référence à quelque chose de précédent, adapte ta requête
3. Si l'utilisateur veut ajouter un contact, utilise `INSERT INTO`
4. Si l'utilisateur donne une nouvelle info sur un contact existant, utilise `UPDATE contacts SET ... WHERE ...`
5. Si c'est une recherche ou un affichage, utilise `SELECT`

⚠️ INSTRUCTIONS CRITIQUES :
- Ne retourne QUE les requêtes SQL, rien d'autre
- PAS de commentaires, PAS d'explications, PAS de texte
- Maximum 3 requêtes si nécessaire (séparées par des points-virgules)
- Une ligne par requête

🔧 GESTION DES CARACTÈRES SPÉCIAUX :
- Pour les noms de colonnes avec espaces : utilise des guillemets doubles "Secteur d'activité"
- Pour les valeurs contenant des apostrophes : remplace les apostrophes par deux apostrophes simples
- Exemple : "s'appelle" devient "s''appelle" dans SQL

📝 STRUCTURE OBLIGATOIRE POUR INSERT :
- Pour INSERT INTO contacts : TOUJOURS spécifier les 10 colonnes dans l'ordre
- Utiliser NULL pour les valeurs manquantes
- Format : INSERT INTO contacts (Nom, Prénom, Email, Société, Domaine, "Secteur d'activité", Poste, Linkedin, Téléphone, Commentaire) VALUES (...)

🔍 RECHERCHE INSENSIBLE À LA CASSE :
- Pour les recherches sur des champs textuels (ex : "Secteur d'activité", "Domaine", "Poste"), génère des requêtes insensibles à la casse en utilisant LOWER(colonne) = 'valeur' ou LOWER(colonne) LIKE '%valeur%'.
- Exemple : SELECT * FROM contacts WHERE LOWER("Secteur d'activité") = 'finance'
- Pour une recherche partielle : SELECT * FROM contacts WHERE LOWER("Secteur d'activité") LIKE '%finance%'

🎯 FORMAT DES COMMENTAIRES :
- Pour les ambassadeurs/égéries : utilise "Ambassadeur [Marque]" ou "Égérie [Marque]"
- Pour plusieurs marques : sépare par des virgules "Ambassadeur [Marque1], [Marque2]"
- Exemples :
  * "Égérie Dior" (pour une égérie)
  * "Ambassadeur Louis Vuitton" (pour un ambassadeur)
  * "Ambassadeur Yves Saint Laurent, Burberry" (pour plusieurs marques)

📝 EXEMPLES CORRECTS :
- INSERT INTO companies (Société) VALUES ('NewJeans');
- INSERT INTO contacts (Nom, Prénom, Email, Société, Domaine, "Secteur d'activité", Poste, Linkedin, Téléphone, Commentaire) VALUES ('Pham', 'Hanni', 'hanni.pham@hybe.com', 'NewJeans', NULL, 'Musique', 'Chanteuse', 'https://in.linkedin.com/in/hanni-pham', '07 09 23 02 22', 'Ambassadeur Burberry, Gucci');
- SELECT * FROM contacts WHERE LOWER("Secteur d'activité") = 'finance';
- SELECT * FROM contacts WHERE LOWER("Secteur d'activité") LIKE '%finance%';

Requête utilisateur :
\"\"\"{user_query}\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    raw_sql = response.choices[0].message.content.strip()

    # Nettoyer la réponse de l'IA
    if raw_sql.lower().startswith("sql "):
        raw_sql = raw_sql[4:].strip()
    if raw_sql.startswith("```sql"):
        raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()
    if raw_sql.startswith("```"):
        raw_sql = raw_sql.replace("```", "").strip()
    
    # Enlever les commentaires et texte parasite
    lines = raw_sql.split('\n')
    sql_lines = []
    for line in lines:
        line = line.strip()
        if line and not line.startswith('--') and not line.startswith('#'):
            sql_lines.append(line)
    
    cleaned_sql = ' '.join(sql_lines)
    
    return cleaned_sql
