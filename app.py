import streamlit as st
from pymongo import MongoClient
from pymongo.errors import ServerSelectionTimeoutError
from bson import ObjectId
from dotenv import load_dotenv
import os

load_dotenv()

# ─────────────────────────────────────────
#  Configuración de página
# ─────────────────────────────────────────
st.set_page_config(page_title="MongoDB CRUD Visual", page_icon="🍃", layout="wide")

# ─────────────────────────────────────────
#  Conexión — acepta cualquier URI
# ─────────────────────────────────────────
@st.cache_resource
def get_client(uri: str):
    return MongoClient(uri, serverSelectionTimeoutMS=4000)

def probar_conexion(client):
    try:
        client.admin.command("ping")
        return True
    except ServerSelectionTimeoutError:
        return False

# ─────────────────────────────────────────
#  Sidebar
# ─────────────────────────────────────────
with st.sidebar:
    st.title("🍃 MongoDB CRUD")

    # ── Modo de conexión ─────────────────
    st.header("1. Origen de datos")
    modo = st.radio(
        "¿Dónde corre MongoDB?",
        ["🐳 Local (Docker)", "☁️ Atlas (Nube)"],
        help="Cambia aquí para ver la diferencia entre una base de datos local y una en la nube"
    )

    if modo == "🐳 Local (Docker)":
        uri = os.getenv("MONGO_URI_LOCAL", "mongodb://localhost:27017")
        st.caption(f"`{uri}`")
        st.info(
            "MongoDB corre en un **contenedor Docker** en tu propia máquina.\n\n"
            "Los contenedores se hablan por nombre de servicio — "
            "por eso la URI dice `mongodb` y no `localhost`."
        )
    else:
        uri = os.getenv("MONGO_URI_ATLAS", "")
        if uri:
            partes = uri.split("@")
            uri_segura = "mongodb+srv://****:****@" + partes[-1] if len(partes) > 1 else "⚠️ sin configurar"
            st.caption(f"`{uri_segura}`")
        st.info(
            "MongoDB corre en **servidores de MongoDB Inc.** en la nube.\n\n"
            "Atlas gestiona replicación, backups y escalado por ti."
        )
        if not uri:
            st.error("Falta `MONGO_URI_ATLAS` en el archivo `.env`")

    # ── Estado de la conexión ────────────
    if uri:
        client = get_client(uri)
        conectado = probar_conexion(client)
        if conectado:
            st.success("Conectado")
        else:
            st.error("Sin conexión — revisa que el servicio esté corriendo")
            st.stop()
    else:
        st.stop()

    st.divider()

    # ── Selección de base de datos y colección ──
    st.header("2. Base de datos")
    dbs_existentes = [
        d for d in client.list_database_names()
        if d not in ("admin", "local", "config")
    ]

    nueva_db = st.text_input("Crear nueva", placeholder="mi_base_datos")
    if dbs_existentes:
        db_seleccionada = st.selectbox("O usar existente", [""] + dbs_existentes)
        nombre_db = nueva_db if nueva_db else db_seleccionada
    else:
        nombre_db = nueva_db

    st.header("3. Colección")
    nombre_coleccion = st.text_input("Nombre", placeholder="personas")

    st.divider()
    if nombre_db and nombre_coleccion:
        st.success(f"**DB:** {nombre_db}\n\n**Colección:** {nombre_coleccion}")
    else:
        st.warning("Completa los campos de arriba para continuar")

# ── Validar configuración ─────────────────
if not nombre_db or not nombre_coleccion:
    # Pantalla de bienvenida
    st.title("🍃 MongoDB CRUD Visual")

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("🐳 Con Docker")
        st.markdown("""
MongoDB corre como un **servicio contenedor** al lado de esta app.

```
┌─────────────────────────────┐
│     docker-compose.yml      │
│                             │
│  ┌──────────┐  ┌─────────┐  │
│  │   app    │→ │ mongodb │  │
│  │Streamlit │  │ mongo:7 │  │
│  └──────────┘  └────┬────┘  │
│                     │       │
│              mongo_data     │
│              (volumen)      │
└─────────────────────────────┘
```

**Comando:**
```bash
docker compose up --build
```

Los datos **persisten** en el volumen `mongo_data`
aunque hagas `docker compose down`.

Para borrar los datos:
```bash
docker compose down -v
```
        """)

    with col2:
        st.subheader("☁️ Con Atlas")
        st.markdown("""
MongoDB corre en la **nube de MongoDB Inc.**,
tú solo te conectas con un string de conexión.

```
Tu app                MongoDB Atlas
  │                        │
  │  mongodb+srv://...     │
  └───────────────────────►│
                      ┌────┴────┐
                      │Replica  │
                      │Set (x3) │
                      └─────────┘
```

**Diferencias clave:**

| | Docker local | Atlas |
|--|--|--|
| Dónde corre | Tu PC | Servidores MongoDB |
| Internet | No necesita | Sí |
| Escala | Manual | Automático |
| Backups | Tú configuras | Incluidos |
| Costo | Gratis | Free tier disponible |
        """)

    st.info("👈 Configura la conexión, base de datos y colección en el panel izquierdo.")
    st.stop()

db = client[nombre_db]
coleccion = db[nombre_coleccion]

# Banner del modo activo
modo_label = "🐳 Docker local" if "Local" in modo else "☁️ Atlas"
st.caption(f"Conectado a **{modo_label}** → `{nombre_db}` / `{nombre_coleccion}`")

# ─────────────────────────────────────────
#  Pestañas CRUD
# ─────────────────────────────────────────
tab_ver, tab_crear, tab_actualizar, tab_eliminar = st.tabs([
    "📋 Ver documentos",
    "➕ Crear documento",
    "✏️ Actualizar documento",
    "🗑️ Eliminar documento",
])


# ══════════════════════════════════════════
#  READ
# ══════════════════════════════════════════
with tab_ver:
    st.subheader("📋 Todos los documentos")

    col1, col2 = st.columns([3, 1])
    with col2:
        limite = st.number_input("Máximo", min_value=1, max_value=100, value=20)
        if st.button("🔄 Refrescar", use_container_width=True):
            st.rerun()

    documentos = list(coleccion.find().limit(limite))

    if documentos:
        total = coleccion.count_documents({})
        st.caption(f"Mostrando {len(documentos)} de {total} documentos totales")
        for doc in documentos:
            with st.expander(f"📄 `{doc['_id']}`"):
                datos = {k: str(v) if isinstance(v, ObjectId) else v for k, v in doc.items()}
                st.json(datos)
    else:
        st.info("Colección vacía. Crea tu primer documento en la pestaña ➕")

    with st.expander("💡 ¿Qué está pasando por detrás?"):
        st.code(f"""\
from pymongo import MongoClient

# La URI cambia según dónde corre MongoDB:
# Docker local → "mongodb://mongodb:27017"   (nombre del servicio)
# Atlas        → "mongodb+srv://user:pass@cluster..."

client = MongoClient("tu_uri")
db = client["{nombre_db}"]
coleccion = db["{nombre_coleccion}"]

# Leer todos los documentos
for doc in coleccion.find():
    print(doc)

# Leer con filtro
for doc in coleccion.find({{"ciudad": "Bogotá"}}):
    print(doc)
""", language="python")
        st.markdown("""\
**Conceptos:**
- `find()` sin argumentos → todos los documentos
- `find({"campo": "valor"})` → filtrado
- Cada documento tiene un `_id` (ObjectId) único, asignado por MongoDB
""")


# ══════════════════════════════════════════
#  CREATE
# ══════════════════════════════════════════
with tab_crear:
    st.subheader("➕ Insertar un nuevo documento")
    st.markdown("MongoDB es **schema-less** — cada documento puede tener campos distintos.")

    if "campos_crear" not in st.session_state:
        st.session_state.campos_crear = [{"clave": "", "valor": ""}]

    for i, campo in enumerate(st.session_state.campos_crear):
        c1, c2, c3 = st.columns([2, 3, 1])
        with c1:
            st.session_state.campos_crear[i]["clave"] = st.text_input(
                "Campo", value=campo["clave"], key=f"ck_{i}", placeholder="nombre"
            )
        with c2:
            st.session_state.campos_crear[i]["valor"] = st.text_input(
                "Valor", value=campo["valor"], key=f"cv_{i}", placeholder="Juan"
            )
        with c3:
            if i > 0 and st.button("✕", key=f"cd_{i}"):
                st.session_state.campos_crear.pop(i)
                st.rerun()

    if st.button("+ Agregar campo"):
        st.session_state.campos_crear.append({"clave": "", "valor": ""})
        st.rerun()

    st.divider()

    if st.button("💾 Insertar documento", type="primary", use_container_width=True):
        doc_nuevo = {
            c["clave"]: c["valor"]
            for c in st.session_state.campos_crear
            if c["clave"].strip()
        }
        if doc_nuevo:
            resultado = coleccion.insert_one(doc_nuevo)
            st.success(f"✅ Insertado con `_id`: `{resultado.inserted_id}`")
            st.session_state.campos_crear = [{"clave": "", "valor": ""}]
            st.rerun()
        else:
            st.warning("Agrega al menos un campo.")

    with st.expander("💡 ¿Qué está pasando por detrás?"):
        st.code("""\
# Insertar un documento
resultado = coleccion.insert_one({
    "nombre": "Juan",
    "edad": 25,
    "ciudad": "Bogotá"
})
print("_id asignado:", resultado.inserted_id)

# Insertar varios de una vez
coleccion.insert_many([
    {"nombre": "Ana", "edad": 30},
    {"nombre": "Luis", "edad": 22},
])
""", language="python")
        st.markdown("""\
**Conceptos:**
- `insert_one()` → un documento
- `insert_many()` → lista de documentos
- MongoDB asigna `_id` automáticamente (puedes pasarlo tú también)
- No hay esquema fijo — cada documento puede tener campos distintos
""")


# ══════════════════════════════════════════
#  UPDATE
# ══════════════════════════════════════════
with tab_actualizar:
    st.subheader("✏️ Actualizar un documento")

    documentos_lista = list(coleccion.find().limit(50))

    if not documentos_lista:
        st.info("No hay documentos. ¡Crea uno primero!")
    else:
        opciones = {str(d["_id"]): d for d in documentos_lista}
        id_sel = st.selectbox("Selecciona documento", list(opciones.keys()),
                              format_func=lambda x: f"ID: {x}")
        doc_actual = opciones[id_sel]

        st.markdown("**Documento actual:**")
        st.json({k: str(v) if isinstance(v, ObjectId) else v for k, v in doc_actual.items()})

        st.markdown("**Editar campos:**")
        nuevos_valores = {}
        for campo, valor in doc_actual.items():
            if campo == "_id":
                continue
            nuevos_valores[campo] = st.text_input(f"`{campo}`", value=str(valor), key=f"upd_{campo}")

        nuevo_campo = st.text_input("Agregar nuevo campo (opcional)", placeholder="telefono")
        nuevo_valor = st.text_input("Valor", placeholder="300-000-0000")
        if nuevo_campo:
            nuevos_valores[nuevo_campo] = nuevo_valor

        if st.button("💾 Guardar cambios", type="primary", use_container_width=True):
            coleccion.update_one({"_id": ObjectId(id_sel)}, {"$set": nuevos_valores})
            st.success("✅ Documento actualizado")
            st.rerun()

    with st.expander("💡 ¿Qué está pasando por detrás?"):
        st.code("""\
from bson import ObjectId

coleccion.update_one(
    {"_id": ObjectId("el_id")},   # filtro: cuál actualizar
    {"$set": {"nombre": "Juan Carlos", "edad": 26}}  # qué cambiar
)

# $set solo toca los campos indicados, el resto queda igual
""", language="python")
        st.markdown("""\
| Operador | Efecto |
|----------|--------|
| `$set` | Cambia el valor de un campo |
| `$unset` | Elimina un campo |
| `$inc` | Incrementa un número |
| `$push` | Agrega elemento a un array |
""")


# ══════════════════════════════════════════
#  DELETE
# ══════════════════════════════════════════
with tab_eliminar:
    st.subheader("🗑️ Eliminar un documento")

    documentos_lista = list(coleccion.find().limit(50))

    if not documentos_lista:
        st.info("No hay documentos para eliminar.")
    else:
        opciones = {str(d["_id"]): d for d in documentos_lista}
        id_del = st.selectbox("Selecciona documento", list(opciones.keys()),
                              format_func=lambda x: f"ID: {x}")

        st.markdown("**Documento que se eliminará:**")
        st.json({k: str(v) if isinstance(v, ObjectId) else v for k, v in opciones[id_del].items()})

        st.warning("⚠️ Esta acción no se puede deshacer.")
        confirmar = st.checkbox("Confirmo que quiero eliminar este documento")

        if st.button("🗑️ Eliminar", type="primary", disabled=not confirmar, use_container_width=True):
            coleccion.delete_one({"_id": ObjectId(id_del)})
            st.success("✅ Eliminado")
            st.rerun()

    st.divider()
    st.subheader("🧹 Vaciar toda la colección")
    confirmar_todo = st.checkbox("Confirmo que quiero eliminar TODOS los documentos")
    if st.button("Vaciar colección", disabled=not confirmar_todo):
        resultado = coleccion.delete_many({})
        st.success(f"✅ {resultado.deleted_count} documentos eliminados")
        st.rerun()

    with st.expander("💡 ¿Qué está pasando por detrás?"):
        st.code("""\
from bson import ObjectId

# Eliminar uno por ID
coleccion.delete_one({"_id": ObjectId("el_id")})

# Eliminar todos los que cumplan una condición
coleccion.delete_many({"ciudad": "Bogotá"})

# Eliminar absolutamente todos
coleccion.delete_many({})
""", language="python")
        st.markdown("""\
**Diferencia:**
- `delete_one()` → borra el primero que coincida
- `delete_many()` → borra todos los que coincidan
- `collection.drop()` → elimina la colección entera con sus índices
""")
