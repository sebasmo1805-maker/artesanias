from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from django.forms import formset_factory
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import PasswordResetForm
from django.utils.translation import gettext_lazy as _
from .models import Artesano, Producto
from django.forms import inlineformset_factory

# ============ Registro / Login ============
from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth import get_user_model
from .models import Feria


class RegisterForm(forms.Form):
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")

    def clean_password(self):
        password = self.cleaned_data.get('password')
        
        # Verificar longitud mínima de 8 caracteres
        if len(password) < 8:
            raise ValidationError('La contraseña es muy corta. Debe tener al menos 8 caracteres.')
        
        # Verificar si la contraseña es solo numérica
        if password.isdigit():
            raise ValidationError('La contraseña no puede ser solo numérica.')
        
        # Verificar si la contraseña es solo letras
        if password.isalpha():
            raise ValidationError('La contraseña no puede ser solo letras.')
        
        return password

    def clean_confirm_password(self):
        confirm_password = self.cleaned_data.get('confirm_password')
        password = self.cleaned_data.get('password')
        
        # Verificar si las contraseñas coinciden
        if confirm_password != password:
            raise ValidationError('Las contraseñas no coinciden.')
        return confirm_password

class RegisterForm(forms.ModelForm):
    username = forms.CharField(max_length=150, label="Nombre de usuario")
    email = forms.EmailField(label="Correo electrónico", max_length=254)
    password = forms.CharField(widget=forms.PasswordInput, label="Contraseña")
    confirm_password = forms.CharField(widget=forms.PasswordInput, label="Confirmar contraseña")
    role = forms.ChoiceField(
        choices=[('user', 'Usuario'), ('artesano', 'Artesano')],
        label="Rol"
    )

    class Meta:
        model = get_user_model()
        fields = ['username', 'email', 'password', 'role']

    def clean_password(self):
        password = self.cleaned_data.get('password')

        # Verificar longitud mínima de 8 caracteres
        if len(password) < 8:
            raise ValidationError('La contraseña es muy corta. Debe tener al menos 8 caracteres.')
        
        # Verificar si la contraseña es solo numérica
        if password.isdigit():
            raise ValidationError('La contraseña no puede ser solo numérica.')
        
        # Verificar si la contraseña es solo letras
        if password.isalpha():
            raise ValidationError('La contraseña no puede ser solo letras.')

        return password

    def clean_confirm_password(self):
        confirm_password = self.cleaned_data.get('confirm_password')
        password = self.cleaned_data.get('password')

        # Verificar si las contraseñas coinciden
        if confirm_password != password:
            raise ValidationError('Las contraseñas no coinciden.')
        
        return confirm_password

    def save(self, commit=True):
        user = super().save(commit=False)
        user.set_password(self.cleaned_data['password'])  # Encripta la contraseña
        if commit:
            user.save()
        return user




class LoginForm(AuthenticationForm):
    pass


# ============ Ferias / Tipos (admin) ============

class FeriaForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre de la feria")
    fecha_inicio = forms.DateField(label="Fecha de inicio", widget=forms.DateInput(attrs={"type": "date"}))
    fecha_fin = forms.DateField(label="Fecha de fin", widget=forms.DateInput(attrs={"type": "date"}))
    preferencias = forms.CharField(max_length=200, label="Preferencias del público", required=False)


class TipoProductoForm(forms.Form):
    tipo = forms.CharField(max_length=50, label="Nombre del tipo")
    cupos = forms.IntegerField(label="Cupos para este tipo")

TipoProductoFormSet = formset_factory(TipoProductoForm, extra=1)


# ============ (LEGADO) Form de Artesano para admin ============
# Lo dejamos por compatibilidad con tu panel actual, aunque ya no se usa para crear.
class ArtesanoForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre del Artesano")
    descripcion = forms.CharField(widget=forms.Textarea, label="Descripción")
    feria_id = forms.ChoiceField(
        choices=[],
        label="Feria",
        widget=forms.Select(attrs={"id": "feria_id"})
    )
    tipo = forms.ChoiceField(choices=[], label="Tipo de Producto")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from . import utils
        data = utils.load_data()
        ferias = data.get("ferias", [])

        # Ferias con cupos
        ferias_disponibles = []
        for f in ferias:
            total_cupos = sum(tp["cupos"] for tp in f.get("tipos_productos", []))
            ocupados = f.get("ocupados", 0)
            if ocupados < total_cupos:
                ferias_disponibles.append(
                    (f["id"], f"{f.get('nombre', f'Feria {f['id']}')} - {f.get('fecha_inicio','')} al {f.get('fecha_fin','')}")
                )

        if not ferias_disponibles:
            ferias_disponibles = [("", "⚠ No hay ferias disponibles")]

        self.fields["feria_id"].choices = ferias_disponibles

        # Cargar tipos según feria elegida
        feria_id = self.data.get("feria_id") or self.initial.get("feria_id")
        if feria_id:
            try:
                feria_id = int(feria_id)
                feria = next(f for f in ferias if f["id"] == feria_id)
                tipos = [(tp["tipo"], tp["tipo"]) for tp in feria.get("tipos_productos", [])]
                self.fields["tipo"].choices = tipos
            except Exception:
                self.fields["tipo"].choices = []
        else:
            self.fields["tipo"].choices = []


# ============ Nuevo: Formulario de Solicitud para Artesano ============

class SolicitudFeriaForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre del Artesano")
    descripcion = forms.CharField(widget=forms.Textarea, label="Descripción")
    feria_id = forms.ChoiceField(choices=[], label="Feria")
    tipo = forms.ChoiceField(choices=[], label="Tipo de Producto")

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from . import utils
        data = utils.load_data()
        ferias = data.get("ferias", [])

        # opciones de ferias
        self.fields["feria_id"].choices = [
            (f["id"], f.get("nombre", f"Feria {f['id']}"))
            for f in ferias
        ] or [("", "⚠ No hay ferias")]

        # cargar tipos si ya hay feria seleccionada
        feria_id = self.data.get("feria_id") or self.initial.get("feria_id")
        if feria_id:
            try:
                feria_id = int(feria_id)
                feria = next(f for f in ferias if f["id"] == feria_id)
                tipos = [(tp["tipo"], tp["tipo"]) for tp in feria.get("tipos_productos", [])]
                self.fields["tipo"].choices = tipos
            except Exception:
                self.fields["tipo"].choices = []
        else:
            self.fields["tipo"].choices = []


User = get_user_model()

class UserEditForm(forms.ModelForm):
    password = forms.CharField(
        label="Nueva contraseña",
        widget=forms.PasswordInput,
        required=False,
        help_text="Déjalo vacío para no cambiarla."
    )

    class Meta:
        model = User
        fields = ("username", "email", "role", "is_active")

    def save(self, commit=True):
        user = super().save(commit=False)
        pwd = self.cleaned_data.get("password")
        if pwd:
            user.set_password(pwd)
        if commit:
            user.save()
        return user


class CustomPasswordResetForm(PasswordResetForm):
    # Sobrecargar los mensajes de error de validación
    error_messages = {
        'password_mismatch': _("Las contraseñas no coinciden."),
        'too_common': _("Esta contraseña es demasiado común."),
        'too_short': _("Esta contraseña es demasiado corta. Debe tener al menos 8 caracteres."),
        'entirely_numeric': _("La contraseña no puede ser completamente numérica."),
        'similar': _("La contraseña no puede ser demasiado similar a tu nombre de usuario."),
        'numeric': _("La contraseña no puede contener solo números."),
    }

class ArtesanoPerfilForm(forms.ModelForm):
    class Meta:
        model = Artesano
        fields = ['nombre', 'descripcion']

ProductoFormSet = inlineformset_factory(
    Artesano, Producto,
    fields=['nombre', 'descripcion'],
    extra=1, can_delete=True
)