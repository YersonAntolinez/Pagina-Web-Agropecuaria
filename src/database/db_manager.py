import mysql.connector
from mysql.connector import Error

class DBManager:
    def __init__(self):
        self.config_local = {
            'host': 'localhost',
            'user': 'root',
            'password': 'yerson11747', # Tu contraseña
            'database': 'la_playa_fuerte'
        }

    def connect(self):
        try:
            conn = mysql.connector.connect(**self.config_local)
            return conn
        except Error as e:
            print(f"Error: {e}")
            return None

    def run_query(self, query, params=None):
        """Para INSERT, UPDATE, DELETE"""
        conn = self.connect()
        if conn:
            cursor = conn.cursor()
            try:
                cursor.execute(query, params)
                conn.commit()
                return True
            except Error as e:
                print(f"Error ejecutando consulta: {e}")
                return False
            finally:
                conn.close()

    def fetch_query(self, query, params=None):
        """Para SELECT (traer datos)"""
        conn = self.connect()
        if conn:
            cursor = conn.cursor(dictionary=True) # Nos devuelve los datos como dict {}
            try:
                cursor.execute(query, params)
                result = cursor.fetchall()
                return result
            except Error as e:
                print(f"Error en lectura: {e}")
                return []
            finally:
                conn.close()