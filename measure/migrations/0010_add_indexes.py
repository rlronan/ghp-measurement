# measure/migrations/0010_add_indexes.py
# Generated manually for performance optimization

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('measure', '0009_alter_piece_bisque_temp_and_more'), 
    ]

    operations = [
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_piece_location ON piece_receipt(piece_location);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_piece_location;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_piece_id ON piece_receipt(piece_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_piece_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_printed ON piece_receipt(printed);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_printed;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_piece_date ON piece_receipt(piece_date);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_piece_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_receipt_type ON piece_receipt(receipt_type);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_receipt_type;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_bisque_temp ON piece_receipt(bisque_temp);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_bisque_temp;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piecereceipt_glaze_temp ON piece_receipt(glaze_temp);",
            reverse_sql="DROP INDEX IF EXISTS idx_piecereceipt_glaze_temp;"
        ),
    ]