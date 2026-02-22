"""
seed_data.py — Datos iniciales del sistema
===========================================
Ejecutar UNA SOLA VEZ para dejar la base de datos lista.
Crea los roles y ubicaciones base del almacén.

Uso:
    python src/database/seed_data.py
"""

import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from database.db_manager import DBManager

def setup_initial_data():
    db = DBManager()

    print("Insertando roles...")
    id_admin    = str(uuid.uuid4())
    id_operario = str(uuid.uuid4())

    db.run_query("INSERT IGNORE INTO rol (idRol, nombreRol) VALUES (%s, %s)", (id_admin,    "Administrador"))
    db.run_query("INSERT IGNORE INTO rol (idRol, nombreRol) VALUES (%s, %s)", (id_operario, "Operario"))
    print("  ✔ Roles insertados.")

    print("Insertando ubicaciones...")
    db.run_query(
        "INSERT IGNORE INTO ubicacion (idUbicacion, nombreUbicacion, tipo) VALUES (%s, %s, %s)",
        (str(uuid.uuid4()), "Punto de Venta Principal", "PUNTO_VENTA")
    )
    db.run_query(
        "INSERT IGNORE INTO ubicacion (idUbicacion, nombreUbicacion, tipo) VALUES (%s, %s, %s)",
        (str(uuid.uuid4()), "Bodega Principal", "BODEGA")
    )
    print("  ✔ Ubicaciones insertadas.")

    print("\n¡Datos iniciales listos! Ahora ejecuta create_admin.py")

if __name__ == "__main__":
    setup_initial_data()