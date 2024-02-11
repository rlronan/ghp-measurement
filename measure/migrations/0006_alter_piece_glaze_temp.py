# Generated by Django 4.1.3 on 2024-02-11 20:01

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measure", "0005_ledger_stripe_session_id"),
    ]

    operations = [
        migrations.AlterField(
            model_name="piece",
            name="glaze_temp",
            field=models.CharField(
                choices=[
                    ("10", "Δ 10 (Cone 10)"),
                    ("6", "Δ 6 (Cone 6)"),
                    ("Lust", "Luster"),
                    ("04", "Δ 04 (Cone 04)"),
                    ("None", "None"),
                ],
                default="10",
                max_length=4,
            ),
        ),
    ]
