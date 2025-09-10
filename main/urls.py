from django.urls import path
from . import views

urlpatterns = [
    path('', views.public_view, name='home'), 
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),
    path('panel/', views.user_panel, name='user_panel'),
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path("public/", views.public_view, name="public_view"),
    path("admin-panel/delete-artesano/<int:artesano_id>/", views.delete_artesano_view, name="delete_artesano"),
    path("admin-panel/edit-artesano/<int:artesano_id>/", views.edit_artesano_view, name="edit_artesano"),
    path(
        "admin-panel/editar-artesano/<int:artesano_id>/",
        views.edit_artesano_view,
        name="editar_artesano"
    ),
    path("editar-feria/<int:feria_id>/", views.editar_feria, name="editar_feria"), 
]
