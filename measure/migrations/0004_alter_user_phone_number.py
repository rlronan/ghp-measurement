# Generated by Django 4.1.3 on 2023-03-28 18:27

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("measure", "0003_alter_courseinstance_course_and_more"),
    ]

    operations = [
        migrations.AlterField(
            model_name="user",
            name="phone_number",
            field=models.CharField(blank=True, default="", max_length=12, unique=True),
        ),
    ]
