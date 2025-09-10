from django import forms
from django.contrib.auth.forms import AuthenticationForm
from .models import CustomUser
from django.forms import formset_factory

class RegisterForm(forms.ModelForm):
    username = forms.CharField(
        max_length=150,
        label="Nombre de usuario",
        help_text='',  # Elimina el help_text por defecto
    )
    password = forms.CharField(widget=forms.PasswordInput)
    confirm_password = forms.CharField(widget=forms.PasswordInput)

    class Meta:
        model = CustomUser
        fields = ['username', 'password']

    def clean(self):
        cleaned_data = super().clean()
        password = cleaned_data.get("password")
        confirm_password = cleaned_data.get("confirm_password")
        if password != confirm_password:
            raise forms.ValidationError("Las contraseñas no coinciden.")
        return cleaned_data

class LoginForm(AuthenticationForm):
    pass


class FeriaForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre de la feria")  # <-- aquí
    fecha_inicio = forms.DateField(label="Fecha de inicio", widget=forms.DateInput(attrs={"type": "date"}))
    fecha_fin = forms.DateField(label="Fecha de fin", widget=forms.DateInput(attrs={"type": "date"}))
    preferencias = forms.CharField(max_length=200, label="Preferencias del público", required=False)




class TipoProductoForm(forms.Form):
    tipo = forms.CharField(max_length=50, label="Nombre del tipo")
    cupos = forms.IntegerField(label="Cupos para este tipo")

TipoProductoFormSet = formset_factory(TipoProductoForm, extra=1)


class ArtesanoForm(forms.Form):
    nombre = forms.CharField(max_length=100, label="Nombre del Artesano")
    descripcion = forms.CharField(widget=forms.Textarea, label="Descripción")
    feria_id = forms.ChoiceField(
        choices=[], 
        label="Feria",
        widget=forms.Select(attrs={"id": "feria_id"})
    )
    tipo = forms.ChoiceField(choices=[], label="Tipo de Producto")  # Cambio a ChoiceField

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        from . import utils
        data = utils.load_data()
        ferias = data.get("ferias", [])

        # --- Opciones de ferias disponibles ---
        ferias_disponibles = []
        for f in ferias:
            total_cupos = sum(tp["cupos"] for tp in f.get("tipos_productos", []))
            ocupados = f.get("ocupados", 0)
            if ocupados < total_cupos:
                fecha_inicio = f.get("fecha_inicio", "")
                fecha_fin = f.get("fecha_fin", "")
                ferias_disponibles.append((
                    f["id"],
                    f"Feria {f['id']} - {fecha_inicio} al {fecha_fin}"
                ))


        if not ferias_disponibles:
            ferias_disponibles = [("", "⚠ No hay ferias disponibles")]

        self.fields["feria_id"].choices = ferias_disponibles

        # --- Si ya se seleccionó una feria, cargar sus tipos ---
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
