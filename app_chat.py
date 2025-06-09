import streamlit as st
from dotenv import load_dotenv
import os
import shelve
import pandas as pd
import base64
from io import BytesIO

from core.db import get_connection
from core.gpt_sql import get_sql_from_gpt
from core.email_campaign import send_email_campaign, preview_personalization

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

    # Navigation principale
    st.markdown("### 🧭 Navigation")
    page = st.selectbox(
        "Choisir une page :",
        ["💬 Chat SQL", "📧 Email Campaign"],
        index=0
    )
    
    st.markdown("---")
    
    # Informations de la page actuelle
    if page == "💬 Chat SQL":
        st.info("💡 Pose tes questions en langage naturel")
    elif page == "📧 Email Campaign":
        st.info("📧 Envoi d'emails personnalisés via Gmail")
    
    # Ajouter un peu d'espace avant le bouton
    for _ in range(12):
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

# === Contenu principal selon la page sélectionnée ===
if page == "💬 Chat SQL":
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

elif page == "📧 Email Campaign":
    st.header("📧 Campagne Email Personnalisée avec IA")
    st.markdown("---")
    
    # Upload du CSV
    st.subheader("📊 1. Import des contacts")
    uploaded_file = st.file_uploader("Choisir un fichier CSV avec tes contacts", type=['csv'])
    
    if uploaded_file is not None:
        df_contacts = pd.read_csv(uploaded_file)
        st.success(f"✅ {len(df_contacts)} contacts importés")
        
        with st.expander("👀 Aperçu des données"):
            st.dataframe(df_contacts.head(), use_container_width=True)
            st.markdown("**Colonnes détectées :** " + ", ".join(df_contacts.columns.tolist()))
        
        st.markdown("---")
        
        # Configuration de l'email
        st.subheader("✉️ 2. Configuration de l'email")
        
        col1, col2 = st.columns(2)
        with col1:
            sender_name = st.text_input("👤 Nom d'expéditeur", 
                                       placeholder="Jean Dupont",
                                       value="Assistant IA")
        with col2:
            subject_template = st.text_input("📋 Sujet de l'email", 
                                            placeholder="Bonjour {nom}, offre spéciale !",
                                            value="Email personnalisé pour {nom}")
        
        st.info("💡 Tu peux utiliser des variables comme {nom}, {profession}, etc. L'IA s'adaptera automatiquement aux colonnes de ton CSV.")
        
        body_template = st.text_area("📝 Corps du message", 
                                    placeholder="""Bonjour {nom},

J'espère que vous allez bien. Je vous contacte car nous avons une offre spéciale qui pourrait vous intéresser.

En tant que {profession}, vous pourriez bénéficier de nos services...

Cordialement,
[Votre nom]""", 
                                    height=250)
        
        st.markdown("---")
        
        # Prévisualisation
        st.subheader("🔍 3. Prévisualisation")
        
        if st.button("👀 Générer un aperçu", use_container_width=True):
            if body_template:
                with st.spinner("🤖 Génération de l'aperçu avec IA..."):
                    try:
                        previews = preview_personalization(
                            df_contacts, 
                            body_template, 
                            subject_template, 
                            sender_name, 
                            1
                        )
                        
                        if previews and 'error' not in previews[0]:
                            preview = previews[0]
                            
                            st.success("✅ Aperçu généré !")
                            
                            with st.container():
                                st.markdown("**📧 Aperçu de l'email :**")
                                st.markdown(f"**De :** {preview['sender']}")
                                st.markdown(f"**À :** {preview['email']}")
                                st.markdown(f"**Sujet :** {preview['subject']}")
                                st.markdown("**Message :**")
                                st.markdown(f"```\n{preview['personalized_content']}\n```")
                        else:
                            st.error(f"❌ Erreur : {previews[0].get('error', 'Erreur inconnue')}")
                    
                    except Exception as e:
                        st.error(f"❌ Erreur lors de la prévisualisation : {e}")
            else:
                st.warning("⚠️ Remplis d'abord le template du message")
        
        # Envoi de la campagne
        st.markdown("---")
        st.subheader("🚀 4. Lancement de la campagne")
        
        st.warning("⚠️ **ATTENTION :** Cette action enverra de vrais emails ! Assure-toi d'avoir configuré ton fichier `.env` avec tes identifiants Gmail.")
        
        if st.button("📧 Lancer la campagne complète", type="primary", use_container_width=True):
            if not body_template:
                st.error("❌ Le template du message est obligatoire")
            else:
                # Créer les éléments d'interface pour le suivi
                progress_container = st.container()
                
                with progress_container:
                    progress_bar = st.progress(0)
                    status_text = st.empty()
                
                try:
                    with st.spinner("🚀 Lancement de la campagne..."):
                        results = send_email_campaign(
                            contacts_df=df_contacts,
                            template_input=body_template,
                            subject_template=subject_template,
                            sender_name=sender_name
                        )
                    
                    # Afficher les résultats
                    if results['errors'] > 0:
                        st.warning(f"⚠️ Campagne terminée avec des erreurs !")
                        col1, col2, col3 = st.columns(3)
                        with col1:
                            st.metric("✅ Succès", results['success'])
                        with col2:
                            st.metric("❌ Erreurs", results['errors'])
                        with col3:
                            st.metric("📊 Total", results['total'])
                        
                        with st.expander("🔍 Voir le détail des erreurs"):
                            for error in results['error_details']:
                                st.error(error)
                    else:
                        st.success("🎉 Campagne terminée avec succès !")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.metric("✅ Emails envoyés", results['success'])
                        with col2:
                            st.metric("📊 Total", results['total'])
                
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'envoi : {e}")
                    st.info("💡 Vérifie que ton fichier `.env` contient bien GMAIL_EMAIL et GMAIL_PASSWORD")
    
    else:
        st.info("📁 Commence par uploader un fichier CSV avec tes contacts")
        
        with st.expander("💡 Format du CSV attendu"):
            st.markdown("""
            Ton fichier CSV doit contenir au minimum :
            - **Une colonne email** (nom peut varier : email, mail, e-mail...)
            - **D'autres colonnes** pour la personnalisation (nom, prénom, profession, entreprise...)
            
            **Exemple :**
            ```
            nom,email,profession
            Jean Dupont,jean@test.com,développeur
            Marie Martin,marie@test.com,designer
            ```
            """)
        
        st.info("🔧 **Configuration requise :** Assure-toi d'avoir un fichier `.env` avec tes identifiants Gmail.")
