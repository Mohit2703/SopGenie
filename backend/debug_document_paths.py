#!/usr/bin/env python
import os
import django
from django.conf import settings

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'sop_rag.settings')
django.setup()

from rag_app.models import Document, Module

def debug_documents():
    print("🔍 DEBUGGING DOCUMENT PATHS")
    print("=" * 50)
    
    print(f"📂 MEDIA_ROOT: {settings.MEDIA_ROOT}")
    print(f"🌐 MEDIA_URL: {settings.MEDIA_URL}")
    print(f"🏠 Current Working Directory: {os.getcwd()}")
    print()
    
    # Get all documents
    documents = Document.objects.filter(active=True)
    print(f"📄 Found {documents.count()} active documents")
    
    for i, doc in enumerate(documents, 1):
        print(f"\n📄 Document {i}:")
        print(f"  ID: {doc.id}")
        print(f"  Title: {doc.title}")
        print(f"  File: {doc.file}")
        print(f"  File Name: {doc.file.name}")
        print(f"  File Path: {doc.file.path}")
        print(f"  File URL: {doc.file.url}")
        print(f"  File Exists: {os.path.exists(doc.file.path)}")
        
        if not os.path.exists(doc.file.path):
            print(f"  ❌ FILE NOT FOUND!")
            # Check directory
            dir_path = os.path.dirname(doc.file.path)
            print(f"  Directory: {dir_path}")
            print(f"  Directory Exists: {os.path.exists(dir_path)}")
            
            if os.path.exists(dir_path):
                files_in_dir = os.listdir(dir_path)
                print(f"  Files in directory: {files_in_dir}")
        else:
            file_size = os.path.getsize(doc.file.path)
            print(f"  ✅ File Size: {file_size} bytes")

if __name__ == "__main__":
    debug_documents()
