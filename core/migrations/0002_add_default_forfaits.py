from django.db import migrations


def create_default_forfaits(apps, schema_editor):
    Forfait = apps.get_model('core', 'Forfait')
    ForfaitDescription = apps.get_model('core', 'ForfaitDescription')

    # SKY BUSINESS
    sb, created = Forfait.objects.get_or_create(
        nom='SKY BUSINESS',
        defaults={
            'description1': 'Pour les Entreprises et institutions',
            'description2': 'Fibre Dédiée(FTTO):connexion sécurisée et garantie',
            'description3': 'Réseau Radio: Solution rapide & performante',
            'description4': 'Services Professionnels: VPN,VLAN,IP Fixe',
            'prix': 649000,
            'icone': 'bi bi-briefcase-fill',
            'type': 'FO',
            'is_bon_plan': True,
            'bg_color': '#2596be',
        }
    )
    if created:
        ForfaitDescription.objects.get_or_create(forfait=sb, ordre=1, defaults={'texte': sb.description1})
        ForfaitDescription.objects.get_or_create(forfait=sb, ordre=2, defaults={'texte': sb.description2})
        ForfaitDescription.objects.get_or_create(forfait=sb, ordre=3, defaults={'texte': sb.description3})
        ForfaitDescription.objects.get_or_create(forfait=sb, ordre=4, defaults={'texte': sb.description4})

    # SKY HOME
    sh, created = Forfait.objects.get_or_create(
        nom='SKY HOME',
        defaults={
            'description1': 'Pour les particuliers & PME',
            'description2': 'Fibre partagée (FTTH/FTTB):haut debit abordable',
            'description3': 'Solutions Adaptées:Forfaits flexibles',
            'description4': 'Installation Rapide:Service technique réactif',
            'prix': 549000,
            'icone': 'bi bi-house-fill',
            'type': 'FO',
            'is_bon_plan': True,
            'bg_color': '#2596be',
        }
    )
    if created:
        ForfaitDescription.objects.get_or_create(forfait=sh, ordre=1, defaults={'texte': sh.description1})
        ForfaitDescription.objects.get_or_create(forfait=sh, ordre=2, defaults={'texte': sh.description2})
        ForfaitDescription.objects.get_or_create(forfait=sh, ordre=3, defaults={'texte': sh.description3})
        ForfaitDescription.objects.get_or_create(forfait=sh, ordre=4, defaults={'texte': sh.description4})


def delete_default_forfaits(apps, schema_editor):
    Forfait = apps.get_model('core', 'Forfait')
    Forfait.objects.filter(nom__in=['SKY BUSINESS', 'SKY HOME']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0001_initial'),
    ]

    operations = [
        migrations.RunPython(create_default_forfaits, delete_default_forfaits),
    ]
