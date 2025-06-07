import streamlit as st
from dotenv import load_dotenv
import os
import shelve
import pandas as pd
import base64
from io import BytesIO

from core.db import get_connection
from core.gpt_sql import get_sql_from_gpt

load_dotenv()

st.set_page_config(page_title="SQL Chatbot", page_icon="🤖")
st.title("SQL Chatbot Assistant")

USER_AVATAR = "👤"
BOT_AVATAR = "🤖"

def load_chat_history():
    with shelve.open("chat_history") as db:
        return db.get("messages", [])

def save_chat_history(messages):
    with shelve.open("chat_history") as db:
        db["messages"] = messages

def prepare_download_links(df: pd.DataFrame):
    csv = df.to_csv(index=False).encode()
    b64_csv = base64.b64encode(csv).decode()
    href_csv = f'<a href="data:text/csv;base64,{b64_csv}" download="résultat.csv">📥 Télécharger CSV</a>'

    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df.to_excel(writer, index=False, sheet_name="Résultat")
    b64_excel = base64.b64encode(output.getvalue()).decode()
    href_excel = f'<a href="data:application/vnd.openxmlformats-officedocument.spreadsheetml.sheet;base64,{b64_excel}" download="résultat.xlsx">📥 Télécharger Excel</a>'

    return href_csv, href_excel

if "messages" not in st.session_state:
    st.session_state.messages = load_chat_history()

with st.sidebar:
    st.markdown("## 📚 Options")

    # Espace réservé pour contenu futur ici si besoin
    
    # Ajouter beaucoup d'espace vertical pour pousser le bouton vers le bas
    for _ in range(32):
        st.write("")

    # Séparateur visuel juste avant le bouton
    st.markdown("---")

    # CSS amélioré pour le bouton
    st.markdown(
        """
        <style>
        .bottom-btn {
            text-align: center;
            margin: 1rem 0;
            padding: 0;
        }
        .bottom-btn .stButton {
            display: flex;
            justify-content: center;
            width: 100%;
        }
        .bottom-btn .stButton > button {
            width: 90% !important;
            max-width: none !important;
            margin: 0 !important;
            padding: 0.5rem 1rem !important;
        }
        </style>
        """,
        unsafe_allow_html=True
    )

    # Bouton de suppression
    st.markdown('<div class="bottom-btn">', unsafe_allow_html=True)
    if st.button("🗑️ Supprimer l'historique", key="btn_delete_fixed"):
        st.session_state.messages = []
        save_chat_history([])
    st.markdown('</div>', unsafe_allow_html=True)




# === Affichage du chat ===
for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

# === Interaction utilisateur ===
if prompt := st.chat_input("Pose une question sur la base..."):
    st.chat_message("user", avatar=USER_AVATAR).markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = get_sql_from_gpt(prompt)

        if sql.lower().startswith(("insert", "update", "delete")):
            cursor.execute(sql)
            conn.commit()
            response = "✅ Requête exécutée avec succès."
            st.chat_message("assistant", avatar=BOT_AVATAR).markdown(response)
        else:
            df = pd.read_sql_query(sql, conn)
            st.session_state.messages.append({"role": "assistant", "content": "📊 Résultat affiché."})

            with st.chat_message("assistant", avatar=BOT_AVATAR):
                st.markdown("📊 Résultat :")
                st.dataframe(df, use_container_width=True)

                href_csv, href_excel = prepare_download_links(df)
                with st.expander("🧠 Voir la requête SQL & téléchargements"):
                    st.markdown("📄 Requête SQL générée :")
                    st.code(sql, language="sql")
                    st.markdown(href_csv, unsafe_allow_html=True)
                    st.markdown(href_excel, unsafe_allow_html=True)

    except Exception as e:
        response = f"❌ Erreur : {e}"
        st.chat_message("assistant", avatar=BOT_AVATAR).markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    save_chat_history(st.session_state.messages)
