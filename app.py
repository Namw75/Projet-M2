import streamlit as st
import sqlite3
import openai
import pandas as pd
from io import BytesIO

# === Configuration OpenAI ===
client = openai.OpenAI(api_key="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")  # Remplace par ta vraie cléts ta vraie clé ici

# === Connexion à la base SQLite ===
conn = sqlite3.connect("bdd_clients.db")
cursor = conn.cursor()

# === Générer une requête SQL depuis une question utilisateur ===
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
   - Identifie le contact avec `Prénom`, `Nom`, et `Société` via `LOWER(...)`.
   - Mets à jour uniquement la colonne concernée (ex: `Téléphone`)
3. Si c’est une recherche ou un affichage, utilise `SELECT`.
4. ⚠️ Échappe toutes les apostrophes dans les valeurs texte (ex: l'air → l\'air)

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

    # Nettoyage si GPT renvoie du markdown ou un préfixe "sql"
    if raw_sql.lower().startswith("sql "):
        raw_sql = raw_sql[4:].strip()
    if raw_sql.startswith("```sql"):
        raw_sql = raw_sql.replace("```sql", "").replace("```", "").strip()

    return raw_sql

# === Fonction pour exporter un DataFrame en mémoire Excel ===
def to_excel(df):
    output = BytesIO()
    with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
        df.to_excel(writer, index=False, sheet_name='Résultat')
    return output.getvalue()

# === Interface Streamlit ===
st.markdown("""
    <style>
    .chat-container {
        background-color: white;
        border-radius: 15px;
        padding: 20px;
        margin-bottom: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .database-message {
        color: #2E7D32;
        margin: 10px 0;
    }
    .user-message {
        color: #D32F2F;
        margin: 10px 0;
    }
    .user-input {
        background-color: white;
        border-radius: 15px;
        padding: 10px;
        margin-top: 20px;
        box-shadow: 0 2px 5px rgba(0,0,0,0.1);
    }
    .stButton>button {
        border-radius: 20px;
        padding: 10px 20px;
    }
    </style>
""", unsafe_allow_html=True)

# Historique des requêtes
if "history" not in st.session_state:
    st.session_state.history = []

# Zone de saisie utilisateur tout en bas
with st.form("query_form", clear_on_submit=True):
    st.markdown('<div class="user-input">', unsafe_allow_html=True)
    user_input = st.text_input("Saisissez votre texte", label_visibility="collapsed")
    submitted = st.form_submit_button("Entrer")
    st.markdown('</div>', unsafe_allow_html=True)

if submitted and user_input:
    sql_query = get_sql_from_gpt(user_input)
    st.session_state.history.append((user_input, sql_query))

    # Afficher immédiatement la requête et le résultat correspondant
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="user-message">Moi : {user_input}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="database-message">Base de donnée :</div>', unsafe_allow_html=True)

    with st.spinner("⏳ Requête en cours..."):
        try:
            if sql_query.strip().lower().startswith("insert") or sql_query.strip().lower().startswith("update") or sql_query.strip().lower().startswith("delete"):
                cursor.execute(sql_query)
                conn.commit()
                st.success("✅ Opération réalisée avec succès.")
            else:
                df = pd.read_sql_query(sql_query, conn)
                st.dataframe(df, use_container_width=True)

                csv_data = df.to_csv(index=False).encode("utf-8")
                excel_data = to_excel(df)

                col1, col2 = st.columns(2)
                with col1:
                    st.download_button(
                        label="📥 Télécharger en CSV",
                        data=csv_data,
                        file_name="resultat_direct.csv",
                        mime="text/csv"
                    )
                with col2:
                    st.download_button(
                        label="📥 Télécharger en Excel",
                        data=excel_data,
                        file_name="resultat_direct.xlsx",
                        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
                    )
        except Exception as e:
            st.error(f"Erreur : {str(e)}")

    with st.expander("Voir la requête SQL utilisée"):
        st.code(sql_query, language="sql")
    st.markdown('</div>', unsafe_allow_html=True)

# Zone de chat avec historique (affichage seulement, sans réexécution)
for i, (q, sql) in enumerate(reversed(st.session_state.history[:-1]), 1):
    st.markdown('<div class="chat-container">', unsafe_allow_html=True)
    st.markdown(f'<div class="user-message">Moi : {q}</div>', unsafe_allow_html=True)
    st.markdown(f'<div class="database-message">Base de donnée :</div>', unsafe_allow_html=True)
    with st.expander("Voir la requête SQL utilisée"):
        st.code(sql, language="sql")
    st.markdown('</div>', unsafe_allow_html=True)
