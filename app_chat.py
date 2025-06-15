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

def load_ai_viz_history():
    with shelve.open("ai_viz_history") as db:
        return db.get("messages", [])

def save_ai_viz_history(messages):
    with shelve.open("ai_viz_history") as db:
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
        ["💬 Chat SQL", "🤖 AI Visualization", "📧 Email Campaign"],
        index=0
    )
    
    st.markdown("---")
    
    # Informations de la page actuelle
    if page == "💬 Chat SQL":
        st.info("💡 Pose tes questions en langage naturel")
    elif page == "🤖 AI Visualization":
        st.info("📊 Génération automatique de graphiques avec IA (SQL + Documents)")
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

    # Bouton de suppression - adapté selon la page
    st.markdown('<div class="bottom-btn">', unsafe_allow_html=True)
    if page == "💬 Chat SQL":
        if st.button("🗑️ Supprimer l'historique SQL", key="btn_delete_sql"):
            st.session_state.messages = []
            save_chat_history([])
    elif page == "🤖 AI Visualization":
        if st.button("🗑️ Supprimer l'historique AI Viz", key="btn_delete_ai_viz"):
            st.session_state.ai_viz_messages = []
            save_ai_viz_history([])
    else:
        # Page Email Campaign - pas d'historique
        if st.button("🗑️ Supprimer tous les historiques", key="btn_delete_all"):
            st.session_state.messages = []
            if "ai_viz_messages" in st.session_state:
                st.session_state.ai_viz_messages = []
            save_chat_history([])
            save_ai_viz_history([])
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
            sql = get_sql_from_gpt(prompt, st.session_state.messages)
            
            # Séparer les requêtes multiples
            sql_statements = []
            if ';' in sql:
                # Plusieurs requêtes
                statements = [s.strip() for s in sql.split(';') if s.strip()]
                sql_statements = statements[:3]  # Maximum 3 requêtes
            else:
                # Une seule requête
                sql_statements = [sql.strip()]
            
            # Exécuter chaque requête séquentiellement
            results = []
            modification_made = False
            
            with st.chat_message("assistant", avatar=BOT_AVATAR):
                for i, statement in enumerate(sql_statements):
                    if not statement:
                        continue
                        
                    if len(sql_statements) > 1:
                        st.markdown(f"**🔄 Étape {i+1}/{len(sql_statements)}**")
                    
                    try:
                        if statement.lower().startswith(("insert", "update", "delete")):
                            cursor.execute(statement)
                            conn.commit()
                            modification_made = True
                            st.success(f"✅ Requête {i+1} exécutée avec succès")
                            results.append(f"Requête {i+1}: Modification effectuée")
                        else:
                            df = pd.read_sql_query(statement, conn)
                            st.markdown(f"📊 **Résultat requête {i+1}:**")
                            st.dataframe(df, use_container_width=True)
                            
                            if not df.empty:
                                href_csv, href_excel = prepare_download_links(df)
                                with st.expander(f"📥 Télécharger résultat requête {i+1}"):
                                    st.markdown(href_csv, unsafe_allow_html=True)
                                    st.markdown(href_excel, unsafe_allow_html=True)
                            
                            results.append(f"Requête {i+1}: {len(df)} résultats")
                    
                    except Exception as e:
                        st.error(f"❌ Erreur requête {i+1}: {e}")
                        results.append(f"Requête {i+1}: Erreur - {e}")
                
                # Résumé final et SQL optionnel
                if len(sql_statements) > 1:
                    st.markdown("---")
                    st.markdown("### 📋 Résumé d'exécution:")
                    for result in results:
                        st.markdown(f"- {result}")
                
                # SQL en option (masqué par défaut)
                with st.expander("🔍 Voir les requêtes SQL générées", expanded=False):
                    for i, statement in enumerate(sql_statements):
                        st.markdown(f"**Requête {i+1}:**")
                        st.code(statement, language="sql")
                
                # Message pour l'historique
                if modification_made:
                    response = f"✅ {len(sql_statements)} requête(s) exécutée(s) avec succès"
                else:
                    response = f"📊 {len(sql_statements)} requête(s) de consultation exécutée(s)"
                
                st.session_state.messages.append({"role": "assistant", "content": response})

        except Exception as e:
            response = f"❌ Erreur : {e}"
            st.chat_message("assistant", avatar=BOT_AVATAR).markdown(response)
            st.session_state.messages.append({"role": "assistant", "content": response})

        save_chat_history(st.session_state.messages)

elif page == "🤖 AI Visualization":
    # Import de la logique AI Viz
    from core.ai_viz_logic import run_ai_viz_pipeline, init_chroma_client, init_sql_connection, process_uploaded_file, add_document_to_chroma
    import pandas as pd
    import base64
    
    # Initialiser les clés de session spécifiques à cet onglet avec persistance
    if "ai_viz_messages" not in st.session_state:
        st.session_state.ai_viz_messages = load_ai_viz_history()
    
    # Sidebar pour la configuration
    with st.sidebar:
        st.markdown("---")
        st.markdown("### ⚙️ Configuration AI Viz")
        
        # Statut des connexions
        chroma_client, collection = init_chroma_client()
        sql_conn = init_sql_connection()
        
        if collection:
            doc_count = collection.count()
            st.success(f"✅ ChromaDB ({doc_count} documents)")
        else:
            st.error("❌ ChromaDB non disponible")
            
        if sql_conn:
            try:
                test_contacts = pd.read_sql_query("SELECT COUNT(*) as count FROM contacts", sql_conn)
                test_companies = pd.read_sql_query("SELECT COUNT(*) as count FROM companies", sql_conn)
                contacts_count = test_contacts['count'].iloc[0]
                companies_count = test_companies['count'].iloc[0]
                st.success(f"✅ Base SQL ({contacts_count} contacts, {companies_count} entreprises)")
            except:
                st.warning("⚠️ Base SQL (erreur)")
        else:
            st.error("❌ Base SQL non disponible")
        
        # Upload de documents
        st.markdown("---")
        st.markdown("### 📁 Upload Documents")
        uploaded_files = st.file_uploader(
            "Ajouter des documents à ChromaDB",
            type=['txt', 'pdf', 'docx'],
            accept_multiple_files=True,
            key="ai_viz_uploader"
        )
        
        if uploaded_files and collection:
            for uploaded_file in uploaded_files:
                file_key = f"ai_viz_processed_{uploaded_file.name}_{uploaded_file.size}"
                
                if file_key not in st.session_state:
                    with st.spinner(f"Traitement de {uploaded_file.name}..."):
                        content = process_uploaded_file(uploaded_file)
                        
                        if content.startswith("❌"):
                            st.error(content)
                        else:
                            chunks_added = add_document_to_chroma(collection, uploaded_file.name, content)
                            if chunks_added > 0:
                                st.success(f"✅ {uploaded_file.name} ajouté ({chunks_added} chunks)")
                                st.session_state[file_key] = True
                                st.rerun()
                            else:
                                st.error("❌ Échec de l'ajout")
                else:
                    st.info(f"📄 {uploaded_file.name} déjà traité")
    
    # === Affichage du chat AI Visualization ===
    for message in st.session_state.ai_viz_messages:
        avatar = USER_AVATAR if message["role"] == "user" else BOT_AVATAR
        with st.chat_message(message["role"], avatar=avatar):
            if message["role"] == "assistant" and "image" in message:
                # Afficher l'image
                st.image(message["image"], use_container_width=True)
                
                # Afficher les détails dans un expander
                with st.expander("🔍 Détails de l'analyse"):
                    if "routing" in message:
                        st.info(f"🧠 Routage IA : {message['routing']}")
                    if "sql" in message and message["sql"]:
                        st.markdown("**🗃️ SQL générée :**")
                        st.code(message["sql"], language="sql")
                    if "code" in message and message["code"]:
                        st.markdown("**💻 Code Python :**")
                        st.code(message["code"], language="python")
                    if "df" in message and message["df"] is not None and not message["df"].empty:
                        st.markdown("**📊 Données utilisées :**")
                        st.dataframe(message["df"].head())
                    if "vector_context" in message and message["vector_context"]:
                        st.markdown("**📄 Contexte documentaire :**")
                        st.text_area("", message["vector_context"][:500] + "...", height=100, disabled=True)
            else:
                st.markdown(message["content"])

    # === Interaction utilisateur ===
    if prompt := st.chat_input("Que veux-tu visualiser ? (ex: graphique des ventes, analyse NewJeans...)"):
        # Afficher le message utilisateur
        st.chat_message("user", avatar=USER_AVATAR).markdown(prompt)
        st.session_state.ai_viz_messages.append({"role": "user", "content": prompt})

        # Traitement avec l'IA
        with st.chat_message("assistant", avatar=BOT_AVATAR):
            with st.spinner("🤖 Analyse et génération en cours..."):
                try:
                    result = run_ai_viz_pipeline(prompt, st.session_state.ai_viz_messages)
                    
                    if result['image_bytes']:
                        # Cas avec visualisation
                        st.image(result['image_bytes'], use_container_width=True)
                        
                        # Préparer le message pour l'historique
                        message = {
                            "role": "assistant",
                            "content": "📊 Visualisation générée avec succès !",
                            "image": result['image_bytes'],
                            "routing": result['routing'],
                            "sql": result['sql'],
                            "code": result['code'],
                            "df": result['df'],
                            "vector_context": result['vector_context']
                        }
                        
                        # Afficher les détails
                        with st.expander("🔍 Détails de l'analyse"):
                            st.info(f"🧠 Routage IA : {result['routing']}")
                            if result['sql']:
                                st.markdown("**🗃️ SQL générée :**")
                                st.code(result['sql'], language="sql")
                            if result['code']:
                                st.markdown("**💻 Code Python :**")
                                st.code(result['code'], language="python")
                            if result['df'] is not None and not result['df'].empty:
                                st.markdown("**📊 Données utilisées :**")
                                st.dataframe(result['df'].head())
                            if result['vector_context']:
                                st.markdown("**📄 Contexte documentaire :**")
                                st.text_area("", result['vector_context'][:500] + "...", height=100, disabled=True)
                                
                    elif result['vector_context'] and not result['vector_context'].startswith("Aucun document"):
                        # Cas avec analyse documentaire (pas de graphique)
                        if result['code'].strip().startswith('#'):
                            # Si c'est une analyse textuelle
                            analysis_text = result['code'].replace('# ', '').replace('#', '')
                            st.markdown("### 📄 Analyse basée sur les documents")
                            st.markdown(analysis_text)
                        else:
                            st.markdown("### 💻 Code d'analyse généré")
                            st.code(result['code'], language="python")
                        
                        message = {
                            "role": "assistant", 
                            "content": "📄 Analyse documentaire terminée",
                            "routing": result['routing'],
                            "code": result['code'],
                            "vector_context": result['vector_context']
                        }
                        
                    elif result['error']:
                        # Cas d'erreur
                        st.error(f"❌ Erreur lors de la génération : {result['error']}")
                        st.code(result['code'], language="python")
                        message = {"role": "assistant", "content": f"❌ Erreur : {result['error']}"}
                        
                    else:
                        # Cas par défaut
                        st.warning("⚠️ Aucune donnée pertinente trouvée pour générer une visualisation.")
                        message = {"role": "assistant", "content": "⚠️ Aucune donnée pertinente trouvée."}
                    
                    st.session_state.ai_viz_messages.append(message)
                    save_ai_viz_history(st.session_state.ai_viz_messages)
                     
                except Exception as e:
                    error_msg = f"❌ Erreur lors du traitement : {e}"
                    st.error(error_msg)
                    st.session_state.ai_viz_messages.append({"role": "assistant", "content": error_msg})
                    save_ai_viz_history(st.session_state.ai_viz_messages)

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
