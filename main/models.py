from django.contrib.auth.models import AbstractUser
from django.db import models
from django.conf import settings
from django.db import models

class CustomUser(AbstractUser):
    ROLE_CHOICES = (
        ('admin', 'Administrador'),
        ('user', 'Usuario'),
        ('artesano', 'Artesano'),   # 👈 agregado
    )
    role = models.CharField(max_length=20, choices=ROLE_CHOICES, default='user')
    email = models.EmailField(unique=True)
    username = models.CharField(max_length=150, unique=True)
    ferias_favoritas = models.ManyToManyField('Feria', blank=True, related_name='usuarios_favoritos')

    def __str__(self):
        return f"{self.username} ({self.role})"

class SolicitudFeria(models.Model):
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="solicitudes"
    )
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    feria_id = models.IntegerField()
    tipo = models.CharField(max_length=50)
    estado = models.CharField(max_length=20, default="pendiente")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.nombre} ({self.tipo}) - {self.estado}"
class Feria(models.Model):
    nombre = models.CharField(max_length=100)
    fecha_inicio = models.DateField()
    fecha_fin = models.DateField()
    preferencias = models.TextField(blank=True)
    ocupados = models.IntegerField(default=0)

    def __str__(self):
        return self.nombre

# --- NUEVO: Modelo Artesano y Producto ---

class Artesano(models.Model):
    usuario = models.OneToOneField(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='perfil_artesano')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

class Producto(models.Model):
    artesano = models.ForeignKey(Artesano, on_delete=models.CASCADE, related_name='productos')
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)

    def __str__(self):
        return self.nombre

