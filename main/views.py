from django.shortcuts import render, redirect
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from .models import CustomUser
from . import utils
from django.http import HttpResponseRedirect
from django.urls import reverse
from .utils import load_data, save_data
from django.contrib import messages
from django.forms import formset_factory
from .forms import SolicitudFeriaForm
import json
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from .forms import UserEditForm 
User = get_user_model()
from django.contrib.auth.views import PasswordResetView
from .forms import CustomPasswordResetForm
from django.shortcuts import render
from .models import Feria

class CustomPasswordResetView(PasswordResetView):
    form_class = CustomPasswordResetForm
# 👇 Formularios
from .forms import (
    RegisterForm, LoginForm,
    FeriaForm, ArtesanoForm, TipoProductoFormSet,
    SolicitudFeriaForm,
    ArtesanoPerfilForm, ProductoFormSet
)

import json


def register_view(request):
    """
    Vista para registrar un nuevo usuario.
    """
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])  # Asegúrate de setear la contraseña encriptada
            user.save()

            # Mostrar mensaje de éxito
            messages.success(request, "Cuenta creada correctamente. Inicia sesión.")
            return redirect('login')  # Redirigir a la página de login
        else:
            messages.error(request, "Hubo un error con el formulario. Verifica los campos.")
    else:
        form = RegisterForm()

    return render(request, 'usuario_sin_registrar/register.html', {'form': form})









# =================== Login / Logout ===================

def login_view(request):
    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            # Redirigir al panel de acuerdo al rol del usuario
            if user.role == 'admin':
                return redirect('admin_panel')
            elif user.role == 'artesano':
                return redirect('artesano_panel')
            else:
                return redirect('user_panel')
    else:
        form = LoginForm()
        return render(request, 'usuario_sin_registrar/login.html', {'form': form})





def logout_view(request):
    logout(request)
    return redirect('login')


# =================== Paneles por Rol ===================

# Asegúrate de importar el formulario en la parte superior del archivo views.py
from .forms import SolicitudFeriaForm  # Asegúrate de que este formulario esté definido

@login_required
def user_panel(request):
    data = utils.load_data()
    ferias_json = data.get("ferias", [])
    artesanos = data.get("artesanos", [])
    solicitudes = data.get("solicitudes", [])

    # --- Sincroniza ferias del modelo con el JSON (solo nombre y fechas) ---
    ferias_db_map = {}
    for f in ferias_json:
        feria_obj, _ = Feria.objects.get_or_create(
            nombre=f.get("nombre", f"Feria {f.get('id')}"),
            defaults={
                "fecha_inicio": f.get("fecha_inicio") or "2000-01-01",
                "fecha_fin": f.get("fecha_fin") or "2000-01-01",
                "preferencias": f.get("preferencias", ""),
                "ocupados": f.get("ocupados", 0),
            }
        )
        ferias_db_map[f["id"]] = feria_obj

    # --- Favoritos ---
    if request.method == "POST" and "fav_feria_id" in request.POST:
        feria_json_id = int(request.POST.get("fav_feria_id"))
        feria_obj = ferias_db_map.get(feria_json_id)
        if feria_obj:
            if feria_obj in request.user.ferias_favoritas.all():
                request.user.ferias_favoritas.remove(feria_obj)
            else:
                request.user.ferias_favoritas.add(feria_obj)
        return redirect('user_panel')

    favoritas = request.user.ferias_favoritas.all()
    favoritas_ids = list(favoritas.values_list('id', flat=True))

    # ====== construir ferias (con cupos y tipos) ======
    ferias_detalles = []
    for f in ferias_json:
        total_cupos = sum(tp.get("cupos", 0) for tp in f.get("tipos_productos", []))
        if not total_cupos:
            total_cupos = f.get("cupos_totales") or 0

        ocupados = sum(1 for a in artesanos if a.get("feria_id") == f.get("id"))

        tipos_info = []
        for tp in f.get("tipos_productos", []):
            ocupados_tipo = sum(
                1 for a in artesanos
                if a.get("feria_id") == f.get("id") and a.get("tipo") == tp.get("tipo")
            )
            tipos_info.append({
                "tipo": tp.get("tipo"),
                "cupos": tp.get("cupos", 0),
                "ocupados": ocupados_tipo,
            })

        ferias_detalles.append({
            "id": f.get("id"),
            "nombre": f.get("nombre", f"Feria {f.get('id')}"),
            "fecha_inicio": f.get("fecha_inicio", ""),
            "fecha_fin": f.get("fecha_fin", ""),
            "total_cupos": total_cupos,
            "ocupados": ocupados,
            "tipos": tipos_info,
        })

    ferias_tipos = {
        str(f["id"]): f["tipos"]
        for f in ferias_detalles
    }

    form = SolicitudFeriaForm()

    return render(request, "usuario_registrado/user_panel.html", {
        "form": form,
        "solicitudes": [s for s in solicitudes if s.get("usuario") == request.user.username],
        "ferias": ferias_detalles,
        "ferias_tipos_json": json.dumps(ferias_tipos),
        "favoritas": favoritas,
        "favoritas_ids": list(ferias_db_map[k].id for k in ferias_db_map if ferias_db_map[k] in favoritas),
        "artesanos": artesanos,  # <-- Agrega esta línea
    })





@login_required
def artesano_panel(request):
    if request.user.role != 'artesano':
        return redirect('user_panel' if request.user.role == 'user' else 'admin_panel')

    data = utils.load_data()
    ferias = data.get("ferias", [])
    artesanos = data.get("artesanos", [])
    solicitudes = data.get("solicitudes", [])

    # 👇 siempre define el form en GET
    form = SolicitudFeriaForm()

    if request.method == "POST":
        form = SolicitudFeriaForm(request.POST)
        if form.is_valid():
            utils.add_solicitud({
                "usuario": request.user.username,
                "nombre": form.cleaned_data["nombre"],
                "descripcion": form.cleaned_data["descripcion"],
                "feria_id": int(form.cleaned_data["feria_id"]),
                "tipo": form.cleaned_data["tipo"],
            })
            messages.success(request, "Solicitud enviada. Espera la aprobación del administrador.")
            return redirect("artesano_panel")

    # ---- construir ferias con cupos para mostrar en selects ----
    ferias_detalles = []
    for f in ferias:
        total_cupos = sum(tp.get("cupos", 0) for tp in f.get("tipos_productos", [])) or f.get("cupos_totales", 0)
        ocupados = sum(1 for a in artesanos if a.get("feria_id") == f.get("id"))
        tipos_info = []
        for tp in f.get("tipos_productos", []):
            ocupados_tipo = sum(1 for a in artesanos if a.get("feria_id") == f.get("id") and a.get("tipo") == tp.get("tipo"))
            tipos_info.append({"tipo": tp.get("tipo"), "cupos": tp.get("cupos", 0), "ocupados": ocupados_tipo})
        ferias_detalles.append({
            "id": f.get("id"),
            "nombre": f.get("nombre", f"Feria {f.get('id')}"),
            "fecha_inicio": f.get("fecha_inicio", ""),
            "fecha_fin": f.get("fecha_fin", ""),
            "total_cupos": total_cupos,
            "ocupados": ocupados,
            "tipos": tipos_info,
        })

    # mapa feria -> tipos (para llenar el combo con ocupados/cupos)
    ferias_tipos = {str(f["id"]): f["tipos"] for f in ferias_detalles}

    mis_solicitudes = [s for s in solicitudes if s.get("usuario") == request.user.username]

    # Obtener perfil y productos actuales del artesano
    try:
        artesano_obj = Artesano.objects.get(usuario=request.user)
        productos = list(Producto.objects.filter(artesano=artesano_obj))
    except Artesano.DoesNotExist:
        artesano_obj = None
        productos = []

    return render(request, "usuario_registrado/artesano_panel.html", {
        "form": form,
        "solicitudes": mis_solicitudes,
        "ferias": ferias_detalles,
        "ferias_tipos_json": json.dumps(ferias_tipos),
        "perfil_artesano": artesano_obj,
        "productos": productos,
    })

# =================== Panel del Admin ===================

@login_required
def admin_panel(request):
    if request.user.role != 'admin':
        return redirect('user_panel' if request.user.role == 'user' else 'artesano_panel')

    # --------- POST: crear feria / editar / eliminar / aprobar-rechazar solicitudes ---------
    if request.method == "POST":
        # Crear feria
        if "crear_feria" in request.POST:
            feria_form = FeriaForm(request.POST)
            tipo_formset = TipoProductoFormSet(request.POST, prefix="tipos")

            if feria_form.is_valid() and tipo_formset.is_valid():
                tipos_productos = []
                total_cupos = 0
                for f in tipo_formset:
                    if f.cleaned_data:
                        tipo = f.cleaned_data.get("tipo")
                        cupos = f.cleaned_data.get("cupos")
                        if tipo and cupos is not None:
                            tipos_productos.append({"tipo": tipo, "cupos": int(cupos)})
                            total_cupos += int(cupos)

                utils.add_feria({
                    "nombre": request.POST.get("nombre"),
                    "fecha_inicio": request.POST.get("fecha_inicio"),
                    "fecha_fin": request.POST.get("fecha_fin"),
                    "preferencias": feria_form.cleaned_data["preferencias"],
                    "ocupados": 0,
                    "tipos_productos": tipos_productos,
                    "cupos_totales": total_cupos
                })
                messages.success(request, "Feria creada correctamente")
                return redirect("admin_panel")

        # --- APROBAR SOLICITUD ---
        elif "aprobar_solicitud" in request.POST:
            sid = int(request.POST.get("aprobar_solicitud"))
            data = utils.load_data()
            solicitudes = data.get("solicitudes", [])
            s = next((x for x in solicitudes if x["id"] == sid), None)
            if not s:
                messages.error(request, "La solicitud no existe.")
                return redirect("admin_panel")

            if s.get("estado") == "aceptado":
                messages.info(request, "La solicitud ya estaba aceptada.")
                return redirect("admin_panel")

            # Validar cupos usando tu helper existente
            try:
                utils.add_artesano({
                    "nombre": s["nombre"],
                    "tipo": s["tipo"],
                    "descripcion": s["descripcion"],
                    "feria_id": s["feria_id"],
                })
                s["estado"] = "aceptado"
                utils.save_data(data)
                messages.success(request, "Solicitud aprobada y artesano agregado a la feria.")
            except ValueError:
                messages.error(request, "No hay cupos disponibles para esa categoría.")
            return redirect("admin_panel")

        # --- RECHAZAR SOLICITUD ---
        elif "rechazar_solicitud" in request.POST:
            sid = int(request.POST.get("rechazar_solicitud"))
            data = utils.load_data()
            solicitudes = data.get("solicitudes", [])
            for x in solicitudes:
                if x["id"] == sid:
                    x["estado"] = "rechazado"
                    break
            utils.save_data(data)
            messages.info(request, "Solicitud rechazada.")
            return redirect("admin_panel")
        # --- ELIMINAR USUARIO ---
        elif "eliminar_usuario" in request.POST:
            uid = int(request.POST.get("eliminar_usuario"))
            target = get_object_or_404(User, pk=uid)

            if request.user.id == target.id:
                messages.error(request, "No puedes eliminar tu propia cuenta.")
                return redirect("admin_panel")

            if target.role == "admin" and User.objects.filter(role="admin").count() <= 1:
                messages.error(request, "No puedes eliminar al último administrador.")
                return redirect("admin_panel")

            username = target.username
            target.delete()

            # Limpia sus solicitudes del JSON (por user_id o, si hay viejas, por username)
            data = utils.load_data()
            data["solicitudes"] = [
                s for s in data.get("solicitudes", [])
                if s.get("user_id") != uid and s.get("usuario") != username
            ]
            utils.save_data(data)

            messages.success(request, "Usuario eliminado.")
            return redirect("admin_panel")


        # Eliminar feria
        elif "eliminar_feria" in request.POST:
            feria_id = request.POST.get("eliminar_feria")
            utils.delete_feria(feria_id)
            return redirect("admin_panel")

        # Editar feria
        elif "editar_feria" in request.POST:
            feria_id = request.POST.get("feria_id")
            feria_form = FeriaForm(request.POST)
            if feria_form.is_valid():
                utils.edit_feria(feria_id, {
                    "nombre": request.POST.get("nombre"),
                    "fecha_inicio": request.POST.get("fecha_inicio"),
                    "fecha_fin": request.POST.get("fecha_fin"),
                    "preferencias": feria_form.cleaned_data["preferencias"],
                })
            return redirect("admin_panel")
    
    # --------- GET: construir contexto ---------
    data = utils.load_data()
    users = User.objects.all().order_by("-date_joined")
    ferias = data.get("ferias", [])
    artesanos = data.get("artesanos", [])
    solicitudes = data.get("solicitudes", [])

    # Formularios
    feria_form = FeriaForm()
    artesano_form = ArtesanoForm()  # legacy (lo dejamos visible si quieres mantenerlo)
    tipo_formset = TipoProductoFormSet(prefix="tipos")

    # Ferias con detalles (recalcular ocupados)
    ferias_detalles = []
    ferias_disponibles = []
    for f in ferias:
        total_cupos = sum(tp.get("cupos", 0) for tp in f.get("tipos_productos", []))
        if total_cupos == 0:
            total_cupos = f.get("cupos_totales") or f.get("cupos") or 0

        ocupados = sum(1 for a in artesanos if a.get("feria_id") == f.get("id"))

        artesanos_feria = [a for a in artesanos if a.get("feria_id") == f.get("id")]
        tipos_info = []
        for tp in f.get("tipos_productos", []):
            ocupados_tipo = sum(
                1 for a in artesanos if a.get("feria_id") == f.get("id") and a.get("tipo") == tp.get("tipo")
            )
            tipos_info.append({
                "tipo": tp.get("tipo"),
                "cupos": tp.get("cupos"),
                "ocupados": ocupados_tipo
            })
        ferias_detalles.append({
            "id": f.get("id"),
            "nombre": f.get("nombre", f"Feria {f.get('id')}"),
            "fecha_inicio": f.get("fecha_inicio", ""),
            "fecha_fin": f.get("fecha_fin", ""),
            "ocupados": ocupados,
            "total_cupos": total_cupos,
            "preferencias": f.get("preferencias", ""),
            "tipos": tipos_info,
            "artesanos": artesanos_feria
        })

        ferias_disponibles.append(
            (f.get("id"), f"{f.get('nombre', f'Feria {f.get('id')}')} ({ocupados}/{total_cupos} cupos)")
        )

    # Datos para el JS de tipos por feria
    ferias_tipos = {}
    for f in ferias:
        fid = str(f.get("id"))
        tipos_info = []
        for tp in f.get("tipos_productos", []):
            ocupados_tipo = sum(1 for a in artesanos if a.get("feria_id") == f.get("id") and a.get("tipo") == tp.get("tipo"))
            tipos_info.append({
                "tipo": tp.get("tipo"),
                "cupos": tp.get("cupos"),
                "ocupados": ocupados_tipo
            })
        ferias_tipos[fid] = tipos_info

    return render(request, "admin/admin_panel.html", {
        "ferias": ferias_detalles,
        "artesanos": artesanos,
        "feria_form": feria_form,
        "artesano_form": artesano_form,  # opcional
        "tipo_formset": tipo_formset,
        "ferias_disponibles": ferias_disponibles,
        "ferias_tipos_json": json.dumps(ferias_tipos),
        "solicitudes": solicitudes,  # 👈 para la pestaña de solicitudes
        "users": users,
    })

@login_required
def edit_user_view(request, user_id):
    if request.user.role != "admin":
        return redirect("user_panel" if request.user.role == "user" else "artesano_panel")

    target = get_object_or_404(User, pk=user_id)

    if request.method == "POST":
        form = UserEditForm(request.POST, instance=target)
        if form.is_valid():
            new_role = form.cleaned_data.get("role")
            # Evitar dejar al sistema sin administradores
            if target.role == "admin" and new_role != "admin" and User.objects.filter(role="admin").count() <= 1:
                form.add_error("role", "No puedes quitar el rol admin al último administrador.")
            else:
                form.save()
                messages.success(request, "Usuario actualizado.")
                return redirect("admin_panel")
    else:
        form = UserEditForm(instance=target)

    return render(request, "admin/edit_user.html", {"form": form, "target": target})

# =================== Otras vistas existentes ===================

def editar_feria(request, feria_id):
    data = utils.load_data()
    feria_id = int(feria_id)
    feria = next((f for f in data["ferias"] if f["id"] == feria_id), None)

    if not feria:
        messages.error(request, "La feria no existe.")
        return redirect("admin_panel")

    if request.method == "POST":
        feria["nombre"] = request.POST.get("nombre", "").strip()
        feria["fecha_inicio"] = request.POST.get("fecha_inicio")
        feria["fecha_fin"] = request.POST.get("fecha_fin")
        feria["preferencias"] = request.POST.get("preferencias", "")

        total_tipos = int(request.POST.get("tipos-TOTAL_FORMS", 0))
        nuevos_tipos = []
        for i in range(total_tipos):
            tipo = request.POST.get(f"tipos-{i}-tipo")
            cupos = request.POST.get(f"tipos-{i}-cupos")
            if tipo and cupos:
                nuevos_tipos.append({"tipo": tipo, "cupos": int(cupos)})

        feria["tipos_productos"] = nuevos_tipos
        feria["cupos_totales"] = sum(tp["cupos"] for tp in nuevos_tipos)

        utils.save_data(data)
        messages.success(request, "Feria actualizada correctamente")
        return redirect("admin_panel")

    return render(request, "admin/editar_feria.html", {
        "feria": feria,
        "tipos_productos": feria.get("tipos_productos", []),
    })


def public_view(request):
    data = utils.load_data()
    ferias = data.get("ferias", [])
    artesanos = data.get("artesanos", [])

    ferias_detalles = []
    ferias_dict = {}
    for f in ferias:
        total_cupos = sum(tp.get("cupos", 0) for tp in f.get("tipos_productos", []))
        if total_cupos == 0:
            total_cupos = f.get("cupos_totales") or f.get("cupos") or 0

        ocupados = sum(1 for a in artesanos if a.get("feria_id") == f.get("id"))

        tipos_info = []
        for tp in f.get("tipos_productos", []):
            ocupados_tipo = sum(
                1 for a in artesanos if a.get("feria_id") == f.get("id") and a.get("tipo") == tp.get("tipo")
            )
            tipos_info.append({
                "tipo": tp.get("tipo"),
                "cupos_totales": tp.get("cupos"),
                "ocupados": ocupados_tipo
            })

        feria_data = {
            "id": f.get("id"),
            "nombre": f.get("nombre", f"Feria {f.get('id')}"),
            "fecha_inicio": f.get("fecha_inicio", ""),
            "fecha_fin": f.get("fecha_fin", ""),
            "ocupados": ocupados,
            "total_cupos": total_cupos,
            "preferencias": f.get("preferencias", ""),
            "tipos": tipos_info
        }
        ferias_detalles.append(feria_data)
        ferias_dict[f.get("id")] = feria_data

    busqueda = request.GET.get("busqueda", "").strip().lower()
    artesanos_filtrados = []

    if busqueda:
        for a in artesanos:
            if busqueda in a.get("nombre", "").lower() or busqueda in a.get("tipo", "").lower():
                feria = ferias_dict.get(a.get("feria_id"))
                artesanos_filtrados.append({**a, "feria": feria})

    artesanos_por_feria = {}
    for a in artesanos:
        fid = a.get("feria_id")
        artesanos_por_feria.setdefault(fid, []).append(a)

    return render(request, "usuario_sin_registrar/public.html", {
        "ferias": ferias_detalles,
        "artesanos": artesanos,
        "busqueda": busqueda,
        "artesanos_filtrados": artesanos_filtrados,
        "artesanos_por_feria": json.dumps(artesanos_por_feria),
    })

@login_required
def delete_artesano_view(request, artesano_id):
    # Solo admin puede borrar
    if getattr(request.user, "role", "") != "admin":
        # redirige al panel correspondiente según rol
        return redirect('artesano_panel' if getattr(request.user, "role", "") == "artesano" else 'user_panel')
    utils.delete_artesano(artesano_id)
    return redirect('admin_panel')


@login_required
def edit_artesano_view(request, artesano_id):
    # Solo admin puede editar
    if getattr(request.user, "role", "") != "admin":
        return redirect('artesano_panel' if getattr(request.user, "role", "") == "artesano" else 'user_panel')

    data = utils.load_data()
    # Busca el artesano en tu JSON
    artesano = next((a for a in data.get("artesanos", []) if str(a.get("id")) == str(artesano_id)), None)
    if not artesano:
        messages.error(request, "El artesano no existe.")
        return redirect("admin_panel")

    if request.method == "POST":
        form = ArtesanoForm(request.POST)
        if form.is_valid():
            utils.edit_artesano(
                artesano_id,
                {
                    "nombre": form.cleaned_data["nombre"],
                    "tipo": form.cleaned_data["tipo"],
                    "descripcion": form.cleaned_data["descripcion"],
                    "feria_id": int(form.cleaned_data["feria_id"]),
                },
            )
            messages.success(request, "Artesano actualizado correctamente.")
            return redirect("admin_panel")
    else:
        # Carga datos iniciales en el form
        form = ArtesanoForm(initial={
            "nombre": artesano.get("nombre", ""),
            "descripcion": artesano.get("descripcion", ""),
            "feria_id": artesano.get("feria_id"),
            "tipo": artesano.get("tipo", ""),
        })

    return render(request, "admin/edit_artesano.html", {"form": form, "artesano": artesano})

from .forms import ArtesanoPerfilForm, ProductoFormSet
from .models import Artesano, Producto
from django import forms

class PerfilSimpleForm(forms.ModelForm):
    class Meta:
        model = Artesano
        fields = ['nombre', 'descripcion']

class ProductoSimpleForm(forms.ModelForm):
    class Meta:
        model = Producto
        fields = ['nombre', 'descripcion']

@login_required
def editar_perfil_artesano(request):
    artesano, _ = Artesano.objects.get_or_create(usuario=request.user)
    productos = Producto.objects.filter(artesano=artesano)
    ProductoFormSet = forms.modelformset_factory(Producto, form=ProductoSimpleForm, extra=0, can_delete=True)

    if request.method == 'POST':
        perfil_form = PerfilSimpleForm(request.POST, instance=artesano)
        productos_formset = ProductoFormSet(request.POST, queryset=productos)
        if perfil_form.is_valid() and productos_formset.is_valid():
            perfil_form.save()
            productos_formset.save()
            # Para agregar un producto nuevo
            nuevo_nombre = request.POST.get('nuevo_producto_nombre', '').strip()
            nuevo_desc = request.POST.get('nuevo_producto_desc', '').strip()
            if nuevo_nombre:
                Producto.objects.create(artesano=artesano, nombre=nuevo_nombre, descripcion=nuevo_desc)
            return redirect('artesano_panel')
    else:
        perfil_form = PerfilSimpleForm(instance=artesano)
        productos_formset = ProductoFormSet(queryset=productos)
    return render(request, 'usuario_registrado/editar_perfil_artesano.html', {
        'perfil_form': perfil_form,
        'productos_formset': productos_formset,
    })