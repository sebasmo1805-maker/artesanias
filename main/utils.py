# main/utils.py
import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data/ferias.json")


# -------------------- IO --------------------

def _ensure_file():
    """Crea el JSON si no existe, con llaves base."""
    if not os.path.exists(DATA_FILE):
        os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
        with open(DATA_FILE, "w", encoding="utf-8") as f:
            json.dump({"ferias": [], "artesanos": [], "solicitudes": []}, f, indent=4, ensure_ascii=False)


def load_data():
    _ensure_file()
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        data = json.load(f)
    # llaves seguras
    data.setdefault("ferias", [])
    data.setdefault("artesanos", [])
    data.setdefault("solicitudes", [])
    return data


def save_data(data):
    os.makedirs(os.path.dirname(DATA_FILE), exist_ok=True)
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)


# -------------------- Ferias --------------------

def add_feria(feria):
    data = load_data()

    # Generar ID único
    next_id = max((f.get("id", 0) for f in data["ferias"]), default=0) + 1
    feria["id"] = next_id

    # Sanitizar nombre
    feria["nombre"] = (feria.get("nombre") or "").strip()

    # Asegurar estructura de tipos
    tipos = feria.get("tipos_productos", []) or []
    for tp in tipos:
        tp["tipo"] = (tp.get("tipo") or "").strip()
        tp["cupos"] = int(tp.get("cupos") or 0)

    feria["tipos_productos"] = tipos
    feria["cupos_totales"] = sum(tp.get("cupos", 0) for tp in tipos)
    feria["ocupados"] = 0

    data["ferias"].append(feria)
    save_data(data)


def delete_feria(feria_id):
    data = load_data()
    feria_id = int(feria_id)

    # eliminar feria
    data["ferias"] = [f for f in data["ferias"] if int(f.get("id")) != feria_id]

    # eliminar artesanos y solicitudes asociadas
    data["artesanos"] = [a for a in data["artesanos"] if int(a.get("feria_id", -1)) != feria_id]
    data["solicitudes"] = [s for s in data["solicitudes"] if int(s.get("feria_id", -1)) != feria_id]

    save_data(data)


def edit_feria(feria_id, new_data):
    data = load_data()
    feria_id = int(feria_id)

    for f in data["ferias"]:
        if int(f.get("id")) == feria_id:
            f.update(new_data or {})
            # Normalizar tipos si vinieron
            if "tipos_productos" in (new_data or {}):
                tipos = f.get("tipos_productos", []) or []
                for tp in tipos:
                    tp["tipo"] = (tp.get("tipo") or "").strip()
                    tp["cupos"] = int(tp.get("cupos") or 0)
                f["tipos_productos"] = tipos
                f["cupos_totales"] = sum(tp.get("cupos", 0) for tp in tipos)
            break

    save_data(data)


# -------------------- Artesanos (aprobados) --------------------

def _cupos_disponibles_para_tipo(feria, tipo):
    """Devuelve (ocupados_tipo, cupos_tipo) para la feria y tipo dados."""
    data = load_data()
    cupos_tipo = 0
    for tp in feria.get("tipos_productos", []):
        if tp.get("tipo") == tipo:
            cupos_tipo = int(tp.get("cupos") or 0)
            break
    ocupados_tipo = sum(
        1 for a in data["artesanos"]
        if int(a.get("feria_id")) == int(feria["id"]) and a.get("tipo") == tipo
    )
    return ocupados_tipo, cupos_tipo


def add_artesano(artesano):
    """
    Se usa al APROBAR una solicitud.
    Valida cupos por tipo según la feria (no un tope fijo).
    """
    data = load_data()

    feria = next((f for f in data["ferias"] if int(f.get("id")) == int(artesano["feria_id"])), None)
    if not feria:
        raise ValueError("Feria no encontrada")

    tipo = artesano.get("tipo")
    # verificar que el tipo exista en la feria
    if not any(tp.get("tipo") == tipo for tp in feria.get("tipos_productos", [])):
        raise ValueError("Tipo no disponible en esta feria")

    ocupados_tipo, cupos_tipo = _cupos_disponibles_para_tipo(feria, tipo)
    if cupos_tipo == 0 or ocupados_tipo >= cupos_tipo:
        raise ValueError("¡Máximo de artesanos alcanzado para esta categoría!")

    # Asignar ID incremental real
    next_id = max((a.get("id", 0) for a in data["artesanos"]), default=0) + 1
    nuevo = {
        "id": next_id,
        "nombre": artesano.get("nombre", "").strip(),
        "tipo": tipo,
        "descripcion": artesano.get("descripcion", "").strip(),
        "feria_id": int(artesano["feria_id"]),
    }
    data["artesanos"].append(nuevo)

    # Recalcular ocupados de la feria
    feria["ocupados"] = sum(1 for a in data["artesanos"] if int(a.get("feria_id")) == int(feria["id"]))

    save_data(data)


def delete_artesano(artesano_id):
    data = load_data()
    artesano_id = int(artesano_id)

    data["artesanos"] = [a for a in data["artesanos"] if int(a.get("id")) != artesano_id]

    # actualizar ocupados por feria
    for feria in data["ferias"]:
        feria["ocupados"] = sum(1 for a in data["artesanos"] if int(a.get("feria_id")) == int(feria["id"]))

    save_data(data)


def edit_artesano(artesano_id, new_data):
    data = load_data()
    artesano_id = int(artesano_id)

    for a in data["artesanos"]:
        if int(a.get("id")) == artesano_id:
            a.update(new_data or {})
            break

    # actualizar ocupados por feria
    for feria in data["ferias"]:
        feria["ocupados"] = sum(1 for a in data["artesanos"] if int(a.get("feria_id")) == int(feria["id"]))

    save_data(data)


# -------------------- Solicitudes --------------------

def add_solicitud(solicitud):
    """
    Crea una solicitud con estado='pendiente'.
    Estructura mínima:
    {
        "usuario": "...",
        "nombre": "...",
        "descripcion": "...",
        "feria_id": 1,
        "tipo": "cerámica"
    }
    """
    data = load_data()
    next_id = max((s.get("id", 0) for s in data["solicitudes"]), default=0) + 1
    solicitud_out = {
        "id": next_id,
        "usuario": solicitud.get("usuario", ""),
        "nombre": solicitud.get("nombre", "").strip(),
        "descripcion": solicitud.get("descripcion", "").strip(),
        "feria_id": int(solicitud.get("feria_id")),
        "tipo": solicitud.get("tipo"),
        "estado": "pendiente",
    }
    data["solicitudes"].append(solicitud_out)
    save_data(data)
    return solicitud_out


def set_estado_solicitud(solicitud_id, estado):
    data = load_data()
    solicitud_id = int(solicitud_id)
    for s in data["solicitudes"]:
        if int(s.get("id")) == solicitud_id:
            s["estado"] = estado
            break
    save_data(data)


def aprobar_solicitud(solicitud_id):
    """Aprueba (valida cupos y agrega a artesanos); setea estado='aceptado'."""
    data = load_data()
    s = next((x for x in data["solicitudes"] if int(x.get("id")) == int(solicitud_id)), None)
    if not s:
        raise ValueError("Solicitud no encontrada")

    if s.get("estado") == "aceptado":
        return  # ya estaba aceptada

    # Intentar agregar como artesano (puede lanzar ValueError si no hay cupos)
    add_artesano({
        "nombre": s["nombre"],
        "tipo": s["tipo"],
        "descripcion": s["descripcion"],
        "feria_id": s["feria_id"],
    })

    s["estado"] = "aceptado"
    save_data(data)


def rechazar_solicitud(solicitud_id):
    set_estado_solicitud(solicitud_id, "rechazado")


# -------------------- Utilidades para vistas --------------------

def ferias_tipos_map():
    """
    Devuelve { "feria_id_str": ["tipo1","tipo2", ...], ... }
    Útil para poblar el <select> de tipos en el panel del artesano vía JS.
    """
    data = load_data()
    mapa = {}
    for f in data["ferias"]:
        fid = str(f.get("id"))
        mapa[fid] = [tp.get("tipo") for tp in f.get("tipos_productos", [])]
    return mapa
