from django.urls import path
from .views import UserView, ProjectView, ModuleView

urlpatterns = [
    # User routes
    path('users/', UserView.as_view(), name='user-list-create'),
    path('users/<int:user_id>/', UserView.as_view(), name='user-detail'),

    # Project routes
    path('projects/', ProjectView.as_view(), name='project-list-create'),
    path('projects/<int:project_id>/', ProjectView.as_view(), name='project-detail'),

    # Module routes
    path('modules/', ModuleView.as_view(), name='module-list-create'),
    path('modules/<int:module_id>/', ModuleView.as_view(), name='module-detail'),
]
