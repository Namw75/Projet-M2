import openai
import pandas as pd
import matplotlib.pyplot as plt
import io
import os
from dotenv import load_dotenv
import chromadb
import uuid
from datetime import datetime
import sqlite3

# Charger les variables d'environnement
load_dotenv('.env')

# Configuration OpenAI (nouvelle API v1.0+)
client = openai.OpenAI(api_key=os.getenv('OPENAI_API_KEY'))

# ==== CONFIGURATION CHROMADB ====
def init_chroma_client():
    """Initialise le client ChromaDB"""
    try:
        chroma_client = chromadb.PersistentClient(path="./chroma_db")
        try:
            collection = chroma_client.get_collection(name="documents")
        except:
            collection = chroma_client.create_collection(name="documents")
        return chroma_client, collection
    except Exception as e:
        print(f"❌ Erreur ChromaDB : {e}")
        return None, None

def init_sql_connection():
    """Initialise la connexion à la base de données SQLite"""
    try:
        conn = sqlite3.connect("bdd_clients.db")
        return conn
    except Exception as e:
        print(f"❌ Erreur connexion SQL : {e}")
        return None

# ==== VECTOR SEARCH AVEC CHROMADB ====
def search_vector_db(query, collection):
    """Recherche sémantique dans ChromaDB"""
    try:
        results = collection.query(
            query_texts=[query], 
            n_results=10,
            include=['documents', 'metadatas', 'distances']
        )
        
        if results['documents'] and results['documents'][0]:
            documents = results['documents'][0]
            distances = results['distances'][0] if 'distances' in results else []
            
            relevant_docs = []
            for i, (doc, distance) in enumerate(zip(documents, distances)):
                if distance < 2.0:  # Seuil de pertinence
                    relevant_docs.append(doc)
            
            if relevant_docs:
                combined_context = "\n\n".join(relevant_docs)
                return combined_context
            elif documents:
                return f"Document le plus proche trouvé :\n{documents[0]}"
            else:
                return f"Aucun document trouvé pour '{query}'"
        else:
            return "Aucun document trouvé dans ChromaDB"
            
    except Exception as e:
        return f"Erreur ChromaDB: {e}"

# ==== SQL SEARCH ====
def search_sql_db(query, conn, conversation_history=None):
    """Recherche dans la base SQL avec génération automatique de requêtes"""
    try:
        from core.gpt_sql import get_sql_from_gpt
        sql = get_sql_from_gpt(query, conversation_history)
        df = pd.read_sql_query(sql, conn)
        return df, sql
    except ImportError:
        # Fallback avec données d'exemple
        df = get_sample_data()
        sql = "-- Module gpt_sql manquant, données d'exemple utilisées"
        return df, sql
    except Exception as e:
        df = get_sample_data()
        sql = f"-- Erreur SQL: {e}, données d'exemple utilisées"
        return df, sql

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
        
        🔧 INSTRUCTIONS POUR LA VISUALISATION :
        - Génère uniquement le code Python (pandas/matplotlib) qui permet de visualiser la donnée de la façon la plus pertinente
        - Choisis le type de graphique le plus adapté à la demande (pie chart, bar plot, courbe, etc.)
        - Suppose que le dataframe s'appelle df
        - Ne mets pas de ```python``` dans ta réponse, juste le code pur
        
        🛡️ GESTION DES ERREURS :
        - TOUJOURS gérer les valeurs NULL/NaN dans les données
        - Utiliser df.fillna('Non spécifié') ou df.dropna() selon le contexte
        - Vérifier que les données ne sont pas vides avant de créer le graphique
        - Utiliser des couleurs différentes pour chaque catégorie
        - Ajouter des titres, labels et légendes appropriés
        
        📊 EXEMPLES DE CODE ROBUSTE :
        ```python
        # Exemple pour un graphique en barres avec gestion des NULL
        df_clean = df.copy()
        df_clean = df_clean.fillna('Non spécifié')  # Remplacer les NaN
        colors = ['#ff1744', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5']
        
        plt.figure(figsize=(12, 6))
        bars = plt.bar(df_clean['colonne'], df_clean['valeur'], color=colors[:len(df_clean)])
        plt.xlabel('X Label')
        plt.ylabel('Y Label')
        plt.title('Titre du graphique')
        plt.xticks(rotation=45, ha='right')
        plt.tight_layout()
        ```
        
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
def execute_viz_code(code, df):
    """Exécute le code de visualisation et retourne l'image en bytes"""
    import matplotlib
    matplotlib.use('Agg')
    local_vars = {'df': df, 'plt': plt, 'pd': pd}
    
    try:
        exec(code, {}, local_vars)
        buf = io.BytesIO()
        plt.tight_layout()
        plt.savefig(buf, format="png", dpi=150, bbox_inches='tight')
        plt.close()
        buf.seek(0)
        return buf.getvalue(), None
    except Exception as e:
        return None, str(e)

# ==== PIPELINE PRINCIPAL ====
def run_ai_viz_pipeline(user_request, conversation_history=None):
    """Pipeline principal avec routage IA intelligent"""
    
    # Initialiser les connexions
    chroma_client, collection = init_chroma_client()
    sql_conn = init_sql_connection()
    
    # 1. Routage IA amélioré avec détection contextuelle
    context_info = ""
    force_sql = False
    
    if conversation_history and len(conversation_history) > 1:
        recent_context = conversation_history[-6:]  # 3 derniers échanges
        
        # Rechercher les mots-clés SQL dans l'historique
        for msg in recent_context:
            content_lower = msg["content"].lower()
            if any(keyword in content_lower for keyword in [
                "contacts", "entreprise", "société", "clients", "base", 
                "sql", "données", "nombre_de_contacts", "graphique", "barres",
                "secteur", "activité", "repartition", "répartition"
            ]):
                context_info = "\nCONTEXTE: La conversation précédente portait sur des données de contacts/entreprises de la base SQL."
                
                # Si l'utilisateur fait référence avec des pronoms OU demande une visualisation, forcer SQL
                visualization_keywords = ["camembert", "pie", "graphique", "visuel", "visualisation", "diagramme"]
                if (any(ref in user_request.lower() for ref in ["les", "ça", "ceux", "celles", "cette", "ces"]) or
                    any(viz in user_request.lower() for viz in visualization_keywords)):
                    force_sql = True
                break

    if force_sql:
        routing = "SQL"
    else:
        routing_prompt = f"""L'utilisateur demande : "{user_request}"{context_info}
        
        RÈGLES DE ROUTAGE :
        - Si ça concerne des données de contacts, entreprises, clients, bases de données → "SQL"
        - Si ça concerne des documents PDF, analyses NewJeans/HYBE, rapports → "VECTOR"  
        - Si l'utilisateur fait référence à "les", "ça", "ceux-là" et que le contexte indique des données SQL → "SQL"
        - Si les deux sources sont utiles → "BOTH"
        
        Réponds UNIQUEMENT par un mot : SQL, VECTOR ou BOTH.
        """
        
        try:
            routing = client.chat.completions.create(
                model="gpt-4",
                messages=[{"role": "user", "content": routing_prompt}],
                max_tokens=10
            ).choices[0].message.content.strip().upper()
        except Exception as e:
            routing = "SQL"  # Fallback

    # 2. Récupérer les données selon le routage
    df, sql, vector_context = None, None, None
    
    if routing == "SQL":
        if sql_conn:
            df, sql = search_sql_db(user_request, sql_conn, conversation_history)
        else:
            df, sql = get_sample_data(), "-- Pas de connexion SQL"
            
    elif routing == "VECTOR":
        if collection:
            vector_context = search_vector_db(user_request, collection)
        else:
            vector_context = "Pas de connexion ChromaDB configurée."
            df = get_sample_data()
            
    elif routing == "BOTH":
        if sql_conn:
            df, sql = search_sql_db(user_request, sql_conn, conversation_history)
        else:
            df, sql = get_sample_data(), "-- Pas de connexion SQL"
            
        if collection:
            vector_context = search_vector_db(user_request, collection)
        else:
            vector_context = "Pas de connexion ChromaDB configurée."

    # 3. Générer le code de visualisation
    code = ai_generate_viz(user_request, df=df, vector_context=vector_context)

    # 4. Résultats
    result = {
        'routing': routing,
        'df': df,
        'sql': sql,
        'vector_context': vector_context,
        'code': code,
        'image_bytes': None,
        'error': None
    }
    
    # 5. Exécuter le code si on a des données
    if df is not None and not df.empty:
        image_bytes, error = execute_viz_code(code, df)
        result['image_bytes'] = image_bytes
        result['error'] = error
    
    return result

# ==== FONCTIONS UTILITAIRES POUR L'UPLOAD ====
def process_uploaded_file(uploaded_file):
    """Traite un fichier uploadé et retourne le texte"""
    try:
        if uploaded_file.type == "text/plain":
            content = str(uploaded_file.read(), "utf-8")
            return content
        elif uploaded_file.type == "application/pdf":
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
        
        if end < len(text):
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
        print(f"Erreur lors de l'ajout à ChromaDB : {e}")
        return 0 