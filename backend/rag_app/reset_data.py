import django
import sys
import os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')
django.setup()
from django.core.management.base import BaseCommand
from django.db import transaction
from rag_app.models import Project, Module, Document
from vectordb.models import VectorDBTask, ModuleVectorStore, QueryLog
import shutil
import os
from django.conf import settings

class Command(BaseCommand):
    help = 'Reset all data except users'
    
    def add_arguments(self, parser):
        parser.add_argument(
            '--confirm',
            action='store_true',
            help='Confirm deletion without prompt',
        )
    
    def handle(self, *args, **options):
        if not options['confirm']:
            confirm = input(
                '⚠️  WARNING: This will delete ALL projects, modules, documents, '
                'vector stores, and tasks.\n'
                'Users will be preserved.\n'
                'Type "yes" to continue: '
            )
            if confirm.lower() != 'yes':
                self.stdout.write(self.style.ERROR('❌ Operation cancelled'))
                return
        
        self.stdout.write('🗑️  Starting data cleanup...\n')
        
        try:
            with transaction.atomic():
                # Delete in correct order (respecting foreign keys)
                
                # 1. Delete QueryLogs
                query_logs_count = QueryLog.objects.count()
                QueryLog.objects.all().delete()
                self.stdout.write(f'✓ Deleted {query_logs_count} query logs')
                
                # 2. Delete VectorDBTasks
                tasks_count = VectorDBTask.objects.count()
                VectorDBTask.objects.all().delete()
                self.stdout.write(f'✓ Deleted {tasks_count} vector DB tasks')
                
                # 3. Delete ModuleVectorStores
                vector_stores_count = ModuleVectorStore.objects.count()
                ModuleVectorStore.objects.all().delete()
                self.stdout.write(f'✓ Deleted {vector_stores_count} vector stores')
                
                # 4. Delete Documents
                documents_count = Document.objects.count()
                Document.objects.all().delete()
                self.stdout.write(f'✓ Deleted {documents_count} documents')
                
                # 5. Delete Modules
                modules_count = Module.objects.count()
                Module.objects.all().delete()
                self.stdout.write(f'✓ Deleted {modules_count} modules')
                
                # 6. Delete Projects
                projects_count = Project.objects.count()
                Project.objects.all().delete()
                self.stdout.write(f'✓ Deleted {projects_count} projects')
            
            # Clean up media files (optional)
            self.stdout.write('\n🗂️  Cleaning media files...')
            media_root = settings.MEDIA_ROOT
            
            # Clean documents folder
            documents_path = os.path.join(media_root, 'documents')
            if os.path.exists(documents_path):
                shutil.rmtree(documents_path)
                self.stdout.write(f'✓ Removed documents folder: {documents_path}')
            
            # Clean vector stores folder
            vector_stores_path = os.path.join(media_root, 'vector_stores')
            if os.path.exists(vector_stores_path):
                shutil.rmtree(vector_stores_path)
                self.stdout.write(f'✓ Removed vector stores folder: {vector_stores_path}')
            
            self.stdout.write(self.style.SUCCESS('\n✅ Data cleanup completed successfully!'))
            self.stdout.write('Users have been preserved.')
            
        except Exception as e:
            self.stdout.write(self.style.ERROR(f'\n❌ Error during cleanup: {str(e)}'))
            raise
