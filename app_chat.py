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
    if st.button("🗑️ Supprimer l'historique"):
        st.session_state.messages = []
        save_chat_history([])

for message in st.session_state.messages:
    avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
    with st.chat_message(message["role"], avatar=avatar):
        st.markdown(message["content"])

if prompt := st.chat_input("Pose une question sur la base..."):
    st.chat_message("user", avatar=USER_AVATAR).markdown(prompt)
    st.session_state.messages.append({"role": "user", "content": prompt})

    conn = get_connection()
    cursor = conn.cursor()

    try:
        sql = get_sql_from_gpt(prompt)
        st.chat_message("assistant", avatar=BOT_AVATAR).markdown(f"📄 Requête SQL générée :\n```sql\n{sql}\n```")

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
                with st.expander("⬇️ Télécharger le résultat"):
                    st.markdown(href_csv, unsafe_allow_html=True)
                    st.markdown(href_excel, unsafe_allow_html=True)

    except Exception as e:
        response = f"❌ Erreur : {e}"
        st.chat_message("assistant", avatar=BOT_AVATAR).markdown(response)
        st.session_state.messages.append({"role": "assistant", "content": response})

    save_chat_history(st.session_state.messages)