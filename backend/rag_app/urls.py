from django.urls import path
from .views import UserView, ProjectView, ModuleView, DocumentView, ProjectModuleListView, DocumentModulesListView, DocumentDownloadView, DocumentStreamView, DocumentInfoView
from rest_framework.authtoken.views import obtain_auth_token

urlpatterns = [
    # User routes
    path("login/", obtain_auth_token, name="api_token_auth"),  # Endpoint for obtaining auth token

    path('users/', UserView.as_view(), name='user-list-create'),
    path('users/<int:user_id>/', UserView.as_view(), name='user-detail'),

    # Project routes
    path('projects/', ProjectView.as_view(), name='project-list-create'),
    path('projects/<int:project_id>/', ProjectView.as_view(), name='project-detail'),
    path('projects/<int:project_id>/modules/', ProjectModuleListView.as_view(), name='project-modules'),

    # Module routes
    path('modules/', ModuleView.as_view(), name='module-list-create'),
    path('modules/<int:project_id>/', ModuleView.as_view(), name='module-list-create'),
    path('modules_details/<int:module_id>/', ModuleView.as_view(), name='module-detail'),
    path('documents/', DocumentView.as_view(), name='document-list-create'),
    path('documents/<int:document_id>/', DocumentView.as_view(), name='document-detail'),

    path('modules/<int:module_id>/documents/', DocumentModulesListView.as_view(), name='module-documents'),

    path('documents/<int:document_id>/download/', DocumentDownloadView.as_view(), name='document-download'),
    path('documents/<int:document_id>/stream/', DocumentStreamView.as_view(), name='document-stream'),
    path('documents/<int:document_id>/info/', DocumentInfoView.as_view(), name='document-info'),
]
