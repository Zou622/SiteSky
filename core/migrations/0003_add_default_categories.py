from django.db import migrations


def create_default_categories(apps, schema_editor):
    Categorie = apps.get_model('core', 'Categorie')
    Categorie.objects.get_or_create(nom='Equipement', defaults={'description': ''})
    Categorie.objects.get_or_create(nom='Accessoire', defaults={'description': ''})


def delete_default_categories(apps, schema_editor):
    Categorie = apps.get_model('core', 'Categorie')
    Categorie.objects.filter(nom__in=['Equipement', 'Accessoire']).delete()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0002_add_default_forfaits'),
    ]

    operations = [
        migrations.RunPython(create_default_categories, delete_default_categories),
    ]
