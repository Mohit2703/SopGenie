import os
import django
import shutil
import sqlite3

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')
django.setup()

from django.conf import settings
from django.db import connection

print("⚠️  WARNING: This will COMPLETELY RESET the database except users!")
print("This will:")
print("  1. Drop all non-user tables")
print("  2. Delete all migrations")
print("  3. Recreate migrations")
print("  4. Run migrations")
print("  5. Clean media files")
confirm = input("\nType 'RESET' to confirm: ")

if confirm != 'RESET':
    print("❌ Cancelled")
    exit()

print("\n🗑️  Starting complete reset...\n")

# Step 1: Get database path
db_path = settings.DATABASES['default']['NAME']
print(f"Database: {db_path}")

# Step 2: Drop specific tables using raw SQL
print("\n📋 Dropping tables...")
with connection.cursor() as cursor:
    # Get list of tables
    cursor.execute("SELECT name FROM sqlite_master WHERE type='table';")
    tables = cursor.fetchall()
    
    # Drop tables except user-related ones
    tables_to_drop = [
        'vectordb_query_log',
        'vectordb_task',
        'vectordb_module_store',
        'rag_app_document',
        'rag_app_module',
        'rag_app_project_users',
        'rag_app_project',
    ]
    
    for table in tables_to_drop:
        try:
            cursor.execute(f"DROP TABLE IF EXISTS {table};")
            print(f"  ✓ Dropped {table}")
        except Exception as e:
            print(f"  ⚠️  Could not drop {table}: {e}")

print("\n📁 Cleaning migration files...")
# Step 3: Remove migration files
import glob
migration_patterns = [
    './rag_app/migrations/[0-9]*.py',
    './vectordb/migrations/[0-9]*.py',
]

for pattern in migration_patterns:
    files = glob.glob(pattern)
    for file in files:
        os.remove(file)
        print(f"  ✓ Removed {file}")

# Step 4: Clean media files
print("\n🗂️  Cleaning media files...")
media_root = settings.MEDIA_ROOT

documents_path = os.path.join(media_root, 'documents')
if os.path.exists(documents_path):
    shutil.rmtree(documents_path)
    print(f"  ✓ Removed: {documents_path}")

vector_stores_path = os.path.join(media_root, 'vector_stores')
if os.path.exists(vector_stores_path):
    shutil.rmtree(vector_stores_path)
    print(f"  ✓ Removed: {vector_stores_path}")

print("\n✅ Database reset complete!")
print("\nNext steps:")
print("  1. Run: python manage.py makemigrations")
print("  2. Run: python manage.py migrate")
print("  3. Verify users: python manage.py shell -c \"from rag_app.models import User; print(f'Users: {User.objects.count()}')\"")
