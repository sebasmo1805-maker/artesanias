from django.core.management.base import BaseCommand, CommandError
from django.contrib.auth import get_user_model
from django.db import transaction
from main import utils

User = get_user_model()

class Command(BaseCommand):
    help = "Borra un usuario de la base de datos y limpia sus solicitudes en ferias.json"

    def add_arguments(self, parser):
        grp = parser.add_mutually_exclusive_group(required=True)
        grp.add_argument("--username", type=str, help="Username del usuario a borrar")
        grp.add_argument("--id", type=int, help="ID del usuario a borrar")
        parser.add_argument("--force", action="store_true",
                            help="Permite borrar al último admin (⚠️ úsalo con cuidado)")
        parser.add_argument("--dry-run", action="store_true",
                            help="Muestra lo que haría, sin aplicar cambios")
        parser.add_argument("--yes", "-y", action="store_true",
                            help="No pedir confirmación interactiva")

    def handle(self, *args, **opts):
        username = opts.get("username")
        uid = opts.get("id")
        force = opts.get("force")
        dry_run = opts.get("dry_run")
        auto_yes = opts.get("yes")

        # --- localizar usuario ---
        try:
            if username:
                user = User.objects.get(username=username)
            else:
                user = User.objects.get(pk=uid)
        except User.DoesNotExist:
            raise CommandError("Usuario no encontrado.")

        uid = user.id
        uname = user.username

        # --- protecciones ---
        admin_count = User.objects.filter(role="admin").count()
        if user.role == "admin" and admin_count <= 1 and not force:
            raise CommandError(
                "No puedes borrar al último administrador. Usa --force si realmente quieres hacerlo."
            )

        # --- resumen previo ---
        data = utils.load_data()
        solicitudes = data.get("solicitudes", [])
        a_borrar = [
            s for s in solicitudes
            if s.get("user_id") == uid or s.get("usuario") == uname  # compat entradas viejas
        ]

        self.stdout.write(self.style.NOTICE("Resumen:"))
        self.stdout.write(f"  Usuario: {uname} (id={uid}, rol={user.role})")
        self.stdout.write(f"  Solicitudes a eliminar en ferias.json: {len(a_borrar)}")

        if dry_run:
            self.stdout.write(self.style.SUCCESS("Dry-run: no se aplicarán cambios."))
            return

        if not auto_yes:
            confirm = input(f"¿Eliminar usuario '{uname}' y sus solicitudes? [y/N]: ").strip().lower()
            if confirm != "y":
                self.stdout.write(self.style.WARNING("Cancelado por el usuario."))
                return

        # --- ejecutar ---
        with transaction.atomic():
            user.delete()
            data["solicitudes"] = [
                s for s in solicitudes
                if not (s.get("user_id") == uid or s.get("usuario") == uname)
            ]
            utils.save_data(data)

        self.stdout.write(self.style.SUCCESS(
            f"Usuario '{uname}' eliminado y {len(a_borrar)} solicitudes limpiadas."
        ))
