import uuid
from db_manager import DBManager

def setup_initial_data():
    db = DBManager()
    
    # 1. Crear Roles
    print("Insertando roles...")
    id_admin = str(uuid.uuid4())
    id_operario = str(uuid.uuid4())
    
    db.run_query("INSERT IGNORE INTO rol (idRol, nombreRol) VALUES (%s, %s)", (id_admin, "Administrador"))
    db.run_query("INSERT IGNORE INTO rol (idRol, nombreRol) VALUES (%s, %s)", (id_operario, "Operario"))

    # 2. Crear Ubicaciones (Bodegas)
    print("Insertando ubicaciones...")
    db.run_query("INSERT IGNORE INTO ubicacion (idUbicacion, nombreUbicacion) VALUES (%s, %s)", 
                 (str(uuid.uuid4()), "Punto de Venta Principal"))
    db.run_query("INSERT IGNORE INTO ubicacion (idUbicacion, nombreUbicacion) VALUES (%s, %s)", 
                 (str(uuid.uuid4()), "Bodega Norte"))

    print("¡Datos iniciales listos!")

if __name__ == "__main__":
    setup_initial_data()