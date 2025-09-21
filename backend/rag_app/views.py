from django.shortcuts import render

# Create your views here.
from http import HTTPStatus
from django.shortcuts import get_object_or_404, redirect
from django.views import View

from django.db.models import Case, CharField, Q, Value, When
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet
from rest_framework.pagination import PageNumberPagination

from .models import User, Project, Module, Document
from .serializers import UserSerializer, ProjectSerializer, ModuleSerializer, DocumentSerializer

class UserView(APIView):
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

class ProjectView(APIView):
    def post(self, request):
        serializer = ProjectSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.CREATED)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    
    def get(self, request, project_id=None):
        if project_id:
            project = get_object_or_404(Project, id=project_id)
            serializer = ProjectSerializer(project)
            return Response(serializer.data)
        projects = Project.objects.all()
        serializer = ProjectSerializer(projects, many=True)
        return Response(serializer.data)
    
    def put(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        serializer = ProjectSerializer(project, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    
    def delete(self, request, project_id):
        project = get_object_or_404(Project, id=project_id)
        project.delete()
        return Response(status=HTTPStatus.NO_CONTENT)
    
class ModuleView(APIView):
    def post(self, request):
        serializer = ModuleSerializer(data=request.data)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data, status=HTTPStatus.CREATED)
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
        serializer = ModuleSerializer(module, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response(serializer.data)
        return Response(serializer.errors, status=HTTPStatus.BAD_REQUEST)
    
    def delete(self, request, module_id):
        module = get_object_or_404(Module, id=module_id)
        module.delete()
        return Response(status=HTTPStatus.NO_CONTENT)

