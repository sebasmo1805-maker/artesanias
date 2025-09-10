import json, os

DATA_FILE = os.path.join(os.path.dirname(__file__), "data/ferias.json")

def load_data():
    with open(DATA_FILE, "r", encoding="utf-8") as f:
        return json.load(f)

def save_data(data):
    with open(DATA_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=4, ensure_ascii=False)

def add_feria(feria):
    data = load_data()

    if "ferias" not in data:
        data["ferias"] = []
    if "artesanos" not in data:
        data["artesanos"] = []

    # Generar ID único
    feria["id"] = max((f["id"] for f in data["ferias"]), default=0) + 1

    # Nombre obligatorio (si no se manda, queda vacío en vez de None)
    feria["nombre"] = feria.get("nombre", "").strip()

    feria["ocupados"] = 0
    feria["cupos_totales"] = sum(tp.get("cupos", 0) for tp in feria.get("tipos_productos", []))

    data["ferias"].append(feria)
    save_data(data)






def delete_feria(feria_id):
    data = load_data()
    feria_id = int(feria_id)  # asegurar que sea int

    # eliminar la feria
    data["ferias"] = [f for f in data["ferias"] if f["id"] != feria_id]

    # también eliminamos artesanos asociados a esa feria
    data["artesanos"] = [a for a in data["artesanos"] if a["feria_id"] != feria_id]

    save_data(data)


def edit_feria(feria_id, new_data):
    data = load_data()
    feria_id = int(feria_id)

    for f in data["ferias"]:
        if f["id"] == feria_id:
            f.update(new_data)
            break

    save_data(data)

def add_artesano(artesano):
    data = load_data()
    artesano["feria_id"] = int(artesano["feria_id"])
    artesano["id"] = len(data["artesanos"]) + 1

    # Validar máximo 8 por tipo
    count_tipo = sum(
        1 for a in data["artesanos"]
        if a["feria_id"] == artesano["feria_id"] and a["tipo"] == artesano["tipo"]
    )
    if count_tipo >= 8:
        raise ValueError("Ya hay 8 artesanos de este tipo en esta feria.")

    # Agregar artesano
    data["artesanos"].append(artesano)

    # Recalcular cupos ocupados
    for feria in data["ferias"]:
        if feria["id"] == artesano["feria_id"]:
            feria["ocupados"] = sum(
                1 for a in data["artesanos"] if a["feria_id"] == feria["id"]
            )
            break

    save_data(data)



def delete_artesano(artesano_id):
    data = load_data()
    artesano_id = int(artesano_id)  # 🔑 conversión a número

    data["artesanos"] = [a for a in data["artesanos"] if a["id"] != artesano_id]

    # actualizar cupos ocupados en cada feria
    for feria in data["ferias"]:
        feria["ocupados"] = sum(1 for a in data["artesanos"] if a["feria_id"] == feria["id"])

    save_data(data)


def edit_artesano(artesano_id, new_data):
    data = load_data()
    for a in data["artesanos"]:
        if a["id"] == artesano_id:
            a.update(new_data)
            break

    # actualizar cupos ocupados
    for feria in data["ferias"]:
        feria["ocupados"] = sum(1 for a in data["artesanos"] if a["feria_id"] == feria["id"])

    save_data(data)

