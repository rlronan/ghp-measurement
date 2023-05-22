# Generated by Django 4.1.7 on 2023-05-08 02:28

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("measure", "0001_initial"),
    ]

    operations = [
        migrations.AddField(
            model_name="piece",
            name="firing_price",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
        migrations.AddField(
            model_name="piece",
            name="glazing_price",
            field=models.DecimalField(decimal_places=2, default=0.0, max_digits=10),
        ),
    ]