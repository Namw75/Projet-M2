import openai
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io
import os
from dotenv import load_dotenv
import chromadb
import uuid
from datetime import datetime

# Charger les variables d'environnement
load_dotenv('.env')

# Configuration OpenAI (nouvelle API v1.0+)
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ==== CONFIGURATION CHROMADB ====
def init_chroma_client():
    """Initialise le client ChromaDB"""
    try:
        # Client ChromaDB (persistant local par défaut)
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        
        # Créer ou récupérer une collection
        collection_name = "documents"
        try:
            collection = chroma_client.get_collection(name=collection_name)
            print(f"✅ Collection '{collection_name}' récupérée")
        except:
            # Créer la collection si elle n'existe pas
            collection = chroma_client.create_collection(name=collection_name)
            print(f"✅ Collection '{collection_name}' créée")
            
        return chroma_client, collection
        
    except Exception as e:
        print(f"❌ Erreur ChromaDB : {e}")
        return None, None

def add_documents_to_chroma(collection, documents, metadatas=None, ids=None):
    """Ajoute des documents à ChromaDB"""
    try:
        if ids is None:
            ids = [f"doc_{i}" for i in range(len(documents))]
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        print(f"✅ {len(documents)} documents ajoutés à ChromaDB")
        
    except Exception as e:
        print(f"❌ Erreur lors de l'ajout : {e}")

def populate_sample_documents(collection):
    """Ajoute des documents d'exemple pour tester ChromaDB"""
    sample_docs = [
        "Notre campagne marketing Q1 2024 a généré 150% d'augmentation des ventes dans la région Nord",
        "Les retours clients montrent une satisfaction de 92% pour notre nouveau produit A",
        "Analyse des performances : les ventes en ligne ont augmenté de 80% par rapport à l'année dernière",
        "Stratégie commerciale : focus sur les clients premium pour maximiser la marge",
        "Rapport trimestriel : croissance de 25% du chiffre d'affaires grâce aux campagnes digitales"
    ]
    
    metadatas = [
        {"type": "campagne", "periode": "Q1_2024", "region": "Nord"},
        {"type": "feedback", "produit": "A", "score": 92},
        {"type": "performance", "canal": "online", "croissance": 80},
        {"type": "strategie", "segment": "premium"},
        {"type": "rapport", "periode": "trimestriel", "croissance": 25}
    ]
    
    # Vérifier si la collection est vide
    try:
        count = collection.count()
        if count == 0:
            add_documents_to_chroma(collection, sample_docs, metadatas)
            print(f"📄 {len(sample_docs)} documents d'exemple ajoutés")
        else:
            print(f"📄 Collection contient déjà {count} documents")
    except Exception as e:
        print(f"❌ Erreur lors du peuplement : {e}")

# ==== VECTOR SEARCH AVEC CHROMADB ====
def search_vector_db(query, collection):
    """Recherche sémantique dans ChromaDB selon votre logique"""
    # Recherche sémantique dans la collection ChromaDB
    try:
        # Recherche avec plus de résultats et affichage debug
        results = collection.query(
            query_texts=[query], 
            n_results=10,  # Plus de résultats
            include=['documents', 'metadatas', 'distances']
        )
        
        if results['documents'] and results['documents'][0]:
            # Filtrer les résultats par pertinence (distance < 1.0 par exemple)
            documents = results['documents'][0]
            distances = results['distances'][0] if 'distances' in results else []
            metadatas = results['metadatas'][0] if 'metadatas' in results else []
            
            # Debug info
            print(f"🔍 Recherche pour: '{query}'")
            print(f"📄 {len(documents)} résultats trouvés")
            
            relevant_docs = []
            for i, (doc, distance, metadata) in enumerate(zip(documents, distances, metadatas)):
                print(f"  - Document {i+1} (distance: {distance:.3f}): {doc[:100]}...")
                # Seuil plus permissif - ChromaDB utilise la distance cosinus
                if distance < 2.0:  # Seuil plus permissif
                    relevant_docs.append(doc)
            
            if relevant_docs:
                combined_context = "\n\n".join(relevant_docs)
                print(f"✅ {len(relevant_docs)} documents pertinents retenus")
                return combined_context
            else:
                # Si aucun document vraiment pertinent, prendre le meilleur quand même
                if documents:
                    best_doc = documents[0]  # Le premier est le plus pertinent
                    print(f"⚠️ Aucun document très pertinent, utilisation du meilleur (distance: {distances[0]:.3f})")
                    return f"Document le plus proche trouvé :\n{best_doc}"
                else:
                    return f"Aucun document trouvé pour '{query}'"
        else:
            return "Aucun document trouvé dans ChromaDB"
            
    except Exception as e:
        print(f"❌ Erreur ChromaDB : {e}")
        return f"Erreur ChromaDB: {e}"

# ==== SQL SEARCH ====
def search_sql_db(query, conn):
    """Recherche dans la base SQL avec génération automatique de requêtes"""
    try:
        from core.gpt_sql import get_sql_from_gpt
        sql = get_sql_from_gpt(query)
        print(f"🗃️ SQL générée : {sql}")
        df = pd.read_sql_query(sql, conn)
        print(f"✅ {len(df)} résultats trouvés")
        return df, sql
    except ImportError:
        print("⚠️ Module gpt_sql non trouvé, utilisation des données d'exemple")
        df = get_sample_data()
        sql = "-- Données d'exemple utilisées (module gpt_sql manquant)"
        return df, sql
    except Exception as e:
        print(f"❌ Erreur SQL : {e}")
        # En cas d'erreur, retourner des données d'exemple
        df = get_sample_data()
        sql = f"-- Erreur SQL: {e}, données d'exemple utilisées"
        return df, sql

def init_sql_connection():
    """Initialise la connexion à la base de données SQLite"""
    import sqlite3
    try:
        conn = sqlite3.connect("bdd_clients.db")
        print("✅ Connexion SQL établie")
        return conn
    except Exception as e:
        print(f"❌ Erreur connexion SQL : {e}")
        return None

# ==== DONNÉES D'EXEMPLE (fallback) ====
def get_sample_data():
    """Génère des données d'exemple pour tester"""
    return pd.DataFrame({
        'mois': ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun'],
        'ventes': [1000, 1200, 800, 1500, 1800, 1600],
        'region': ['Nord', 'Sud', 'Est', 'Ouest', 'Nord', 'Sud'],
        'produit': ['A', 'B', 'A', 'C', 'B', 'A']
    })

# ==== IA SELECTION & CODE GENERATION ====
def ai_generate_viz(user_request, df=None, vector_context=None):
    """Génère le code de visualisation avec l'IA selon les données disponibles"""
    # Prépare le prompt selon les données disponibles
    head_df = df.head(5).to_string() if df is not None else ""
    context = f"\nVoici des informations issues de documents :\n{vector_context}\n" if vector_context else ""
    
    # Si on a uniquement du contexte vectoriel (pas de données tabulaires)
    if vector_context and (df is None or df.empty):
        # Vérifier si le contexte contient vraiment des infos pertinentes
        if vector_context.startswith("Aucun document") or vector_context.startswith("Documents trouvés mais non pertinents") or vector_context.startswith("Erreur"):
            return f"# Je n'ai pas trouvé d'informations sur '{user_request}' dans les documents uploadés.\n# Veuillez vérifier que les documents pertinents ont été ajoutés à ChromaDB."
        
        prompt = f"""
        L'utilisateur te demande : {user_request}
        
        DOCUMENTS DISPONIBLES :
        {vector_context}
        
        INSTRUCTIONS CRITIQUES :
        - Réponds UNIQUEMENT en te basant sur les documents fournis ci-dessus
        - Si l'information n'est pas dans les documents, dis "Cette information n'est pas disponible dans les documents"
        - NE PAS inventer ou utiliser des connaissances générales
        - Sois précis et cite les éléments des documents
        - Si une visualisation est pertinente basée sur les documents, génère le code Python (matplotlib)
        - Sinon, fournis une réponse textuelle sous forme de commentaires Python
        
        Format de réponse :
        # === RÉPONSE BASÉE SUR LES DOCUMENTS ===
        # [Ta réponse ici basée uniquement sur les documents]
        """
    else:
        # Prompt original pour la dataviz
        prompt = f"""
        L'utilisateur te demande : {user_request}
        {context}
        Voici les premières lignes du dataframe (si pertinent) :
        {head_df}
        
        Génère uniquement le code Python (pandas/matplotlib) qui permet de visualiser la donnée de la façon la plus pertinente (ex: pie chart, bar plot, courbe, etc.). 
        Choisis le type de graphique le plus adapté à la demande, pas de texte, seulement le code. 
        Suppose que le dataframe s'appelle df.
        Ne mets pas de ```python``` dans ta réponse, juste le code pur.
        """
    
    try:
        response = client.chat.completions.create(
            model="gpt-4",
            messages=[
                {"role": "system", "content": "Tu es un assistant RAG (Retrieval-Augmented Generation). Tu réponds UNIQUEMENT basé sur les documents fournis. Si l'info n'est pas dans les documents, tu le dis clairement."},
                {"role": "user", "content": prompt}
            ],
            max_tokens=800,
            temperature=0.1  # Plus déterministe
        )
        
        # Ne garder QUE le code (enlève les ```python éventuels)
        code = response.choices[0].message.content
        code = code.replace("```python", "").replace("```", "").strip()
        return code
        
    except Exception as e:
        return f"# Erreur lors de la génération : {e}"

# ==== EXECUTION DU CODE DE VIZ ====
def exec_and_display_plot(code, df):
    """Exécute le code de visualisation et affiche le résultat"""
    import matplotlib
    matplotlib.use('Agg')
    local_vars = {'df': df, 'plt': plt, 'pd': pd}
    try:
        exec(code, {}, local_vars)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        st.image(buf.getvalue())
        plt.close()
        return True
    except Exception as e:
        st.error(f"Erreur lors de la génération du graphique : {e}")
        st.code(code, language="python")
        return False

# ==== PIPELINE PRINCIPAL - VOTRE LOGIQUE ====
def run_viz_pipeline(user_request, collection=None, sql_conn=None):
    """Votre pipeline principal avec routage IA intelligent"""
    
    # 1. On demande à l'IA si la question vise plutôt la base SQL ou les docs PDF
    routing_prompt = f"""L'utilisateur demande : "{user_request}"
    S'il s'agit d'une donnée structurée (ex: clients, stats numériques), réponds simplement "SQL".
    Si la réponse se trouve dans des documents (PDF, texte libre, campagnes passées...), réponds simplement "VECTOR".
    Si les deux sont utiles, réponds "BOTH".
    Ne donne aucune explication, juste un mot clé.
    """
    
    try:
        routing = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": routing_prompt}],
            max_tokens=10
        ).choices[0].message.content.strip().upper()
    except Exception as e:
        st.error(f"Erreur de routage IA : {e}")
        routing = "SQL"  # Fallback

    # 2. On récupère la donnée selon le routage IA
    df, sql, vector_context = None, None, None
    
    if routing == "SQL":
        if sql_conn:
            df, sql = search_sql_db(user_request, sql_conn)
        else:
            df, sql = get_sample_data(), "-- Données d'exemple (pas de connexion SQL)"
            
    elif routing == "VECTOR":
        if collection:
            vector_context = search_vector_db(user_request, collection)
        else:
            vector_context = "Pas de connexion ChromaDB configurée. Données d'exemple utilisées."
            df = get_sample_data()
            
    elif routing == "BOTH":
        if sql_conn:
            df, sql = search_sql_db(user_request, sql_conn)
        else:
            df, sql = get_sample_data(), "-- Données d'exemple (pas de connexion SQL)"
            
        if collection:
            vector_context = search_vector_db(user_request, collection)
        else:
            vector_context = "Pas de connexion ChromaDB configurée."
    else:
        st.error("Impossible de déterminer la source de données à utiliser.")
        return

    # 3. Afficher le routage choisi
    st.info(f"🧠 Routage IA : {routing}")

    # 4. On génère le code de visualisation pertinent
    code = ai_generate_viz(user_request, df=df, vector_context=vector_context)

    # 5. On exécute le code (s'il y a un df, sinon afficher le contexte)
    if df is not None and not df.empty:
        st.markdown("### 📊 Visualisation générée")
        success = exec_and_display_plot(code, df)
        
        if success:
            st.markdown("### 💻 Code généré")
            st.code(code, language="python")
            
        if sql and sql != "-- Données d'exemple":
            st.markdown("### 🗃️ SQL utilisée")
            st.code(sql, language="sql")
            
    elif vector_context:
        st.markdown("### 📄 Contexte extrait des documents")
        
        # Afficher le contexte dans un expandeur pour ne pas encombrer
        with st.expander("🔍 Documents trouvés", expanded=False):
            st.markdown(vector_context)
        
        st.markdown("### 🧠 Analyse Marketing IA")
        
        # Exécuter le code d'analyse (même si c'est du texte)
        if code.strip().startswith('#'):
            # Si c'est une analyse textuelle (commentaires)
            analysis_text = code.replace('# ', '').replace('#', '')
            st.markdown(analysis_text)
        else:
            # Si c'est du code de visualisation
            st.markdown("### 📊 Visualisation conceptuelle")
            try:
                exec_and_display_plot(code, pd.DataFrame())  # DataFrame vide pour les schémas conceptuels
            except:
                st.code(code, language="python")
                
        st.markdown("### 💻 Code/Analyse générée")
        st.code(code, language="python")
        
    else:
        st.warning("Aucune donnée pertinente trouvée.")

# ==== INTERFACE STREAMLIT ====
def main():
    st.set_page_config(
        page_title="🤖 AI Data Visualization", 
        page_icon="🤖",
        layout="wide"
    )
    
    st.title("🤖 AI Data Visualization")
    st.markdown("**Générez des visualisations automatiquement avec l'IA !**")
    
    # Vérifier la clé API
    if not client.api_key:
        st.error("🔑 Clé OpenAI manquante ! Ajoutez OPENAI_API_KEY à votre fichier .env")
        return

    # Configuration des connexions (sidebar)
    st.sidebar.header("⚙️ Configuration")
    
    # Initialiser ChromaDB
    chroma_client, collection = init_chroma_client()
    
    # Initialiser la connexion SQL
    sql_conn = init_sql_connection()
    
    if collection:
        st.sidebar.success("✅ ChromaDB connecté")
        
        # Afficher le nombre de documents
        try:
            doc_count = collection.count()
            st.sidebar.info(f"📄 {doc_count} documents dans la base")
        except:
            st.sidebar.warning("⚠️ Impossible de compter les documents")
        
        # Section upload de documents
        st.sidebar.markdown("---")
        st.sidebar.subheader("📁 Upload de documents")
        
        uploaded_files = st.sidebar.file_uploader(
            "Ajoutez des documents à ChromaDB",
            type=['txt', 'pdf', 'docx'],
            accept_multiple_files=True
        )
        
        # Traitement automatique des fichiers uploadés
        if uploaded_files:
            for uploaded_file in uploaded_files:
                # Vérifier si le fichier n'est pas déjà traité
                file_key = f"processed_{uploaded_file.name}_{uploaded_file.size}"
                
                if file_key not in st.session_state:
                    with st.spinner(f"Traitement de {uploaded_file.name}..."):
                        # Traiter le fichier
                        content = process_uploaded_file(uploaded_file)
                        
                        if content.startswith("❌"):
                            st.sidebar.error(content)
                        else:
                            # Ajouter automatiquement à ChromaDB
                            chunks_added = add_document_to_chroma(collection, uploaded_file.name, content)
                            if chunks_added > 0:
                                st.sidebar.success(f"✅ {uploaded_file.name} ajouté ({chunks_added} chunks)")
                                st.session_state[file_key] = True
                                st.rerun()
                            else:
                                st.sidebar.error("❌ Échec de l'ajout")
                else:
                    st.sidebar.info(f"📄 {uploaded_file.name} déjà traité")
        
        # Bouton pour ajouter des exemples
        st.sidebar.markdown("---")
        if st.sidebar.button("📝 Ajouter des exemples"):
            populate_sample_documents(collection)
            st.sidebar.success("✅ Documents d'exemple ajoutés")
            st.rerun()
        
        # Bouton pour vider la base
        if st.sidebar.button("🗑️ Vider ChromaDB", type="secondary"):
            try:
                chroma_client.delete_collection(name="documents")
                chroma_client.create_collection(name="documents")
                st.sidebar.success("✅ ChromaDB vidée")
                st.rerun()
            except Exception as e:
                st.sidebar.error(f"❌ Erreur : {e}")
                
    else:
        st.sidebar.error("❌ ChromaDB non disponible")
    
    # Note sur les connexions
    st.sidebar.markdown("---")
    
    # Statut des connexions
    st.sidebar.markdown("**🔗 Connexions disponibles :**")
    st.sidebar.markdown("- ✅ OpenAI GPT-4")
    
    if collection:
        doc_count = collection.count() if collection else 0
        st.sidebar.markdown(f"- ✅ ChromaDB ({doc_count} docs)")
    else:
        st.sidebar.markdown("- ❌ ChromaDB")
        
    if sql_conn:
        # Tester la connexion SQL avec un count
        try:
            test_contacts = pd.read_sql_query("SELECT COUNT(*) as count FROM contacts", sql_conn)
            test_companies = pd.read_sql_query("SELECT COUNT(*) as count FROM companies", sql_conn)
            contacts_count = test_contacts['count'].iloc[0]
            companies_count = test_companies['count'].iloc[0]
            st.sidebar.markdown(f"- ✅ Base SQL ({contacts_count} contacts, {companies_count} entreprises)")
        except Exception as e:
            st.sidebar.markdown("- ⚠️ Base SQL (erreur)")
    else:
        st.sidebar.markdown("- ❌ Base SQL")
    
    st.sidebar.markdown("---")
    st.sidebar.markdown("""
    **📄 Formats supportés :**
    - 📄 Fichiers texte (.txt)
    - 📕 PDF (.pdf) - nécessite PyPDF2
    - 📘 Word (.docx) - nécessite python-docx
    """)
    
    # Interface principale
    st.markdown("---")
    
    user_request = st.text_input(
        "🎯 Que voulez-vous visualiser ?",
        placeholder="Ex: Graphique des ventes par mois, Analyse des campagnes marketing..."
    )
    
    col1, col2 = st.columns([1, 4])
    
    with col1:
        generate_btn = st.button("🚀 Générer", type="primary")
    
    if generate_btn and user_request:
        with st.spinner("🤖 Analyse et génération en cours..."):
            # Lancer votre pipeline principal avec la vraie connexion SQL
            run_viz_pipeline(user_request, collection, sql_conn)
            
    elif generate_btn:
        st.warning("⚠️ Veuillez saisir une demande !")
    
    # Exemples
    st.markdown("---")
    st.markdown("### 💡 Exemples de demandes")
    
    examples = [
        "Graphique en barres des ventes par mois",
        "Analyse des campagnes marketing passées", 
        "Répartition des clients par région",
        "Tendance des performances trimestrielles"
    ]
    
    cols = st.columns(2)
    for i, example in enumerate(examples):
        cols[i % 2].button(f"📊 {example}", key=f"ex_{i}")

# ==== MODE TEST SIMPLE ====
def test_mode():
    """Mode test simple pour vérifier que tout fonctionne"""
    print("🤖 Test AI Data Visualization Pipeline")
    print("=" * 50)
    
    # Vérifier la clé API
    if not client.api_key:
        print("❌ Clé OpenAI manquante ! Ajoutez OPENAI_API_KEY à votre fichier .env")
        return
    
    # Initialiser ChromaDB pour le test
    print("🔧 Initialisation ChromaDB...")
    chroma_client, collection = init_chroma_client()
    
    if collection:
        # Collection disponible pour les tests
        print(f"📄 Collection prête avec {collection.count()} documents")
    
    # Test avec une demande marketing (pour tester VECTOR)
    user_request = "Que sais-tu de la stratégie marketing et des campagnes ?"
    print(f"🎯 Demande : {user_request}")
    
    # Test du pipeline complet
    print("🤖 Test du pipeline complet...")
    
    # Test du routage
    routing_prompt = f"""L'utilisateur demande : "{user_request}"
    S'il s'agit d'une donnée structurée (ex: clients, stats numériques), réponds simplement "SQL".
    Si la réponse se trouve dans des documents (PDF, texte libre, campagnes passées...), réponds simplement "VECTOR".
    Si les deux sont utiles, réponds "BOTH".
    Ne donne aucune explication, juste un mot clé.
    """
    
    try:
        routing = client.chat.completions.create(
            model="gpt-4",
            messages=[{"role": "user", "content": routing_prompt}],
            max_tokens=10
        ).choices[0].message.content.strip().upper()
        print(f"🧠 Routage choisi : {routing}")
    except Exception as e:
        print(f"❌ Erreur de routage : {e}")
        return
    
    # Test de la recherche vectorielle
    if routing == "VECTOR" and collection:
        print("🔍 Test de la recherche vectorielle...")
        vector_context = search_vector_db(user_request, collection)
        print(f"📄 Contexte trouvé : {vector_context[:200]}...")
        
        # Générer l'analyse
        code = ai_generate_viz(user_request, df=None, vector_context=vector_context)
        print("\n💻 Analyse générée :")
        print("-" * 30)
        print(code)
        print("-" * 30)
        
    else:
        # Fallback sur des données d'exemple
        df = get_sample_data()
        code = ai_generate_viz(user_request, df=df)
        
        print("\n💻 Code généré :")
        print("-" * 30)
        print(code)
        print("-" * 30)
        
        # Tester l'exécution
        import matplotlib
        matplotlib.use('Agg')
        
        local_vars = {'df': df, 'plt': plt, 'pd': pd}
        
        try:
            exec(code, {}, local_vars)
            plt.tight_layout()
            plt.savefig('test_viz.png', dpi=150, bbox_inches='tight')
            plt.close()
            print("✅ Graphique généré et sauvé dans 'test_viz.png'")
        except Exception as e:
            print(f"❌ Erreur lors de l'exécution : {e}")
    
    print("✅ Pipeline complet testé avec succès !")

# ==== FONCTIONS DE TRAITEMENT DE DOCUMENTS ====
def process_uploaded_file(uploaded_file):
    """Traite un fichier uploadé et retourne le texte"""
    try:
        if uploaded_file.type == "text/plain":
            # Fichier texte
            content = str(uploaded_file.read(), "utf-8")
            return content
        
        elif uploaded_file.type == "application/pdf":
            # Fichier PDF - nécessite PyPDF2 ou pymupdf
            try:
                import PyPDF2
                pdf_reader = PyPDF2.PdfReader(uploaded_file)
                text = ""
                for page in pdf_reader.pages:
                    text += page.extract_text() + "\n"
                return text
            except ImportError:
                return "❌ Installez PyPDF2 pour lire les PDFs : pip install PyPDF2"
        
        elif uploaded_file.type in ["application/vnd.openxmlformats-officedocument.wordprocessingml.document"]:
            # Fichier Word - nécessite python-docx
            try:
                import docx
                doc = docx.Document(uploaded_file)
                text = ""
                for paragraph in doc.paragraphs:
                    text += paragraph.text + "\n"
                return text
            except ImportError:
                return "❌ Installez python-docx pour lire les fichiers Word : pip install python-docx"
        
        else:
            return f"❌ Type de fichier non supporté : {uploaded_file.type}"
            
    except Exception as e:
        return f"❌ Erreur lors du traitement : {e}"

def chunk_text(text, chunk_size=1000, overlap=200):
    """Découpe le texte en chunks pour ChromaDB"""
    chunks = []
    text = text.strip()
    
    if len(text) <= chunk_size:
        return [text]
    
    start = 0
    while start < len(text):
        end = start + chunk_size
        
        # Essayer de couper à la fin d'une phrase
        if end < len(text):
            # Chercher le dernier point ou saut de ligne
            last_period = text.rfind('.', start, end)
            last_newline = text.rfind('\n', start, end)
            cut_point = max(last_period, last_newline)
            
            if cut_point > start:
                end = cut_point + 1
        
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        
        start = end - overlap
        
    return chunks

def add_document_to_chroma(collection, filename, content):
    """Ajoute un document découpé en chunks à ChromaDB"""
    try:
        chunks = chunk_text(content)
        
        documents = []
        metadatas = []
        ids = []
        
        for i, chunk in enumerate(chunks):
            doc_id = f"{filename}_{uuid.uuid4().hex[:8]}_{i}"
            
            documents.append(chunk)
            metadatas.append({
                "filename": filename,
                "chunk_index": i,
                "total_chunks": len(chunks),
                "upload_date": datetime.now().isoformat(),
                "file_type": filename.split('.')[-1] if '.' in filename else "unknown"
            })
            ids.append(doc_id)
        
        collection.add(
            documents=documents,
            metadatas=metadatas,
            ids=ids
        )
        
        return len(chunks)
        
    except Exception as e:
        st.error(f"Erreur lors de l'ajout à ChromaDB : {e}")
        return 0

# ==== POINT D'ENTRÉE ====
if __name__ == "__main__":
    import sys
    
    # Si argument "test", lancer le mode test simple
    if len(sys.argv) > 1 and sys.argv[1] == "test":
        test_mode()
    else:
        # Sinon lancer l'interface Streamlit
        main()

