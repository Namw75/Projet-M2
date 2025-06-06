import sqlite3
import pandas as pd

# === Chargement des CSV ===
contacts_df = pd.read_csv("Mémoire BDD Clients - Contact .csv")
companies_df = pd.read_csv("Mémoire BDD Clients - Company.csv")

# === Connexion SQLite ===
conn = sqlite3.connect("bdd_clients.db")
cursor = conn.cursor()

# === Sauvegarde dans SQLite ===
contacts_df.to_sql("contacts", conn, if_exists="replace", index=False)
companies_df.to_sql("companies", conn, if_exists="replace", index=False)

# === Vérification rapide ===
print("Tables créées avec succès :")
for row in cursor.execute("SELECT name FROM sqlite_master WHERE type='table';"):
    print(f" - {row[0]}")

conn.close()
