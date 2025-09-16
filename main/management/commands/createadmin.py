from django.core.management.base import BaseCommand
from main.models import CustomUser

class Command(BaseCommand):
    help = 'Crea el usuario admin por defecto'

    def handle(self, *args, **kwargs):
        if not CustomUser.objects.filter(username='admin').exists():
            CustomUser.objects.create_superuser(username='admin', password='admin', role='admin')
            self.stdout.write(self.style.SUCCESS('Usuario admin creado'))
        else:
            self.stdout.write(self.style.WARNING('El usuario admin ya existe'))
