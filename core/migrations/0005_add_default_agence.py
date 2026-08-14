from django.db import migrations


def create_default_agence(apps, schema_editor):
    Agence = apps.get_model('core', 'Agence')
    Agence.objects.get_or_create(
        nom='Kipé',
        defaults={
            'adresse': 'Kipé Carrefour Metal Guinée',
            'telephone': '+224622900400',
            'email': 'contact@skyconnect-sa.com',
        }
    )


def delete_default_agence(apps, schema_editor):
    Agence = apps.get_model('core', 'Agence')
    Agence.objects.filter(nom='Kipé').delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0004_add_zones_communes'),
    ]

    operations = [
        migrations.RunPython(create_default_agence, delete_default_agence),
    ]
