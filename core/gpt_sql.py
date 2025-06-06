import openai
import os
from dotenv import load_dotenv

load_dotenv()
client = openai.OpenAI(api_key=os.getenv("OPENAI_API_KEY"))

def get_sql_from_gpt(user_query):
    prompt = f"""
Tu es un assistant SQL pour une base SQLite contenant deux tables :

1. `contacts` :
   - Nom, Prénom, Email, Société, Domaine, Secteur d'activité, Poste, Linkedin, Téléphone, Commentaire

2. `companies` :
   - Société

COMPORTEMENTS ATTENDUS :

1. Si l'utilisateur veut ajouter un contact, utilise `INSERT INTO`.
2. Si l'utilisateur donne une nouvelle info sur un contact existant, utilise `UPDATE contacts SET ... WHERE ...`.
3. Si c’est une recherche ou un affichage, utilise `SELECT`.
⚠️ Ne retourne que la requête SQL. Pas d’explication.

Requête utilisateur :
\"\"\"{user_query}\"\"\"
"""
    response = client.chat.completions.create(
        model="gpt-4",
        messages=[{"role": "user", "content": prompt}],
        temperature=0
    )
    raw_sql = response.choices[0].message.content.strip()

    if raw_sql.lower().startswith("sql "):
        raw_sql = raw_sql[4:].strip()
    if raw_sql.startswith("```sql"):
        raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()

    return raw_sql
