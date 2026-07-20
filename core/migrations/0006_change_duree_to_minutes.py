# Migration to change duree_heures to duree_minutes

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0005_add_default_agence'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='wifitickettype',
            options={'ordering': ['ordre', 'duree_minutes'], 'verbose_name': 'Type de ticket WiFi', 'verbose_name_plural': 'Types de tickets WiFi'},
        ),
        migrations.RemoveField(
            model_name='wifitickettype',
            name='duree_heures',
        ),
        migrations.AddField(
            model_name='wifitickettype',
            name='duree_minutes',
            field=models.PositiveIntegerField(default=60, help_text='Durée en minutes'),
        ),
        migrations.AlterField(
            model_name='wifitickettype',
            name='nom',
            field=models.CharField(help_text='Ex: 5 minutes, 30 minutes, 1 heure, 2 heures, 1 jour', max_length=100),
        ),
    ]
