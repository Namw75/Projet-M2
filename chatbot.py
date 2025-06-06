from core.db import get_connection
from core.gpt_sql import get_sql_from_gpt
import pandas as pd

conn = get_connection()
cursor = conn.cursor()

print("💬 Chatbot SQL - tape 'exit' pour quitter")

while True:
    query = input("🧠> ")
    if query.strip().lower() == "exit":
        break

    sql = get_sql_from_gpt(query)
    print(f"🧾 SQL générée : {sql}")

    try:
        if sql.lower().startswith(("insert", "update", "delete")):
            cursor.execute(sql)
            conn.commit()
            print("✅ Opération effectuée.")
        else:
            df = pd.read_sql_query(sql, conn)
            print(df.head(10).to_markdown())
    except Exception as e:
        print("❌ Erreur :", e)
