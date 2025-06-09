import smtplib
import os
import pandas as pd
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
import openai
from dotenv import load_dotenv

# Charger le fichier de configuration
load_dotenv(".env")

# === Configuration sécurisée ===
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
GMAIL_EMAIL = os.getenv("GMAIL_EMAIL")
GMAIL_PASSWORD = os.getenv("GMAIL_PASSWORD")

# Vérifications de sécurité
if not OPENAI_API_KEY:
    raise Exception("❌ OPENAI_API_KEY manquant dans .env")
if not GMAIL_EMAIL:
    raise Exception("❌ GMAIL_EMAIL manquant dans .env")
if not GMAIL_PASSWORD:
    raise Exception("❌ GMAIL_PASSWORD manquant dans .env")

print(f"✅ Configuration chargée pour {GMAIL_EMAIL[:10]}***")

# === Fonctions ===

def ia_fill_template(template, row):
    """Personnalise un template avec les données d'une ligne CSV via IA"""
    variables_csv = "\n".join([f"- {col}: {row[col]}" for col in row.index])
    prompt = f"""
Tu es un assistant d'automatisation d'emails.
Voici les données de contact (une ligne du CSV) :
{variables_csv}

Voici le template email à remplir :
{template}

Instructions :
- Pour chaque variable entre {{}} dans le template, trouve la colonne CSV qui correspond le mieux (même si les noms ne correspondent pas parfaitement)
- Remplis chaque variable avec la valeur correspondante
- Si tu dois déduire un mapping (exemple : "prénom" = "FirstName", "société" = "Company"), fais-le de façon intelligente
- Retourne seulement le texte final sans commentaires ni balises.

Texte personnalisé :
"""
    client = openai.OpenAI(api_key=OPENAI_API_KEY)
    response = client.chat.completions.create(
        model="gpt-3.5-turbo",
        messages=[{"role": "user", "content": prompt}],
        max_tokens=600,
        temperature=0.2
    )
    return response.choices[0].message.content.strip()

def find_email_column(row):
    """Trouve automatiquement la colonne email dans une ligne"""
    for col in row.index:
        if 'mail' in col.lower():
            return row[col]
    # Fallback : cherche une valeur qui contient "@"
    for col in row.index:
        if "@" in str(row[col]):
            return row[col]
    raise Exception("Aucune colonne email détectée dans cette ligne")

def send_email_campaign(contacts_df, template_input, subject_template="Email personnalisé IA", sender_name="Assistant IA"):
    """
    Fonction principale pour envoyer une campagne
    
    Args:
        contacts_df: DataFrame pandas avec les contacts
        template_input: Template email à personnaliser
        subject_template: Template du sujet (peut contenir des variables)
        sender_name: Nom d'expéditeur affiché
    
    Returns:
        dict: Résultats de la campagne
    """
    
    print(f"📊 {len(contacts_df)} contacts à traiter")
    print("📋 Colonnes détectées :", contacts_df.columns.tolist())
    
    results = {
        'total': len(contacts_df),
        'success': 0,
        'errors': 0,
        'error_details': []
    }
    
    for idx, row in contacts_df.iterrows():
        try:
            # Personnalisation avec IA
            personalized_body = ia_fill_template(template_input, row)
            personalized_subject = ia_fill_template(subject_template, row)
            receiver_email = find_email_column(row)

            # === Envoi du mail ===
            msg = MIMEMultipart()
            msg['From'] = f"{sender_name} <{GMAIL_EMAIL}>"
            msg['To'] = receiver_email
            msg['Subject'] = personalized_subject
            msg.attach(MIMEText(personalized_body, 'plain'))

            server = smtplib.SMTP('smtp.gmail.com', 587)
            server.starttls()
            server.login(GMAIL_EMAIL, GMAIL_PASSWORD)
            server.sendmail(GMAIL_EMAIL, receiver_email, msg.as_string())
            server.quit()
            
            print(f"✅ Email envoyé à {receiver_email}")
            results['success'] += 1

        except Exception as e:
            error_msg = f"Erreur pour {receiver_email if 'receiver_email' in locals() else 'contact'}: {e}"
            print(f"❌ {error_msg}")
            results['errors'] += 1
            results['error_details'].append(error_msg)

    print(f"\n🎉 Campagne terminée : {results['success']} succès, {results['errors']} erreurs")
    return results

def preview_personalization(contacts_df, template_input, subject_template="Email personnalisé IA", sender_name="Assistant IA", num_previews=1):
    """
    Génère un aperçu de personnalisation sans envoyer d'emails
    
    Args:
        contacts_df: DataFrame pandas avec les contacts
        template_input: Template email à personnaliser
        subject_template: Template du sujet
        sender_name: Nom d'expéditeur affiché
        num_previews: Nombre d'aperçus à générer
    
    Returns:
        list: Liste des aperçus générés
    """
    previews = []
    
    for idx in range(min(num_previews, len(contacts_df))):
        row = contacts_df.iloc[idx]
        try:
            receiver_email = find_email_column(row)
            personalized_body = ia_fill_template(template_input, row)
            personalized_subject = ia_fill_template(subject_template, row)
            
            previews.append({
                'email': receiver_email,
                'subject': personalized_subject,
                'personalized_content': personalized_body,
                'sender': f"{sender_name} <{GMAIL_EMAIL}>",
                'contact_data': row.to_dict()
            })
            
        except Exception as e:
            previews.append({
                'email': 'Erreur',
                'error': str(e),
                'contact_data': row.to_dict()
            })
    
    return previews

# === Main routine (pour test direct) ===
if __name__ == "__main__":
    print("📧 Test du module de campagne email")
    
    # Demander le fichier CSV
    csv_file = input("📁 Chemin vers le fichier CSV (ou 'test' pour créer un exemple): ").strip()
    
    # Nettoyer les guillemets si présents
    csv_file = csv_file.strip('"').strip("'")
    
    if csv_file.lower() == 'test':
        # Créer un DataFrame de test
        test_data = {
            'nom': ['Jean Dupont', 'Marie Martin'],
            'email': ['jean@test.com', 'marie@test.com'],
            'profession': ['développeur', 'designer']
        }
        contacts = pd.DataFrame(test_data)
        print("📊 Données de test créées:")
    else:
        # Charger le fichier CSV
        try:
            contacts = pd.read_csv(csv_file)
            print(f"📊 {len(contacts)} contacts chargés depuis {csv_file}")
        except FileNotFoundError:
            print(f"❌ Fichier {csv_file} introuvable")
            exit(1)
        except Exception as e:
            print(f"❌ Erreur lors du chargement : {e}")
            exit(1)
    
    print("📋 Colonnes détectées :", contacts.columns.tolist())
    print("👀 Aperçu des données :")
    print(contacts.head(3))
    
    # Demander les infos d'envoi
    sender_name = input("\n👤 Nom d'expéditeur affiché (ex: Jean Dupont): ").strip() or "Assistant IA"
    subject_template = input("📋 Sujet de l'email (peut contenir des variables comme {nom}): ").strip() or "Email personnalisé pour {nom}"
    template_input = input("\n📝 Colle ici le template d'email à personnaliser :\n")
    
    # Test de prévisualisation
    print("\n🔍 Test de prévisualisation...")
    previews = preview_personalization(contacts, template_input, subject_template, sender_name, 1)
    if previews:
        preview = previews[0]
        if 'error' not in preview:
            print(f"📧 De: {preview['sender']}")
            print(f"📧 À: {preview['email']}")
            print(f"📋 Sujet: {preview['subject']}")
            print(f"📝 Contenu:\n{preview['personalized_content']}")
        else:
            print(f"❌ Erreur: {preview['error']}")
    
    # Confirmation pour envoi réel
    confirm = input(f"\n⚠️  Envoyer {len(contacts)} emails RÉELS ? (oui/non): ")
    if confirm.lower() in ['oui', 'o', 'yes', 'y']:
        results = send_email_campaign(contacts, template_input, subject_template, sender_name)
        print(f"\n📊 Résultats: {results['success']} succès, {results['errors']} erreurs")
    else:
        print("❌ Envoi annulé - seule la prévisualisation a été effectuée")

