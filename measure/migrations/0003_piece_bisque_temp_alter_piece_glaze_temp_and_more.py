# Generated by Django 4.1.3 on 2023-05-15 20:05

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measure", "0002_piece_firing_price_piece_glazing_price"),
    ]

    operations = [
        migrations.AddField(
            model_name="piece",
            name="bisque_temp",
            field=models.CharField(
                choices=[("06B", "Δ 06 BISQUE (Cone 06 Bisque)"), ("None", "None")],
                default="06B",
                max_length=4,
            ),
        ),
        migrations.AlterField(
            model_name="piece",
            name="glaze_temp",
            field=models.CharField(
                choices=[
                    ("10", "Δ 10 (Cone 10)"),
                    ("6", "Δ 6 (Cone 6)"),
                    ("2", "Δ 2 (Cone 2)"),
                    ("014", "Δ 014 (Cone 014)"),
                    ("06G", "Δ 06 (Cone 06)"),
                    ("04", "Δ 04 (Cone 04)"),
                    ("None", "None"),
                ],
                default="10",
                max_length=4,
            ),
        ),
        migrations.AddConstraint(
            model_name="piece",
            constraint=models.CheckConstraint(
                check=models.Q(
                    ("length__lte", 21.0), ("width__lte", 21.0), _connector="OR"
                ),
                name="length_or_width_lte_21.0",
                violation_error_message="Length or width must be less than or equal to 21 inches",
            ),
        ),
    ]
