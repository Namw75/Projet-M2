import openai
import pandas as pd
import streamlit as st
import matplotlib.pyplot as plt
import io

# ==== VECTOR SEARCH EXEMPLE ====
def search_vector_db(query, chroma_client):
    # Ici tu implémentes ta recherche sémantique dans ChromaDB selon ta logique
    # Renvoie un texte/context utile pour l’IA
    results = chroma_client.query(query_texts=[query], n_results=5)
    return "\n".join([doc for doc in results['documents'][0]])

# ==== SQL SEARCH EXEMPLE ====
def search_sql_db(query, conn):
    # On suppose que tu as déjà une fonction GPT qui transforme la demande en SQL (genre core.gpt_sql.get_sql_from_gpt)
    from core.gpt_sql import get_sql_from_gpt
    sql = get_sql_from_gpt(query)
    df = pd.read_sql_query(sql, conn)
    return df, sql

# ==== IA SELECTION & CODE GEN ====
def ai_generate_viz(user_request, df=None, vector_context=None):
    # Prépare le prompt selon les datas disponibles
    head_df = df.head(5).to_string() if df is not None else ""
    context = f"\nVoici des informations issues de documents :\n{vector_context}\n" if vector_context else ""
    prompt = f"""
    L'utilisateur te demande : {user_request}
    {context}
    Voici les premières lignes du dataframe (si pertinent) :
    {head_df}
    Génère uniquement le code Python (pandas/matplotlib) qui permet de visualiser la donnée de la façon la plus pertinente (ex: pie chart, bar plot, courbe, etc.). Choisis le type de graphique le plus adapté à la demande, pas de texte, seulement le code. Suppose que le dataframe s'appelle df.
    """
    response = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[
            {"role": "system", "content": "Tu es un expert en data visualisation Python."},
            {"role": "user", "content": prompt}
        ],
        max_tokens=500
    )
    # Ne garder QUE le code (enlève les ```python éventuels)
    code = response.choices[0].message['content']
    code = code.replace("```python", "").replace("```", "").strip()
    return code

# ==== EXECUTION DU CODE DE VIZ ====
def exec_and_display_plot(code, df):
    import matplotlib
    matplotlib.use('Agg')
    local_vars = {'df': df, 'plt': plt}
    try:
        exec(code, {}, local_vars)
        buf = io.BytesIO()
        plt.savefig(buf, format="png")
        st.image(buf.getvalue())
        plt.close()
    except Exception as e:
        st.error(f"Erreur lors de la génération du graphique : {e}")

# ==== PIPELINE PRINCIPAL ====
def run_viz_pipeline(user_request, chroma_client, sql_conn):
    # 1. On demande à l'IA si la question vise plutôt la base SQL ou les docs PDF
    routing_prompt = f"""L'utilisateur demande : "{user_request}"
    S'il s'agit d'une donnée structurée (ex: clients, stats numériques), réponds simplement "SQL".
    Si la réponse se trouve dans des documents (PDF, texte libre, campagnes passées...), réponds simplement "VECTOR".
    Si les deux sont utiles, réponds "BOTH".
    Ne donne aucune explication, juste un mot clé.
    """
    routing = openai.ChatCompletion.create(
        model="gpt-4o",
        messages=[{"role": "user", "content": routing_prompt}],
        max_tokens=10
    ).choices[0].message['content'].strip().upper()

    # 2. On récupère la donnée selon le routage IA
    df, sql, vector_context = None, None, None
    if routing == "SQL":
        df, sql = search_sql_db(user_request, sql_conn)
    elif routing == "VECTOR":
        vector_context = search_vector_db(user_request, chroma_client)
    elif routing == "BOTH":
        df, sql = search_sql_db(user_request, sql_conn)
        vector_context = search_vector_db(user_request, chroma_client)
    else:
        st.error("Impossible de déterminer la source de données à utiliser.")
        return

    # 3. On génère le code de visualisation pertinent
    code = ai_generate_viz(user_request, df=df, vector_context=vector_context)

    # 4. On exécute le code (s'il y a un df, sinon afficher le contexte)
    if df is not None and not df.empty:
        exec_and_display_plot(code, df)
        st.code(code, language="python")
        if sql:
            st.info(f"SQL utilisée :\n{sql}")
    elif vector_context:
        st.markdown(f"**Contexte extrait des documents :**\n\n{vector_context}")
        st.code(code, language="python")
        # Optionnel : générer une explication IA ou un résumé de ce contexte/document
    else:
        st.warning("Aucune donnée pertinente trouvée.")

