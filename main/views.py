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
from .forms import RegisterForm, LoginForm, FeriaForm, ArtesanoForm, TipoProductoFormSet
import json

# Vista de registro
def register_view(request):
    if request.method == 'POST':
        form = RegisterForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            user.set_password(form.cleaned_data['password'])
            user.role = 'user'  # todos los que se registran por defecto son usuarios
            user.save()
            return redirect('login')
    else:
        form = RegisterForm()
    return render(request, 'usuario_sin_registrar/register.html', {'form': form})


# Vista de login
def login_view(request):
    # Crear usuario admin automáticamente si no existe
    if not CustomUser.objects.filter(username='admin').exists():
        CustomUser.objects.create_superuser(
            username='admin',
            password='admin',
            role='admin'
        )

    if request.method == 'POST':
        form = LoginForm(request, data=request.POST)
        if form.is_valid():
            user = form.get_user()
            login(request, user)
            if user.role == 'admin':
                return redirect('admin_panel')
            else:
                return redirect('user_panel')
    else:
        form = LoginForm()
    return render(request, 'usuario_sin_registrar/login.html', {'form': form})


# Panel de usuario normal
@login_required
def user_panel(request):
    if request.user.role != 'user':
        return redirect('admin_panel')
    return render(request, 'usuario_registrado/user_panel.html')


@login_required
def admin_panel(request):
    if request.user.role != 'admin':
        return redirect('user_panel')

    # Manejo de POST (crear feria / crear artesano / etc.)
    if request.method == "POST":
        # NOTE: mantén tu lógica actual de POST (la copié abajo para no romper nada)
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
                        if tipo and cupos:
                            tipos_productos.append({"tipo": tipo, "cupos": cupos})
                            total_cupos += cupos

                utils.add_feria({
                    "nombre": request.POST.get("nombre"),   # 🔹 Nombre de la feria
                    "fecha_inicio": request.POST.get("fecha_inicio"),
                    "fecha_fin": request.POST.get("fecha_fin"),
                    "preferencias": feria_form.cleaned_data["preferencias"],
                    "ocupados": 0,
                    "tipos_productos": tipos_productos,
                    "cupos_totales": total_cupos
                })
                messages.success(request, "Feria creada correctamente")
                return redirect("admin_panel")





        elif "crear_artesano" in request.POST:
            artesano_form = ArtesanoForm(request.POST)
            if artesano_form.is_valid():
                try:
                    utils.add_artesano({
                        "nombre": artesano_form.cleaned_data["nombre"],
                        "tipo": artesano_form.cleaned_data["tipo"],
                        "descripcion": artesano_form.cleaned_data["descripcion"],
                        "feria_id": artesano_form.cleaned_data["feria_id"],
                    })
                    messages.success(request, "Artesano agregado correctamente.")
                except ValueError:
                    messages.error(request, "¡Máximo de artesanos alcanzado para esta categoría!")
                return redirect("admin_panel")

        elif "eliminar_artesano" in request.POST:
            artesano_id = request.POST.get("eliminar_artesano")
            utils.delete_artesano(artesano_id)
            return redirect("admin_panel")

        elif "editar_artesano" in request.POST:
            artesano_id = request.POST.get("artesano_id")
            artesano_form = ArtesanoForm(request.POST)
            if artesano_form.is_valid():
                utils.edit_artesano(artesano_id, {
                    "nombre": artesano_form.cleaned_data["nombre"],
                    "tipo": artesano_form.cleaned_data["tipo"],
                    "descripcion": artesano_form.cleaned_data["descripcion"],
                    "feria_id": artesano_form.cleaned_data["feria_id"],
                })
            return redirect("admin_panel")

        elif "eliminar_feria" in request.POST:
            feria_id = request.POST.get("eliminar_feria")
            utils.delete_feria(feria_id)
            return redirect("admin_panel")

        elif "editar_feria" in request.POST:
            feria_id = request.POST.get("feria_id")
            feria_form = FeriaForm(request.POST)
            if feria_form.is_valid():
                utils.edit_feria(feria_id, {
                    "nombre": request.POST.get("nombre"),   # 🔹 Nombre
                    "fecha_inicio": request.POST.get("fecha_inicio"),
                    "fecha_fin": request.POST.get("fecha_fin"),
                    "preferencias": feria_form.cleaned_data["preferencias"],
                })
            return redirect("admin_panel")

    # ========== GET y preparación del contexto ==========
    data = utils.load_data()
    ferias = data.get("ferias", [])
    artesanos = data.get("artesanos", [])

    # Formularios para el template
    feria_form = FeriaForm()
    artesano_form = ArtesanoForm()
    tipo_formset = TipoProductoFormSet(prefix="tipos")

    # Construir ferias_detalles con total_cupos y ocupados correctos
    ferias_detalles = []
    ferias_disponibles = []
    for f in ferias:
        # total_cupos: suma de cupos por tipo (si no hay tipos, fallback a cupos_totales o cupos)
        total_cupos = sum(tp.get("cupos", 0) for tp in f.get("tipos_productos", []))
        if total_cupos == 0:
            total_cupos = f.get("cupos_totales") or f.get("cupos") or 0

        # ocupados: recalculamos desde la lista de artesanos (más fiable)
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
            "artesanos": artesanos_feria   # 👈
        })



        ferias_disponibles.append(
            (f.get("id"), f"{f.get('nombre', f'Feria {f.get("id")}')} ({ocupados}/{total_cupos} cupos)")
        )


    # Construir ferias_tipos con ocupados por tipo (para el JS)
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
        "ferias": ferias_detalles,               # lo que usará tu template
        "artesanos": artesanos,
        "feria_form": feria_form,
        "artesano_form": artesano_form,
        "tipo_formset": tipo_formset,
        "ferias_disponibles": ferias_disponibles,
        "ferias_tipos_json": json.dumps(ferias_tipos),
    })



def editar_feria(request, feria_id):
    data = utils.load_data()
    feria_id = int(feria_id)

    feria = next((f for f in data["ferias"] if f["id"] == feria_id), None)

    if not feria:
        messages.error(request, "La feria no existe.")
        return redirect("admin_panel")

    if request.method == "POST":
        # Actualizar campos simples
        feria["nombre"] = request.POST.get("nombre", "").strip()
        feria["fecha_inicio"] = request.POST.get("fecha_inicio")
        feria["fecha_fin"] = request.POST.get("fecha_fin")
        feria["preferencias"] = request.POST.get("preferencias", "")

        # Leer tipos dinámicos
        total_tipos = int(request.POST.get("tipos-TOTAL_FORMS", 0))
        nuevos_tipos = []
        for i in range(total_tipos):
            tipo = request.POST.get(f"tipos-{i}-tipo")
            cupos = request.POST.get(f"tipos-{i}-cupos")

            if tipo and cupos:
                nuevos_tipos.append({
                    "tipo": tipo,
                    "cupos": int(cupos),
                })

        feria["tipos_productos"] = nuevos_tipos
        feria["cupos_totales"] = sum(tp["cupos"] for tp in nuevos_tipos)

        utils.save_data(data)
        messages.success(request, "Feria actualizada correctamente")
        return redirect("admin_panel")

    return render(request, "admin/editar_feria.html", {
        "feria": feria,
        "tipos_productos": feria.get("tipos_productos", []),
    })









# Logout
def logout_view(request):
    logout(request)
    return redirect('login')


def public_view(request):
    data = utils.load_data()
    ferias = data.get("ferias", [])
    artesanos = data.get("artesanos", [])
    # --- Construcción de ferias con detalles ---
    ferias_detalles = []
    ferias_dict = {}  # 👈 para mapear feria_id → datos de feria
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
        ferias_dict[f.get("id")] = feria_data  # 👈 guardamos para lookup rápido

    # --- Búsqueda ---
    busqueda = request.GET.get("busqueda", "").strip().lower()
    artesanos_filtrados = []

    if busqueda:
        for a in artesanos:
            if busqueda in a.get("nombre", "").lower() or busqueda in a.get("tipo", "").lower():
                feria = ferias_dict.get(a.get("feria_id"))
                artesanos_filtrados.append({
                    **a,
                    "feria": feria  # 👈 ahora cada artesano tiene su feria asociada
                })
    artesanos_por_feria = {}
    for a in artesanos:
        fid = a.get("feria_id")
        if fid not in artesanos_por_feria:
            artesanos_por_feria[fid] = []
        artesanos_por_feria[fid].append(a)

    return render(request, "usuario_sin_registrar/public.html", {
        "ferias": ferias_detalles,
        "artesanos": artesanos,
        "busqueda": busqueda,
        "artesanos_filtrados": artesanos_filtrados,
        "artesanos_por_feria": json.dumps(artesanos_por_feria),
    })




@login_required
def delete_artesano_view(request, artesano_id):
    if request.user.role != 'admin':
        return redirect('user_panel')
    utils.delete_artesano(artesano_id)
    return HttpResponseRedirect(reverse('admin_panel'))

@login_required
def edit_artesano_view(request, artesano_id):
    if request.user.role != 'admin':
        return redirect('user_panel')

    data = utils.load_data()
    artesano = next((a for a in data["artesanos"] if a["id"] == artesano_id), None)

    if not artesano:
        return redirect("admin_panel")

    if request.method == "POST":
        form = ArtesanoForm(request.POST)
        if form.is_valid():
            utils.edit_artesano(artesano_id, {
                "nombre": form.cleaned_data["nombre"],
                "tipo": form.cleaned_data["tipo"],
                "descripcion": form.cleaned_data["descripcion"],
                "feria_id": int(form.cleaned_data["feria_id"])  # 👈 Asegurar que sea int
            })
            return redirect("admin_panel")
    else:
        form = ArtesanoForm(initial=artesano)

    return render(request, "admin/edit_artesano.html", {"form": form, "artesano": artesano})