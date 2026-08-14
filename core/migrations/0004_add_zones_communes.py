from django.db import migrations


def create_zones_and_communes(apps, schema_editor):
    Zone = apps.get_model('core', 'ZoneCouverture')
    Commune = apps.get_model('core', 'Commune')

    data = {
        'Conakry': ['Kaloum', 'Dixinn', 'Matam', 'Ratoma', 'Matoto'],
        'Boké': ['Boké', 'Boffa', 'Fria', 'Gaoual', 'Koundara'],
        'Kindia': ['Kindia', 'Coyah', 'Dubréka', 'Forécariah', 'Télimélé'],
        'Labé': ['Labé', 'Koubia', 'Lélouma', 'Mali', 'Tougué'],
        'Mamou': ['Mamou', 'Dalaba', 'Pita'],
        'Faranah': ['Faranah', 'Dabola', 'Dinguiraye', 'Kissidougou'],
        'Kankan': ['Kankan', 'Kérouané', 'Kouroussa', 'Mandiana', 'Siguiri'],
        "N'Zérékoré": ["N'Zérékoré", 'Beyla', "Guéckédou", 'Lola', 'Macenta', 'Yomou'],
    }

    for region, communes in data.items():
        zone_obj, created = Zone.objects.get_or_create(region=region, defaults={'description': ''})
        for idx, commune_name in enumerate(communes, start=1):
            Commune.objects.get_or_create(nom=commune_name, zone=zone_obj, defaults={'description': ''})


def delete_zones_and_communes(apps, schema_editor):
    Zone = apps.get_model('core', 'ZoneCouverture')
    regions = ['Conakry', 'Boké', 'Kindia', 'Labé', 'Mamou', 'Faranah', 'Kankan', "N'Zérékoré"]
    Zone.objects.filter(region__in=regions).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_add_default_categories'),
    ]

    operations = [
        migrations.RunPython(create_zones_and_communes, delete_zones_and_communes),
    ]
