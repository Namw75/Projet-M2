import sqlite3
import pandas as pd

def explore_database():
    """Explore la structure de la base de données clients"""
    print("🔍 Exploration de bdd_clients.db")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect("bdd_clients.db")
        
        # Lister les tables
        tables = pd.read_sql_query("SELECT name FROM sqlite_master WHERE type='table'", conn)
        print("📊 Tables disponibles :")
        for table in tables['name']:
            print(f"  - {table}")
        
        # Explorer chaque table
        for table_name in tables['name']:
            print(f"\n📋 Table '{table_name}':")
            
            # Schema de la table
            schema = pd.read_sql_query(f"PRAGMA table_info({table_name})", conn)
            print("  Colonnes :")
            for _, row in schema.iterrows():
                print(f"    - {row['name']} ({row['type']})")
            
            # Nombre de lignes
            count = pd.read_sql_query(f"SELECT COUNT(*) as count FROM {table_name}", conn)
            print(f"  Nombre de lignes : {count['count'].iloc[0]}")
            
            # Aperçu des données
            sample = pd.read_sql_query(f"SELECT * FROM {table_name} LIMIT 3", conn)
            print(f"  Aperçu :")
            print(sample.to_string(index=False, max_cols=5))
            
        conn.close()
        print("\n✅ Exploration terminée !")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    explore_database() 