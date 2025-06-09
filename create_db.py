import sqlite3
import pandas as pd
import os

# Chemins vers les fichiers CSV
CONTACTS_CSV = "data/Mémoire BDD Clients - Contact.csv"
COMPANIES_CSV = "data/Mémoire BDD Clients - Company.csv"

# Nom de la base SQLite
DB_PATH = os.getenv("DB_PATH", "bdd_clients.db")

def create_database():
    # Chargement des données
    contacts_df = pd.read_csv(CONTACTS_CSV)
    companies_df = pd.read_csv(COMPANIES_CSV)

    # Connexion à SQLite
    conn = sqlite3.connect(DB_PATH)
    contacts_df.to_sql("contacts", conn, if_exists="replace", index=False)
    companies_df.to_sql("companies", conn, if_exists="replace", index=False)

    print("✅ Base de données créée avec succès.")
    conn.close()

if __name__ == "__main__":
    create_database()
