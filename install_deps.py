#!/usr/bin/env python3
"""
Script pour installer les dépendances optionnelles pour le traitement de documents
"""

import subprocess
import sys

def install_package(package):
    """Installe un package pip"""
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])
        print(f"✅ {package} installé avec succès")
        return True
    except subprocess.CalledProcessError:
        print(f"❌ Échec de l'installation de {package}")
        return False

def main():
    print("🔧 Installation des dépendances optionnelles pour AI Viz")
    print("=" * 60)
    
    packages = {
        "PyPDF2": "Lecture des fichiers PDF",
        "python-docx": "Lecture des fichiers Word",
        "streamlit": "Interface web",
        "seaborn": "Visualisations avancées"
    }
    
    success_count = 0
    
    for package, description in packages.items():
        print(f"\n📦 Installation de {package} ({description})...")
        if install_package(package):
            success_count += 1
    
    print(f"\n🎉 Installation terminée : {success_count}/{len(packages)} packages installés")
    
    if success_count == len(packages):
        print("✅ Toutes les dépendances sont installées !")
        print("\n🚀 Vous pouvez maintenant lancer :")
        print("   python -m streamlit run core/ai_viz.py")
    else:
        print("⚠️ Certaines dépendances n'ont pas pu être installées")

if __name__ == "__main__":
    main() 