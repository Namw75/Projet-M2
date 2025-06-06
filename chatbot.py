import sqlite3
import openai
import pandas as pd

# === Clé API OpenAI (test local) ===
client = openai.OpenAI(api_key="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")  # Remplace par ta vraie cléts ta vraie clé ici

# === Connexion SQLite ===
conn = sqlite3.connect("bdd_clients.db")
cursor = conn.cursor()

# === Fonction GPT améliorée ===
def get_sql_from_gpt(user_query):
    prompt = f"""
Tu es un assistant SQL pour une base SQLite contenant deux tables :

1. `contacts` :
   - Nom, Prénom, Email, Société, Domaine, Secteur d'activité, Poste, Linkedin, Téléphone, Commentaire

2. `companies` :
   - Société

🧠 COMPORTEMENTS ATTENDUS :

1. Si l'utilisateur veut ajouter un contact, utilise `INSERT INTO`.
2. Si l'utilisateur donne une nouvelle info sur un contact existant, utilise `UPDATE contacts SET ... WHERE ...`.
   - Identifie le contact avec `Prénom`, `Nom`, et `Société` via `LOWER(...)`.
   - Mets à jour uniquement la colonne concernée (ex: `Téléphone`)
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
    return response.choices[0].message.content.strip()

# === Boucle principale ===
print("💬 Chatbot connecté. Tape 'Hypeboy' pour quitter.")
while True:
    user_input = input("\n📤 Question : ")
    if user_input.strip().lower() == "hypeboy":
        print("👋 À la prochaine, killer.")
        break

    try:
        sql_query = get_sql_from_gpt(user_input)
        print(f"\n💡 Requête SQL générée :\n{sql_query}")

        if sql_query.strip().lower().startswith("insert"):
            cursor.execute(sql_query)
            conn.commit()
            print("✅ Contact ajouté avec succès.")
        else:
            result = pd.read_sql_query(sql_query, conn)
            print("\n📊 Résultat :")
            print(result.head(10).to_markdown())

    except Exception as e:
        print("❌ Erreur :", e)
