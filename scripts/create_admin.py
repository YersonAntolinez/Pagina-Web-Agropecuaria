"""
create_admin.py — Creación del usuario administrador inicial
=============================================================
Ejecutar UNA SOLA VEZ después de seed_data.py.
Crea el usuario 'admin' con contraseña '1234' para el primer acceso.

IMPORTANTE: Cambia la contraseña desde el sistema después del primer login.

Uso:
    python src/database/create_admin.py
"""

import uuid
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from database.db_manager import DBManager

def create_admin():
    db = DBManager()

    # Buscar el rol Administrador
    rol = db.fetch_one("SELECT idRol FROM rol WHERE nombreRol = 'Administrador'")

    if not rol:
        print("❌ No se encontró el rol Administrador.")
        print("   Ejecuta primero: python src/database/seed_data.py")
        return

    # Verificar si ya existe el usuario admin
    existente = db.fetch_one("SELECT idUsuario FROM usuario WHERE nombreUsuario = 'admin'")
    if existente:
        print("⚠️  El usuario 'admin' ya existe. No se creó uno nuevo.")
        return

    id_usuario = str(uuid.uuid4())
    result = db.run_query(
        """INSERT INTO usuario (idUsuario, nombreUsuario, contrasena, idRol, estado)
           VALUES (%s, %s, %s, %s, %s)""",
        (id_usuario, "admin", "1234", rol['idRol'], 1)
    )

    if result['success']:
        print("✔ Usuario 'admin' creado exitosamente.")
        print("  Usuario:    admin")
        print("  Contraseña: 1234")
        print("\n⚠️  Recuerda cambiar la contraseña después del primer login.")
    else:
        print("❌ Error al crear el usuario administrador.")

if __name__ == "__main__":
    create_admin()