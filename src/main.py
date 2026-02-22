import flet as ft
import sys
import os

# Asegura que los módulos src sean accesibles
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from ui.login import login_window

async def main(page: ft.Page):
    """
    Punto de entrada principal de la aplicación.
    Gestiona el flujo de navegación global:
      Login → Dashboard → Login (logout)

    La función 'navigate' se pasa como callback a cada vista,
    permitiendo que cualquier módulo pueda redirigir sin conocer
    los detalles de las otras pantallas.
    """

    async def navigate(destino: str, datos: dict = {}):
        """
        Limpia la página y carga la vista solicitada.

        Parámetros:
          destino: 'login' | 'dashboard'
          datos:   información a pasar entre vistas
                   (ej: {'nombre': 'Yerson', 'rol': 'admin-uuid...'})
        """
        # Limpiar sin llamar update_async aquí — la vista destino se encarga
        page.controls.clear()

        if destino == "login":
            await login_window(page, navigate)

        elif destino == "dashboard":
            from ui.dashboard import dashboard_main
            await dashboard_main(
                page,
                navigate,
                usuario_nombre=datos.get("nombre", "Usuario"),
                id_rol=datos.get("id_rol", "")
            )

    # Arrancar siempre desde el login
    await navigate("login")

if __name__ == "__main__":
    ft.app(target=main)