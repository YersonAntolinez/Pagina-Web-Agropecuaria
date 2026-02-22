import os
import mysql.connector
from mysql.connector import Error
from dotenv import load_dotenv

# Carga las variables del archivo .env ubicado en la raíz del proyecto
load_dotenv()

class DBManager:
    """
    Gestor de base de datos para el Almacén La Playa.

    Responsabilidades:
      - Manejo de conexiones seguras a MySQL.
      - Operaciones CRUD simples (fetch_query, run_query).
      - Operaciones transaccionales atómicas (run_transaction).
      - Soporte para obtener el ID del último registro insertado.

    Configuración:
      Las credenciales se leen desde el archivo .env en la raíz del proyecto.
      Nunca escribir credenciales directamente en este archivo.
    """

    def __init__(self):
        self.config_local = {
            'host':     os.getenv('DB_HOST',     'localhost'),
            'user':     os.getenv('DB_USER',     'root'),
            'password': os.getenv('DB_PASSWORD', 'yerson11747'),
            'database': os.getenv('DB_NAME',     'la_playa_fuerte'),
            'charset':  'utf8mb4',
        }

    # ------------------------------------------------------------------
    # CONEXIÓN
    # ------------------------------------------------------------------

    def connect(self):
        """
        Abre y retorna una conexión a la base de datos.
        Retorna None si no se puede conectar.
        """
        try:
            conn = mysql.connector.connect(**self.config_local)
            return conn
        except Error as e:
            print(f"[DBManager] Error de conexión: {e}")
            return None

    # ------------------------------------------------------------------
    # LECTURA
    # ------------------------------------------------------------------

    def fetch_query(self, query, params=None):
        """
        Ejecuta un SELECT y retorna los resultados como lista de dicts.
        Retorna lista vacía si ocurre un error.

        Uso:
            resultados = db.fetch_query(
                "SELECT * FROM producto WHERE activo = %s", (1,)
            )
        """
        conn = self.connect()
        if not conn:
            return []
        try:
            cursor = conn.cursor(dictionary=True)
            cursor.execute(query, params)
            return cursor.fetchall()
        except Error as e:
            print(f"[DBManager] Error en fetch_query: {e}")
            return []
        finally:
            conn.close()

    def fetch_one(self, query, params=None):
        """
        Igual que fetch_query pero retorna solo el primer resultado o None.
        Útil para búsquedas por ID o verificaciones de existencia.

        Uso:
            cliente = db.fetch_one(
                "SELECT * FROM cliente WHERE documento = %s", (doc,)
            )
        """
        results = self.fetch_query(query, params)
        return results[0] if results else None

    # ------------------------------------------------------------------
    # ESCRITURA SIMPLE
    # ------------------------------------------------------------------

    def run_query(self, query, params=None):
        """
        Ejecuta un INSERT, UPDATE o DELETE simple (una sola operación).

        Retorna un dict con:
          - success (bool): True si la operación fue exitosa.
          - lastrowid (int): ID del último registro insertado (útil para INSERT).
          - rowcount (int): Número de filas afectadas.

        Uso:
            result = db.run_query(
                "UPDATE producto SET activo = %s WHERE idProducto = %s",
                (0, producto_id)
            )
            if result['success']:
                print(f"Filas afectadas: {result['rowcount']}")
        """
        conn = self.connect()
        if not conn:
            return {'success': False, 'lastrowid': None, 'rowcount': 0}
        try:
            cursor = conn.cursor()
            cursor.execute(query, params)
            conn.commit()
            return {
                'success':   True,
                'lastrowid': cursor.lastrowid,
                'rowcount':  cursor.rowcount,
            }
        except Error as e:
            print(f"[DBManager] Error en run_query: {e}")
            conn.rollback()
            return {'success': False, 'lastrowid': None, 'rowcount': 0}
        finally:
            conn.close()

    # ------------------------------------------------------------------
    # ESCRITURA TRANSACCIONAL
    # ------------------------------------------------------------------

    def run_transaction(self, operations):
        """
        Ejecuta múltiples operaciones de escritura como una transacción atómica.
        Si cualquiera falla, TODAS se revierten (rollback).

        Parámetro:
          operations: lista de tuplas (query, params) en orden de ejecución.

        Retorna un dict con:
          - success (bool): True si TODAS las operaciones fueron exitosas.
          - error (str|None): Mensaje del error si ocurrió alguno.

        Uso típico — registrar un traslado:
            ops = [
                # 1. Crear la cabecera del movimiento
                ("INSERT INTO movimiento (...) VALUES (...)", (...,)),

                # 2. Restar stock en bodega origen
                ("UPDATE inventario SET stockActual = stockActual - %s
                  WHERE idProducto = %s AND idUbicacion = %s",
                  (cantidad_base, id_producto, id_origen)),

                # 3. Sumar stock en punto de venta destino
                ("UPDATE inventario SET stockActual = stockActual + %s
                  WHERE idProducto = %s AND idUbicacion = %s",
                  (cantidad_base, id_producto, id_destino)),

                # 4. Insertar el detalle del movimiento
                ("INSERT INTO movimiento_detalle (...) VALUES (...)", (...,)),
            ]
            result = db.run_transaction(ops)

            if result['success']:
                print("Traslado registrado correctamente.")
            else:
                print(f"Error: {result['error']}")
        """
        conn = self.connect()
        if not conn:
            return {'success': False, 'error': 'No se pudo conectar a la base de datos.'}

        try:
            conn.autocommit = False
            cursor = conn.cursor()

            for query, params in operations:
                cursor.execute(query, params)

            conn.commit()
            return {'success': True, 'error': None}

        except Error as e:
            conn.rollback()
            print(f"[DBManager] Error en transacción, se hizo rollback: {e}")
            return {'success': False, 'error': str(e)}

        finally:
            conn.close()

    # ------------------------------------------------------------------
    # UTILIDADES
    # ------------------------------------------------------------------

    def test_connection(self):
        """
        Verifica si hay conexión disponible con la base de datos.
        Retorna True si conecta, False si no.
        Útil para el indicador de estado offline/online en la UI.

        Uso:
            if db.test_connection():
                mostrar_indicador("Conectado")
            else:
                mostrar_indicador("Sin conexión — modo offline")
        """
        conn = self.connect()
        if conn:
            conn.close()
            return True
        return False