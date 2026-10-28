# Adds a unique constraint on Ledger.stripe_session_id so duplicate Stripe
# webhook deliveries for the same checkout session can't double-credit an
# account (the duplicate insert fails with IntegrityError instead).
#
# NOTE: if production already contains duplicate non-NULL stripe_session_id
# values (e.g. from the double-credit bug this fixes), this migration's CREATE
# UNIQUE INDEX will fail. Deduplicate those rows before applying.

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ('measure', '0011_add_piece_ledger_indexes'),
    ]

    operations = [
        migrations.AlterField(
            model_name='ledger',
            name='stripe_session_id',
            field=models.CharField(blank=True, max_length=100, null=True, unique=True),
        ),
    ]
