# measure/migrations/0011_add_piece_ledger_indexes.py
# Generated manually for additional performance optimization

from django.db import migrations

class Migration(migrations.Migration):
    dependencies = [
        ('measure', '0010_add_indexes'), 
    ]

    operations = [
        # Piece table indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_ghp_user_id ON piece(ghp_user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_ghp_user_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_date ON piece(date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_bisque_temp ON piece(bisque_temp);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_bisque_temp;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_glaze_temp ON piece(glaze_temp);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_glaze_temp;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_piece_location ON piece(piece_location);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_piece_location;"
        ),
        
        # Ledger table indexes
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ledger_ghp_user_id ON ledger(ghp_user_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ledger_ghp_user_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ledger_piece_id ON ledger(piece_id);",
            reverse_sql="DROP INDEX IF EXISTS idx_ledger_piece_id;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ledger_date ON ledger(date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_ledger_date;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ledger_transaction_type ON ledger(transaction_type);",
            reverse_sql="DROP INDEX IF EXISTS idx_ledger_transaction_type;"
        ),
        
        # GHPUser table indexes for common filters
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ghpuser_current_student ON ghp_user(current_student);",
            reverse_sql="DROP INDEX IF EXISTS idx_ghpuser_current_student;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ghpuser_current_ghp_staff ON ghp_user(current_ghp_staff);",
            reverse_sql="DROP INDEX IF EXISTS idx_ghpuser_current_ghp_staff;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ghpuser_current_faculty ON ghp_user(current_faculty);",
            reverse_sql="DROP INDEX IF EXISTS idx_ghpuser_current_faculty;"
        ),
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ghpuser_current_location ON ghp_user(current_location);",
            reverse_sql="DROP INDEX IF EXISTS idx_ghpuser_current_location;"
        ),
        
        # Composite index for common Piece queries (user + date)
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_piece_user_date ON piece(ghp_user_id, date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_piece_user_date;"
        ),
        
        # Composite index for common Ledger queries (user + date)
        migrations.RunSQL(
            "CREATE INDEX IF NOT EXISTS idx_ledger_user_date ON ledger(ghp_user_id, date DESC);",
            reverse_sql="DROP INDEX IF EXISTS idx_ledger_user_date;"
        ),
    ]

