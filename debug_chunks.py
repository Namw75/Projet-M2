import chromadb
from collections import Counter

def analyze_chromadb():
    """Analyse détaillée de ChromaDB"""
    print("🔍 Analyse de ChromaDB")
    print("=" * 50)
    
    # Connexion
    try:
        client = chromadb.PersistentClient(path="./chroma_db")
        collection = client.get_collection(name="documents")
        
        # Compter les documents
        total_count = collection.count()
        print(f"📄 Total documents : {total_count}")
        
        # Récupérer tous les documents avec métadonnées
        all_docs = collection.get(include=['documents', 'metadatas'])
        
        if all_docs['metadatas']:
            # Analyser par fichier
            filenames = [meta.get('filename', 'Unknown') for meta in all_docs['metadatas']]
            file_counts = Counter(filenames)
            
            print(f"\n📂 Répartition par fichier :")
            for filename, count in file_counts.items():
                print(f"  - {filename}: {count} chunks")
            
            # Montrer quelques exemples de chunks
            print(f"\n📝 Exemples de chunks :")
            for i, (doc, meta) in enumerate(zip(all_docs['documents'][:5], all_docs['metadatas'][:5])):
                filename = meta.get('filename', 'Unknown')
                chunk_idx = meta.get('chunk_index', '?')
                print(f"\n  📄 {filename} - Chunk {chunk_idx}:")
                print(f"     {doc[:150]}...")
        
        print(f"\n✅ Analyse terminée !")
        
    except Exception as e:
        print(f"❌ Erreur : {e}")

if __name__ == "__main__":
    analyze_chromadb() 