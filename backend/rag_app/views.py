## django imports
from django.conf import settings
from django.http import FileResponse, Http404
from django.shortcuts import get_object_or_404
from django.db.models import Q

## other imports
import os
import mimetypes
import uuid
from http import HTTPStatus

## rest framework imports
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

## app model imports
from vectordb.models import ModuleVectorStore
from .models import User, Project, Module, Document, ProjectMember

## app serializer imports
from .serializers import UserSerializer, ProjectSerializer, ModuleSerializer, DocumentSerializer, ProjectMemberSerializer

class UserView(APIView):
    ## Allow any user (authenticated or not) to access this view
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.CREATED)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)

    def get(self, request, user_id=None):
        if user_id:
            user = get_object_or_404(User, id=user_id)
            serializer = UserSerializer(user)
            return Response(serializer.data)
        users = User.objects.all()
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data)
  
    def put(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        serializer = UserSerializer(user, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)

    def delete(self, request, user_id):
        user = get_object_or_404(User, id=user_id)
        user.delete()
        return Response(status=HTTPStatus.NO_CONTENT)


class UserInfoView(APIView):
    permission_classes = [AllowAny]
    def get(self, request):
        user = request.user
        serializer = UserSerializer(user)
        return Response(serializer.data)


class CreateUserView(APIView):
    def post(self, request):
        serializer = UserSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.CREATED)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)


class ProjectView(APIView):
    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        members = request.data.get('users', [])  # list of user ids
        if serializer.is_valid():
            print('user: ', request.user)
            project = serializer.save(admin=request.user)  # save without users
            print(project)
            if members:
                project.users.set(User.objects.filter(id__in=members) | User.objects.filter(id=request.user.id))
            return Response(ProjectSerializer(project).data, status=HTTPStatus.CREATED)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    
    def get(self, request):
        # Fetch all projects where user is either admin or a member
        projects = Project.objects.filter(users=request.user) | Project.objects.filter(admin=request.user)
        projects = projects.distinct()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)
    
    def get(self, request, project_id=None):
        if project_id:  # fetch single project
            project = get_object_or_404(
                Project.objects.prefetch_related("users").select_related("admin"),
                id=project_id
            )
            serializer = ProjectSerializer(project)
            return Response(serializer.data, status=HTTPStatus.OK)

        # fallback → fetch all projects for logged-in user
        projects = Project.objects.filter(users=request.user) | Project.objects.filter(admin=request.user)
        projects = projects.distinct()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)

    def put(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        data = request.data.copy()

        # Extract user IDs and admin separately
        members = data.pop("users", [])
        admin_id = data.pop("admin", None)

        serializer = ProjectSerializer(project, data=data, partial=True)
        if serializer.is_valid():
            updated_project = serializer.save()

            # ✅ Update users (if provided)
            if members is not None or members == []:
                updated_project.users.set(User.objects.filter(id__in=members))

            # ✅ Update admin (if provided)
            if admin_id:
                try:
                    new_admin = User.objects.get(id=admin_id)
                    updated_project.admin = new_admin
                    updated_project.save()
                except User.DoesNotExist:
                    return Response({"error": "Admin user not found"}, status=HTTPStatus.BAD_REQUEST)

            return Response(ProjectSerializer(updated_project).data, status=HTTPStatus.OK)

        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)

    def delete(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)

        # ✅ Only allow admin (or staff) to delete
        if project.admin != request.user and not request.user.is_staff:
            return Response(
                {"error": "You do not have permission to delete this project."},
                status=HTTPStatus.FORBIDDEN,
            )

        project.delete()
        return Response(status=HTTPStatus.NO_CONTENT)


class SearchUserView(APIView):
    def get(self, request):
        query = request.GET.get('q', '')  # Use request.GET instead of request.query_params
        
        if len(query) < 2:
            return Response({'users': []}, status=HTTPStatus.OK)
        
        users = User.objects.filter(
            Q(username__icontains=query) |
            Q(email__icontains=query) |
            Q(name__icontains=query)
        ).exclude(id=request.user.id)[:10]
        serializer = UserSerializer(users, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)


class ProjectMemberView(APIView):
    def get(self, request, project_id):
        user = request.user
        user_role = ProjectMember.objects.filter(project_id=project_id, user=user).first()
        if not user_role:
            return Response({"error": "You are not a member of this project."}, status=HTTPStatus.FORBIDDEN)
        project_members = ProjectMember.objects.filter(project_id=project_id)
        serializer = ProjectMemberSerializer(project_members, many=True)
        data = {
            "user_role": user_role.role,
            "members": serializer.data
        }
        return Response(data, status=HTTPStatus.OK)

    def post(self, request, project_id):
        data = request.data
        user_id = data.get("user_id")
        role = data.get("role", "viewer")
        user = request.user
        
        user_role = ProjectMember.objects.filter(project_id=project_id, user=user).first()

        if not user_role or user_role.role not in ('admin', 'owner'):
            return Response({"error": "Only admins can add members."}, status=HTTPStatus.FORBIDDEN)

        project = get_object_or_404(Project, id=project_id)
        user = get_object_or_404(User, id=user_id)

        ProjectMember.objects.create(
            project=project,
            user=user,
            role=role
        )
        return Response({"detail": "User added to project"}, status=HTTPStatus.OK)
    
    def delete(self, request, project_id, user_id):
        user = request.user
        user_role = ProjectMember.objects.filter(project_id=project_id, user=user).first()
        if not user_role or user_role.role not in ('admin', 'owner'):
            return Response({"error": "Only admins can remove members."}, status=HTTPStatus.FORBIDDEN)
        
        membership = get_object_or_404(ProjectMember, project_id=project_id, user_id=user_id)
        membership.delete()
        return Response({"detail": "User removed from project"}, status=HTTPStatus.NO_CONTENT)

    def put(self, request, project_id, user_id):
        user = request.user
        user_role = ProjectMember.objects.filter(project_id=project_id, user=user).first()
        if not user_role or user_role.role not in ('admin', 'owner'):
            return Response({"error": "Only admins can update member roles."}, status=HTTPStatus.FORBIDDEN)
        
        membership = get_object_or_404(ProjectMember, project_id=project_id, user_id=user_id)
        new_role = request.data.get("role")
        if new_role:
            membership.role = new_role
            membership.save(update_fields=['role'])
            return Response({"detail": "User role updated"}, status=HTTPStatus.OK)
        return Response({"error": "Role not provided"}, status=HTTPStatus.BAD_REQUEST) 


class ModuleView(APIView):
    def post(self, request, project_id):
        print('project_id: ', project_id)
        if not project_id:
            return Response({"error": "Project ID is required"}, status=HTTPStatus.BAD_REQUEST)

        project = get_object_or_404(Project, id=project_id)
        media = settings.MEDIA_ROOT

        # prepare data for serializer
        data = request.data.copy()
        data["project_id"] = project.id

        print('data: ', data)

        serializer = ModuleSerializer(data=data)
        if serializer.is_valid():
            # Pass created_by explicitly here
            module = serializer.save(
                created_by=request.user,
                project=project
            )

            # 🔥 auto-generate folder_path & collection_name
            module.folder_path = f"project_{project.id}/module_{module.id}"
            complete_path = os.path.join(media, module.folder_path)
            os.makedirs(complete_path, exist_ok=True)

            module.save(update_fields=["folder_path"])

            return Response(ModuleSerializer(module).data, status=HTTPStatus.CREATED)

        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    
    def get(self, request, module_id=None):
        if module_id:
            module = get_object_or_404(Module, id=module_id)
            serializer = ModuleSerializer(module)
            return Response(serializer.data)
        modules = Module.objects.all()
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data)
    
    def put(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)

        # Remove restricted fields from request before updating
        data = request.data.copy()
        data.pop("created_by", None)
        data.pop("project", None)
        data.pop("folder_path", None)

        serializer = ModuleSerializer(module, data=data, partial=True)

        if serializer.is_valid():
            module = serializer.save()

            # Always ensure system fields are consistent
            module.collection_name = f"{module.project.name.lower().replace(' ', '_')}_module_{module.id}"
            module.save(update_fields=["collection_name", "updated_at"])

            return Response(ModuleSerializer(module).data)

        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
  
    def delete(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)
        module.delete()
        return Response(status=HTTPStatus.NO_CONTENT)


class DocumentView(APIView):
    def get(self, request, document_id=None):
        if document_id:
            document = get_object_or_404(Document, id=document_id)
            serializer = DocumentSerializer(document)
            return Response(serializer.data, status=HTTPStatus.ACCEPTED)

        documents = Document.objects.all()
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)

    def post(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)

        upload_file = request.FILES.get('file')
        data = request.data.copy()

        if not upload_file:
            return Response({"error": "No file provided"}, status=HTTPStatus.BAD_REQUEST)
        
        module_folder = module.folder_path
        save_path = os.path.join(settings.MEDIA_ROOT, module_folder)
        os.makedirs(save_path, exist_ok=True)

        file_path = os.path.join(save_path, upload_file.name)
        file_name = data["file_name"] if "file_name" in data else upload_file.name
        file_name = file_name + uuid.uuid5()

        with open(file_path, 'wb+') as dest:
            for chunk in upload_file.chunks():
                dest.write(chunk)

        document = Document.objects.create(
            title = request.data.get("title", file_name),
            file = upload_file,
            file_path = file_path,
            module = module,
            upload_file = request.user.id
        )

        return Response(
            DocumentSerializer(document).data,
            status = HTTPStatus.CREATED
        )
    

    def put(self, request, document_id):
        document = get_object_or_404(Document, id=document_id)

        # Exclude fields that should not be updated
        restricted_fields = {"uploaded_by", "module", "file_path"}
        update_data = {k: v for k, v in request.data.items() if k not in restricted_fields}

        serializer = DocumentSerializer(document, data=update_data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.CREATED)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    

    def delete(self, request, document_id):
        document = get_object_or_404(Document, id=document_id)
        document.delete()
        return Response({"detail": "Document deleted successfully"}, status=HTTPStatus.NO_CONTENT)
  

class ProjectModuleListView(APIView):
    def get(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        modules = Module.objects.filter(project=project)
        serializer = ModuleSerializer(modules, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)


class DocumentModulesListView(APIView):
    def get(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)
        documents = Document.objects.filter(module=module)
        serializer = DocumentSerializer(documents, many=True)
        return Response(serializer.data, status=HTTPStatus.OK)
    
    def post(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)
        
        # Get uploaded file
        upload_file = request.FILES.get('file')
        if not upload_file:
            return Response(
                {"error": "No file provided"}, 
                status=HTTPStatus.BAD_REQUEST
            )
        
        # File validation
        max_size = 10 * 1024 * 1024  # 10MB limit
        if upload_file.size > max_size:
            return Response(
                {"error": "File size exceeds 10MB limit"}, 
                status=HTTPStatus.BAD_REQUEST
            )
        
        # Validate file extension
        allowed_extensions = ['.pdf', '.doc', '.docx', '.txt', '.md']
        file_ext = os.path.splitext(upload_file.name)[1].lower()
        if file_ext not in allowed_extensions:
            return Response(
                {"error": f"File type {file_ext} not allowed. Allowed types: {', '.join(allowed_extensions)}"}, 
                status=HTTPStatus.BAD_REQUEST
            )
        
        # Create document - Django FileField handles the file storage automatically
        document = Document.objects.create(
            title=request.data.get("title", upload_file.name),
            file=upload_file,  # Django handles the storage automatically
            module=module,
            uploaded_by=request.user  # Fixed field name
        )

        # if vector store exists for module, update status to empty to trigger re-indexing
        vector_store = ModuleVectorStore.objects.get(module=module)
        vector_store.status = 'empty'
        vector_store.save(update_fields=['status'])

        return Response(
            DocumentSerializer(document).data,
            status=HTTPStatus.CREATED
        )


class DocumentDownloadView(APIView):
    def get(self, request, document_id):
        """Download a document file"""
        try:
            # Get the document object
            document = get_object_or_404(Document, id=document_id, active=True)
            
            # Check if file exists
            if not document.file:
                return Response(
                    {"error": "File not found for this document"}, 
                    status=HTTPStatus.NOT_FOUND
                )
            
            # Get file path
            file_path = document.file.path
            
            # Check if file physically exists
            if not os.path.exists(file_path):
                return Response(
                    {"error": "File not found on server"}, 
                    status=HTTPStatus.NOT_FOUND
                )
            
            # Get file information
            file_size = os.path.getsize(file_path)
            file_name = document.title or os.path.basename(file_path)
            
            # Ensure file name has extension
            if not os.path.splitext(file_name)[1] and document.file_type:
                file_name = f"{file_name}{document.file_type}"
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # Create file response
            try:
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=mime_type,
                    as_attachment=True,
                    filename=file_name
                )
                
                # Add headers
                response['Content-Length'] = file_size
                response['Content-Disposition'] = f'attachment; filename="{file_name}"'
                
                return response
                
            except IOError:
                return Response(
                    {"error": "Error reading file"}, 
                    status=HTTPStatus.INTERNAL_SERVER_ERROR
                )
            
        except Exception as e:
            return Response(
                {"error": f"Download failed: {str(e)}"}, 
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )


class DocumentStreamView(APIView):
    def get(self, request, document_id):
        """Stream a document file for viewing in browser"""
        try:
            document = get_object_or_404(Document, id=document_id, active=True)
            
            if not document.file or not os.path.exists(document.file.path):
                raise Http404("File not found")
            
            file_path = document.file.path
            file_name = document.title or os.path.basename(file_path)
            
            # Get MIME type
            mime_type, _ = mimetypes.guess_type(file_path)
            if not mime_type:
                mime_type = 'application/octet-stream'
            
            # For PDF files, show inline; for others, download
            if mime_type == 'application/pdf':
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=mime_type,
                    as_attachment=False,  # Display in browser
                    filename=file_name
                )
                response['Content-Disposition'] = f'inline; filename="{file_name}"'
            else:
                response = FileResponse(
                    open(file_path, 'rb'),
                    content_type=mime_type,
                    as_attachment=True,
                    filename=file_name
                )
                response['Content-Disposition'] = f'attachment; filename="{file_name}"'
            
            return response
            
        except Exception as e:
            raise Http404(f"File download error: {str(e)}")


class DocumentInfoView(APIView):
    
    def get(self, request, document_id):
        """Get document metadata"""
        try:
            document = get_object_or_404(Document, id=document_id, active=True)
            
            file_info = {
                'id': document.id,
                'title': document.title,
                'file_name': os.path.basename(document.file.name) if document.file else None,
                'file_size': document.file.size if document.file else 0,
                'file_type': document.file_type,
                'uploaded_at': document.uploaded_at,
                'uploaded_by': document.uploaded_by.username if document.uploaded_by else None,
                'module': document.module.name,
                'download_url': request.build_absolute_uri(
                    f'/api/documents/{document.id}/download/'
                ) if document.file else None,
                'stream_url': request.build_absolute_uri(
                    f'/api/documents/{document.id}/stream/'
                ) if document.file else None,
            }
            
            return Response(file_info, status=HTTPStatus.OK)
            
        except Exception as e:
            return Response(
                {"error": f"Failed to get document info: {str(e)}"}, 
                status=HTTPStatus.INTERNAL_SERVER_ERROR
            )

