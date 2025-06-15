import sqlite3
import pandas as pd
import matplotlib.pyplot as plt

def debug_viz_issue():
    """Diagnostique le problème avec la visualisation des secteurs d'activité"""
    
    print("🔍 Diagnostic du problème de visualisation")
    print("=" * 50)
    
    try:
        conn = sqlite3.connect('bdd_clients.db')
        
        # 1. Vérifier les données brutes
        print("📊 Données brutes dans 'Secteur d'activité' :")
        raw_data = pd.read_sql_query(
            "SELECT \"Secteur d'activité\", COUNT(*) as count FROM contacts GROUP BY \"Secteur d'activité\" ORDER BY count DESC",
            conn
        )
        print(raw_data.to_string(index=False))
        
        # 2. Vérifier les valeurs NULL
        null_count = pd.read_sql_query(
            "SELECT COUNT(*) as count FROM contacts WHERE \"Secteur d'activité\" IS NULL",
            conn
        )
        print(f"\n❌ Contacts avec secteur NULL : {null_count['count'].iloc[0]}")
        
        # 3. Tester la requête qui devrait fonctionner
        print("\n🧪 Test de la requête corrigée :")
        query = """
        SELECT 
            COALESCE("Secteur d'activité", 'Non spécifié') as "Secteur d'activité",
            COUNT(*) as "Nombre_de_contacts"
        FROM contacts 
        GROUP BY "Secteur d'activité" 
        ORDER BY "Nombre_de_contacts" DESC 
        LIMIT 5
        """
        
        df = pd.read_sql_query(query, conn)
        print("✅ Données nettoyées :")
        print(df.to_string(index=False))
        
        # 4. Tester la visualisation
        print("\n🎨 Test de la visualisation :")
        if len(df) > 0:
            # Nettoyer les données pour la visualisation
            df_clean = df.copy()
            df_clean = df_clean.fillna('Non spécifié')  # Remplacer les NaN restants
            
            # Créer le graphique
            colors = ['#ff1744', '#e91e63', '#9c27b0', '#673ab7', '#3f51b5']
            
            plt.figure(figsize=(12, 6))
            bars = plt.bar(df_clean['Secteur d\'activité'], df_clean['Nombre_de_contacts'], color=colors[:len(df_clean)])
            
            plt.xlabel('Secteur d\'activité', fontsize=12)
            plt.ylabel('Nombre de contacts', fontsize=12)
            plt.title('Répartition des contacts par secteur d\'activité (Top 5)', fontsize=14, fontweight='bold')
            
            # Ajouter les valeurs sur les barres
            for bar in bars:
                height = bar.get_height()
                plt.text(bar.get_x() + bar.get_width()/2., height + 0.1,
                        f'{int(height)}', ha='center', va='bottom', fontweight='bold')
            
            plt.xticks(rotation=45, ha='right')
            plt.tight_layout()
            
            # Sauvegarder pour vérifier
            plt.savefig('test_viz_debug.png', dpi=150, bbox_inches='tight')
            plt.close()
            
            print("✅ Graphique généré et sauvé dans 'test_viz_debug.png'")
        else:
            print("❌ Aucune donnée à visualiser")
        
        conn.close()
        
    except Exception as e:
        print(f"❌ Erreur : {e}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    debug_viz_issue() 