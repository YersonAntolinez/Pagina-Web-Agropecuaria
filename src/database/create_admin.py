import uuid
from db_manager import DBManager

def create_admin():
    db = DBManager()
    
    # 1. Buscamos el ID del rol Administrador que creamos antes
    roles = db.fetch_query("SELECT idRol FROM rol WHERE nombreRol = 'Administrador'")
    
    if roles:
        id_rol_admin = roles[0]['idRol']
        id_usuario = str(uuid.uuid4())
        
        # 2. Insertamos el usuario (Contraseña simple por ahora para probar)
        query = """INSERT INTO usuario (idUsuario, nombreUsuario, contrasena, idRol, estado) 
                   VALUES (%s, %s, %s, %s, %s)"""
        params = (id_usuario, "admin", "1234", id_rol_admin, 1)
        
        if db.run_query(query, params):
            print("Usuario 'admin' con clave '1234' creado con éxito.")
    else:
        print("No se encontró el rol Administrador. Ejecuta seed_data.py primero.")

if __name__ == "__main__":
    create_admin()