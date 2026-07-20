from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0006_change_duree_to_minutes'),
    ]

    operations = [
        migrations.AddField(
            model_name='wifiticket',
            name='date_premiere_connexion',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='wifiticket',
            name='date_expiration',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
