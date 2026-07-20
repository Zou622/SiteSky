import os
import django
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'skyconnect.settings')
django.setup()

from django.core.files import File
from django.conf import settings
from core.models import QuickBlock, Slider, Logo, Forfait, ForfaitDescription

def import_quickblocks():
    print("📸 Importation des QuickBlocks...")
    data = [
        ('slide1_soVJpxD.jpg', 'Couverture régionale', 'Toute la Guinée', 'zone_couverture', 1),
        ('slide2.jpg', 'Notre histoire', 'Grands clients', 'qui_sommes_nous', 2),
        ('slide3.jpg', 'Support 24h/24', 'Contactez-nous', 'contact', 3),
        ('slide42.jpg', 'Nos services', 'Découvrez nos offres', 'forfaits', 4),
    ]
    
    for filename, title, desc, url, ordre in data:
        filepath = os.path.join(settings.MEDIA_ROOT, 'quickblocks', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                qb, _ = QuickBlock.objects.get_or_create(title=title)
                qb.image.save(filename, File(f), save=True)
                qb.url_name = url
                qb.description = desc
                qb.ordre = ordre
                qb.save()
                print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} manquant")

def import_sliders():
    print("\n📸 Importation des Sliders...")
    data = [
        ('slide1_soVJpxD.jpg', 'Bienvenue chez SKYCONNECT', 'Internet haut débit en Guinée', 1),
        ('slide2.jpg', 'Nos offres spéciales', 'Découvrez nos promotions', 2),
        ('slide3.jpg', 'Support 24h/24', 'Nous sommes à votre écoute', 3),
        ('slide42.jpg', 'Connectez-vous', 'Le meilleur de la fibre', 4),
    ]
    
    for filename, titre, desc, ordre in data:
        filepath = os.path.join(settings.MEDIA_ROOT, 'quickblocks', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                slider, _ = Slider.objects.get_or_create(titre=titre)
                slider.image.save(filename, File(f), save=True)
                slider.description = desc
                slider.ordre = ordre
                slider.is_active = True
                slider.save()
                print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} manquant")

def import_logos():
    print("\n📸 Importation des Logos...")
    for filename in ['New_logo.jpg', 'New_logo_Zv1m196.jpg']:
        filepath = os.path.join(settings.MEDIA_ROOT, 'logos', filename)
        if os.path.exists(filepath):
            with open(filepath, 'rb') as f:
                logo, _ = Logo.objects.get_or_create(alt=filename)
                logo.image.save(filename, File(f), save=True)
                logo.actif = True
                logo.save()
                print(f"  ✅ {filename}")
        else:
            print(f"  ❌ {filename} manquant")

def import_forfaits():
    print("\n📸 Importation des Forfaits...")
    forfaits = [
        {
            'nom': 'SKY BUSINESS',
            'prix': 649000,
            'type': 'FO',
            'is_bon_plan': True,
            'bg_color': '#2596be',
            'image': 'skyget_II.png',
            'descriptions': [
                'Pour les Entreprises et institutions',
                'Fibre Dédiée(FTTO): connexion sécurisée et garantie',
                'Réseau Radio: Solution rapide & performante',
                'Services Professionnels: VPN, VLAN, IP Fixe',
            ]
        },
        {
            'nom': 'SKY HOME',
            'prix': 549000,
            'type': 'FO',
            'is_bon_plan': True,
            'bg_color': '#cf0606',
            'image': '29_janv._2026_12_32_49.png',
            'descriptions': [
                'Pour les particuliers & PME',
                'Fibre partagée (FTTH/FTTB): haut débit abordable',
                'Solutions Adaptées: Forfaits flexibles',
                'Installation Rapide: Service technique réactif',
            ]
        },
    ]
    
    for data in forfaits:
        forfait, created = Forfait.objects.get_or_create(
            nom=data['nom'],
            defaults={
                'prix': data['prix'],
                'type': data['type'],
                'is_bon_plan': data['is_bon_plan'],
                'bg_color': data['bg_color'],
            }
        )
        
        # Image
        image_path = os.path.join(settings.MEDIA_ROOT, 'forfaits', data['image'])
        if os.path.exists(image_path):
            with open(image_path, 'rb') as f:
                forfait.image.save(data['image'], File(f), save=True)
            print(f"  ✅ Image importée pour {forfait.nom}")
        
        # Descriptions
        ForfaitDescription.objects.filter(forfait=forfait).delete()
        for i, texte in enumerate(data['descriptions']):
            ForfaitDescription.objects.create(
                forfait=forfait,
                texte=texte,
                ordre=i
            )
        
        print(f"  {'✅ Créé' if created else '✅ Mis à jour'}: {forfait.nom}")

if __name__ == '__main__':
    print("🚀 Importation des données...\n")
    import_quickblocks()
    import_sliders()
    import_logos()
    import_forfaits()
    
    print("\n📊 Statistiques:")
    print(f"  QuickBlocks: {QuickBlock.objects.count()}")
    print(f"  Sliders: {Slider.objects.count()}")
    print(f"  Logos: {Logo.objects.count()}")
    print(f"  Forfaits: {Forfait.objects.count()}")
    print("\n✅ Importation terminée !")
