from django.urls import path
from . import views
from django.contrib.auth import views as auth_views
from django.urls import path, reverse_lazy

urlpatterns = [
    # --- Público ---
    path('', views.public_view, name='home'), 
    path('public/', views.public_view, name='public_view'),

    # --- Autenticación ---
    path('register/', views.register_view, name='register'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # --- Paneles según rol ---
    path('panel/', views.user_panel, name='user_panel'),
    path('panel/artesano/', views.artesano_panel, name='artesano_panel'),   # 👈 faltaba
    path('panel/admin/', views.admin_panel, name='admin_panel'),

    # --- Gestión de Artesanos ---
    path("panel/admin/delete-artesano/<int:artesano_id>/", views.delete_artesano_view, name="delete_artesano"),
    path("panel/admin/edit-artesano/<int:artesano_id>/", views.edit_artesano_view, name="edit_artesano"),
    path("panel/admin/editar-artesano/<int:artesano_id>/", views.edit_artesano_view, name="editar_artesano"),  # 👈 para tu template

    # --- Gestión de Ferias ---
    path("panel/admin/editar-feria/<int:feria_id>/", views.editar_feria, name="editar_feria"),
    path("panel/admin/usuarios/<int:user_id>/editar/", views.edit_user_view, name="edit_user"),
    path('password-reset/',
         auth_views.PasswordResetView.as_view(
             template_name='auth/password_reset.html',
             email_template_name='auth/password_reset_email.txt',
             subject_template_name='auth/password_reset_subject.txt',
             success_url=reverse_lazy('password_reset_done'),
         ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(
        template_name='auth/password_reset_done.html'), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(
        template_name='auth/password_reset_confirm.html',
        success_url=reverse_lazy('password_reset_complete'),
    ), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(
        template_name='auth/password_reset_complete.html'), name='password_reset_complete'),

            path('password-reset/', auth_views.PasswordResetView.as_view(template_name='auth/password_reset.html'), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset/done/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),

    path('editar-perfil-artesano/', views.editar_perfil_artesano, name='editar_perfil_artesano'),

]
