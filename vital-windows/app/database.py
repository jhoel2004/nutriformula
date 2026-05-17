import sqlite3
import os
import json

from app.utils import resource_path

DB_PATH = resource_path(os.path.join('data', 'nutriformula.db'))

def get_connection():
    """Obtiene una conexión a la base de datos SQLite."""
    os.makedirs(os.path.dirname(DB_PATH), exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    conn.execute("PRAGMA foreign_keys = ON")
    return conn

# ══════════════════════════════════════════════════════════════════════
# Inicialización de la BD
# ══════════════════════════════════════════════════════════════════════
def init_db():
    """Inicializa la base de datos y crea las tablas necesarias."""
    try:
        conn = get_connection()
        cursor = conn.cursor()

        # ── Tabla animales ────────────────────────────────────────────
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS animales (
            id     INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL UNIQUE,
            icono  TEXT DEFAULT '🐾'
        )
        ''')

        # ── Tabla insumos ─────────────────────────────────────────────
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS insumos (
            id              INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre          TEXT NOT NULL UNIQUE,
            proteina        REAL,
            em_kcal         REAL,
            fibra           REAL,
            grasa           REAL,
            calcio          REAL,
            fosforo         REAL,
            lisina          REAL,
            metionina       REAL,
            colina_mgr      REAL,
            precio_kg       REAL DEFAULT 0,
            categoria       TEXT DEFAULT 'General',
            especies_compatibles TEXT DEFAULT '["Todos"]',
            activo          INTEGER DEFAULT 1
        )
        ''')

        # ── Migraciones ───────────────────────────────────────────────
        cursor.execute("PRAGMA table_info(insumos)")
        columns = [info[1] for info in cursor.fetchall()]
        if 'especies_compatibles' not in columns:
            cursor.execute("ALTER TABLE insumos ADD COLUMN especies_compatibles TEXT DEFAULT '[\"Todos\"]'")

        # ── Datos por defecto: Animales ───────────────────────────────
        cursor.execute('SELECT COUNT(*) FROM animales')
        if cursor.fetchone()[0] == 0:
            animales_default = [
                ('Gallinas Ponedoras',),
                ('Pollos de Engorde',),
                ('Cerdos',),
                ('Bovinos',),
                ('Ovinos/Caprinos',),
                ('Peces',),
                ('Mascotas',),
                ('Equinos',),
            ]
            cursor.executemany('INSERT INTO animales (nombre) VALUES (?)', animales_default)

        # ── Datos por defecto: Insumos ────────────────────────────────
        cursor.execute('SELECT COUNT(*) FROM insumos')
        if cursor.fetchone()[0] == 0:
            insumos_default = [
                ("harina maíz amarillo", 8.8, 3350, 1.8, 4.2, 0.03, 0.26, 0.20, 0.18, 496, 0, "Cereales"),
                ("chanca maíz amarillo", 8.8, 3300, 3.0, 4.0, 0.03, 0.26, 0.20, 0.15, 490, 0, "Cereales"),
                ("soya integral", 38.0, 3450, 6.0, 20.0, 0.25, 0.59, 2.40, 0.54, 2800, 0, "Proteínas"),
                ("torta de soya", 45.0, 2200, 6.5, 1.5, 0.30, 0.63, 2.68, 0.52, 2614, 0, "Proteínas"),
                ("palmiste", 15.0, 1600, 20.0, 9.0, 0.20, 0.59, 2.40, 0.50, 2600, 0, "Subproductos"),
                ("sorgo", 8.0, 3000, 7.5, 4.0, 0.03, 0.20, 0.20, 0.17, 450, 0, "Cereales"),
                ("afrecho de trigo", 15.0, 2000, 30.0, 3.0, 0.10, 1.02, 0.57, 0.33, 1000, 0, "Subproductos"),
                ("pasta de algodón", 30.0, 1600, 25.0, 4.0, 0.20, 0.30, 1.91, 0.73, 0, 0, "Proteínas"),
                ("arrocillo nielen", 9.0, 3350, 0.8, 1.8, 0.06, 0.28, 0.27, 0.16, 957, 0, "Subproductos"),
                ("polvo de arroz", 13.96, 2600, 8.0, 14.0, 0.70, 1.50, 0.52, 0.20, 1200, 0, "Subproductos"),
                ("harina de avena", 11.0, 3100, 3.0, 3.0, 0.80, 0.40, 0.53, 0.20, 1100, 0, "Cereales"),
                ("salvado de avena", 17.3, 2460, 15.0, 7.0, 0.80, 0.38, 0.50, 0.18, 990, 0, "Subproductos"),
                ("heno de avena molida", 3.0, 800, 50.0, 0.0, 0.00, 0.00, 0.00, 0.00, 0, 0, "Fibras"),
                ("gallinaza aves", 18.0, 2000, 35.0, 1.0, 0.05, 2.28, 0.05, 0.05, 600, 0, "Subproductos"),
                ("harina de carne", 60.0, 3050, 2.7, 2.5, 8.85, 4.44, 3.23, 0.70, 2041, 0, "Proteínas"),
                ("bagazo de caña azúcar", 2.1, 1450, 47.0, 0.7, 0.82, 0.27, 0.00, 0.00, 0, 0, "Fibras"),
                ("harina de cebada", 13.0, 2500, 4.0, 5.4, 0.04, 0.34, 0.39, 0.15, 1039, 0, "Cereales"),
                ("heno de cebada molida", 3.4, 800, 70.0, 0.0, 0.00, 0.00, 0.00, 0.00, 0, 0, "Fibras"),
                ("galleta molida", 10.4, 3600, 2.0, 4.0, 0.13, 0.24, 0.31, 0.17, 923, 0, "Subproductos"),
                ("aceite vegetal", 0.0, 7000, 0.0, 80.0, 0.00, 0.00, 0.00, 0.00, 0, 0, "Grasas"),
                ("melaza", 3.2, 1950, 0.0, 0.0, 0.75, 0.08, 0.00, 0.00, 750, 0, "Subproductos"),
                ("harina de pescado", 65.0, 3000, 1.0, 5.0, 3.75, 2.49, 5.00, 2.00, 3709, 0, "Proteínas"),
                ("harina de yuca", 2.3, 3330, 4.6, 0.0, 0.25, 0.17, 0.07, 0.03, 800, 0, "Subproductos"),
                ("harina alfalfa", 10.5, 2200, 30.0, 0.0, 0.10, 0.25, 0.08, 0.02, 100, 0, "Proteínas"),
                ("achiote", 14.5, 2460, 15.0, 7.0, 0.20, 0.30, 1.90, 0.70, 900, 0, "Aditivos"),
                ("harina de banana", 35.0, 3450, 8.0, 7.0, 0.23, 0.60, 0.10, 0.05, 0, 0, "Subproductos"),
            ]
            cursor.executemany('''
            INSERT INTO insumos (nombre, proteina, em_kcal, fibra, grasa, calcio, fosforo,
                                 lisina, metionina, colina_mgr, precio_kg, categoria, especies_compatibles)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, '["Todos"]')
            ''', insumos_default)

        conn.commit()
    except sqlite3.Error as e:
        print(f"Error inicializando la base de datos: {e}")
    finally:
        if conn:
            conn.close()
    # Ejecutar migraciones adicionales (idempotente)
    migrar_base_de_datos()

# ══════════════════════════════════════════════════════════════════════
# CRUD — Animales
# ══════════════════════════════════════════════════════════════════════
def get_all_animales():
    """Retorna lista de dicts {id, nombre, icono} de todos los animales."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT id, nombre, icono FROM animales ORDER BY nombre')
        return [dict(r) for r in cursor.fetchall()]
    except sqlite3.Error as e:
        print(f"Error obteniendo animales: {e}")
        return []
    finally:
        conn.close()

def insert_animal(data: dict) -> bool:
    try:
        conn = get_connection()
        conn.execute('INSERT INTO animales (nombre, icono) VALUES (:nombre, :icono)', data)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error insertando animal: {e}")
        return False
    finally:
        conn.close()

def update_animal(id_animal: int, data: dict) -> bool:
    try:
        conn = get_connection()
        conn.execute('UPDATE animales SET nombre=:nombre, icono=:icono WHERE id=:id',
                     {**data, 'id': id_animal})
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error actualizando animal: {e}")
        return False
    finally:
        conn.close()

def delete_animal(id_animal: int) -> bool:
    try:
        conn = get_connection()
        conn.execute('DELETE FROM animales WHERE id=?', (id_animal,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error eliminando animal: {e}")
        return False
    finally:
        conn.close()

# ══════════════════════════════════════════════════════════════════════
# CRUD — Insumos
# ══════════════════════════════════════════════════════════════════════
def get_all_insumos():
    """Retorna lista de dicts de todos los insumos activos."""
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()
        cursor.execute('SELECT * FROM insumos WHERE activo = 1 ORDER BY nombre')
        rows = cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            try:
                d['especies_compatibles'] = json.loads(d.get('especies_compatibles', '["Todos"]'))
            except Exception:
                d['especies_compatibles'] = ["Todos"]
            result.append(d)
        return result
    except sqlite3.Error as e:
        print(f"Error obteniendo insumos: {e}")
        return []
    finally:
        conn.close()

def insert_insumo(data: dict) -> bool:
    try:
        conn = get_connection()
        conn.execute('''
        INSERT INTO insumos (nombre, proteina, em_kcal, fibra, grasa, calcio, fosforo,
                             lisina, metionina, colina_mgr, precio_kg, categoria, especies_compatibles)
        VALUES (:nombre, :proteina, :em_kcal, :fibra, :grasa, :calcio, :fosforo,
                :lisina, :metionina, :colina_mgr, :precio_kg, :categoria, :especies_compatibles)
        ''', data)
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error insertando insumo: {e}")
        return False
    finally:
        conn.close()

def update_insumo(id_insumo: int, data: dict) -> bool:
    try:
        conn = get_connection()
        conn.execute('''
        UPDATE insumos
        SET nombre=:nombre, proteina=:proteina, em_kcal=:em_kcal, fibra=:fibra,
            grasa=:grasa, calcio=:calcio, fosforo=:fosforo, lisina=:lisina,
            metionina=:metionina, colina_mgr=:colina_mgr, precio_kg=:precio_kg,
            categoria=:categoria, especies_compatibles=:especies_compatibles
        WHERE id=:id
        ''', {**data, 'id': id_insumo})
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error actualizando insumo: {e}")
        return False
    finally:
        conn.close()

def delete_insumo(id_insumo: int) -> bool:
    try:
        conn = get_connection()
        conn.execute('UPDATE insumos SET activo=0 WHERE id=?', (id_insumo,))
        conn.commit()
        return True
    except sqlite3.Error as e:
        print(f"Error eliminando insumo: {e}")
        return False
    finally:
        conn.close()


# ══════════════════════════════════════════════════════════════════════
# Migración — eliminar especies_compatibles y agregar tablas de formulaciones
# ══════════════════════════════════════════════════════════════════════
def migrar_base_de_datos():
    """
    Ejecuta migraciones necesarias de forma segura (idempotente).
    Llama al iniciar la aplicación.
    """
    try:
        conn = get_connection()
        conn.row_factory = sqlite3.Row
        cursor = conn.cursor()

        # 1) Agregar tablas de formulaciones si no existen
        cursor.executescript("""
            CREATE TABLE IF NOT EXISTS formulaciones (
                id                        INTEGER PRIMARY KEY AUTOINCREMENT,
                nombre                    TEXT NOT NULL,
                fecha_creacion            TEXT NOT NULL,
                fecha_modificacion        TEXT NOT NULL,
                animal_id                 INTEGER,
                total_kg                  REAL NOT NULL DEFAULT 0,
                modo                      TEXT DEFAULT 'kilogramos',
                proteina_total            REAL DEFAULT 0,
                em_total                  REAL DEFAULT 0,
                fibra_total               REAL DEFAULT 0,
                grasa_total               REAL DEFAULT 0,
                calcio_total              REAL DEFAULT 0,
                fosforo_total             REAL DEFAULT 0,
                lisina_total              REAL DEFAULT 0,
                metionina_total           REAL DEFAULT 0,
                colina_total              REAL DEFAULT 0,
                costo_por_kg              REAL DEFAULT 0,
                costo_por_tonelada        REAL DEFAULT 0,
                instrucciones_preparacion TEXT DEFAULT '',
                notas_generales           TEXT DEFAULT '',
                tipo                      TEXT DEFAULT 'manual'
            );

            CREATE TABLE IF NOT EXISTS formulacion_ingredientes (
                id                  INTEGER PRIMARY KEY AUTOINCREMENT,
                formulacion_id      INTEGER NOT NULL,
                insumo_id           INTEGER NOT NULL,
                nombre_insumo       TEXT NOT NULL DEFAULT '',
                tanteo_kg           REAL NOT NULL DEFAULT 0,
                porcentaje          REAL NOT NULL DEFAULT 0,
                precio_kg           REAL DEFAULT 0,
                proteina_aportada   REAL DEFAULT 0,
                em_aportada         REAL DEFAULT 0,
                fibra_aportada      REAL DEFAULT 0,
                grasa_aportada      REAL DEFAULT 0,
                calcio_aportado     REAL DEFAULT 0,
                fosforo_aportado    REAL DEFAULT 0,
                lisina_aportada     REAL DEFAULT 0,
                metionina_aportada  REAL DEFAULT 0,
                colina_aportada     REAL DEFAULT 0,
                FOREIGN KEY (formulacion_id) REFERENCES formulaciones(id) ON DELETE CASCADE
            );

            CREATE INDEX IF NOT EXISTS idx_formulaciones_animal ON formulaciones(animal_id);
            CREATE INDEX IF NOT EXISTS idx_form_ingr_form       ON formulacion_ingredientes(formulacion_id);
        """)

        conn.commit()
        print("✓ Migración BD completada")
    except sqlite3.Error as e:
        print(f"Error en migración: {e}")
    finally:
        conn.close()# ══════════════════════════════════════════════════════════════════════
# GestorFormulacionesBD — Persistencia completa en SQLite
# ══════════════════════════════════════════════════════════════════════
class GestorFormulacionesBD:
    """Reemplaza el sistema de archivos .nfp. Toda la persistencia en SQLite."""

    def guardar_formulacion(self, datos):
        """
        Guarda una formulación completa con sus ingredientes.
        datos = {
          'nombre', 'animal_id', 'total_kg', 'tipo',
          'resultados_nutricionales': {'proteina_total', 'em_total', ...},
          'ingredientes': [{'insumo_id','nombre_insumo','tanteo_kg','porcentaje', ...}],
          'costo_por_kg', 'costo_por_tonelada',
          'instrucciones_preparacion', 'notas_generales'
        }
        Returns: int formulacion_id, or None on error
        """
        from datetime import datetime
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            ahora = datetime.now().isoformat()
            nuts = datos.get('resultados_nutricionales', {})

            cursor.execute("""
                INSERT INTO formulaciones (
                    nombre, fecha_creacion, fecha_modificacion,
                    animal_id, total_kg, modo,
                    proteina_total, em_total, fibra_total, grasa_total,
                    calcio_total, fosforo_total, lisina_total,
                    metionina_total, colina_total,
                    costo_por_kg, costo_por_tonelada,
                    instrucciones_preparacion, notas_generales, tipo
                ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
            """, (
                datos['nombre'], ahora, ahora,
                datos.get('animal_id'),
                datos.get('total_kg', 0), datos.get('modo', 'kilogramos'),
                nuts.get('proteina_total', 0), nuts.get('em_total', 0),
                nuts.get('fibra_total', 0), nuts.get('grasa_total', 0),
                nuts.get('calcio_total', 0), nuts.get('fosforo_total', 0),
                nuts.get('lisina_total', 0), nuts.get('metionina_total', 0),
                nuts.get('colina_total', 0),
                datos.get('costo_por_kg', 0), datos.get('costo_por_tonelada', 0),
                datos.get('instrucciones_preparacion', ''),
                datos.get('notas_generales', ''), datos.get('tipo', 'manual')
            ))
            fid = cursor.lastrowid

            for ing in datos.get('ingredientes', []):
                cursor.execute("""
                    INSERT INTO formulacion_ingredientes (
                        formulacion_id, insumo_id, nombre_insumo,
                        tanteo_kg, porcentaje, precio_kg,
                        proteina_aportada, em_aportada, fibra_aportada, grasa_aportada,
                        calcio_aportado, fosforo_aportado, lisina_aportada,
                        metionina_aportada, colina_aportada
                    ) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """, (
                    fid, ing.get('insumo_id', 0), ing.get('nombre_insumo', ''),
                    ing.get('tanteo_kg', 0), ing.get('porcentaje', 0),
                    ing.get('precio_kg', 0),
                    ing.get('proteina_aportada', 0), ing.get('em_aportada', 0),
                    ing.get('fibra_aportada', 0), ing.get('grasa_aportada', 0),
                    ing.get('calcio_aportado', 0), ing.get('fosforo_aportado', 0),
                    ing.get('lisina_aportada', 0), ing.get('metionina_aportada', 0),
                    ing.get('colina_aportada', 0),
                ))
            conn.commit()
            return fid
        except sqlite3.Error as e:
            print(f"Error guardando formulación: {e}")
            return None
        finally:
            conn.close()

    def cargar_formulacion(self, formulacion_id):
        """Carga formulación completa por ID. Returns dict or None."""
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM formulaciones WHERE id=?", (formulacion_id,))
            fila = cursor.fetchone()
            if not fila:
                return None
            fila = dict(fila)
            cursor.execute("""
                SELECT * FROM formulacion_ingredientes
                WHERE formulacion_id=? ORDER BY porcentaje DESC
            """, (formulacion_id,))
            ingredientes = [dict(r) for r in cursor.fetchall()]
            return {
                'id': fila['id'],
                'nombre': fila['nombre'],
                'fecha_creacion': fila['fecha_creacion'],
                'fecha_modificacion': fila['fecha_modificacion'],
                'animal_id': fila['animal_id'],
                'total_kg': fila['total_kg'],
                'modo': fila['modo'],
                'tipo': fila['tipo'],
                'resultados_nutricionales': {
                    'proteina_total': fila['proteina_total'],
                    'em_total': fila['em_total'],
                    'fibra_total': fila['fibra_total'],
                    'grasa_total': fila['grasa_total'],
                    'calcio_total': fila['calcio_total'],
                    'fosforo_total': fila['fosforo_total'],
                    'lisina_total': fila['lisina_total'],
                    'metionina_total': fila['metionina_total'],
                    'colina_total': fila['colina_total'],
                },
                'ingredientes': ingredientes,
                'costo_por_kg': fila['costo_por_kg'],
                'costo_por_tonelada': fila['costo_por_tonelada'],
                'instrucciones_preparacion': fila['instrucciones_preparacion'],
                'notas_generales': fila['notas_generales'],
            }
        except sqlite3.Error as e:
            print(f"Error cargando formulación: {e}")
            return None
        finally:
            conn.close()

    def listar_formulaciones(self, animal_id=None):
        """Lista formulaciones, opcionalmente filtradas por animal."""
        try:
            conn = get_connection()
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            sql = """
                SELECT f.*, a.nombre as animal_nombre
                FROM formulaciones f
                LEFT JOIN animales a ON f.animal_id = a.id
                WHERE 1=1
            """
            params = []
            if animal_id is not None:
                sql += " AND f.animal_id=?"
                params.append(animal_id)
            sql += " ORDER BY f.fecha_modificacion DESC"
            cursor.execute(sql, params)
            return [dict(r) for r in cursor.fetchall()]
        except sqlite3.Error as e:
            print(f"Error listando formulaciones: {e}")
            return []
        finally:
            conn.close()

    def eliminar_formulacion(self, formulacion_id):
        """Elimina formulación y sus ingredientes."""
        try:
            conn = get_connection()
            conn.execute("PRAGMA foreign_keys = ON")
            conn.execute("DELETE FROM formulaciones WHERE id=?", (formulacion_id,))
            conn.commit()
        except sqlite3.Error as e:
            print(f"Error eliminando formulación: {e}")
        finally:
            conn.close()

    def duplicar_formulacion(self, formulacion_id, nuevo_nombre=None):
        """Crea copia de una formulación existente."""
        original = self.cargar_formulacion(formulacion_id)
        if not original:
            return None
        original['nombre'] = nuevo_nombre or f"Copia de {original['nombre']}"
        del original['id']
        return self.guardar_formulacion(original)
