import flet as ft
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DBManager

async def dashboard_main(page: ft.Page, navigate, usuario_nombre="Usuario", id_rol=""):
    """
    Vista principal del sistema tras el login.

    Parámetros:
      page:           objeto de página de Flet.
      navigate:       callback del main.py para redirigir vistas.
      usuario_nombre: nombre del usuario autenticado.
      id_rol:         UUID del rol del usuario (para control de acceso por módulo).
    """

    page.title = "La Playa | Panel de Control"
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0e12"
    page.padding = 0
    page.spacing = 0

    db = DBManager()

    # ------------------------------------------------------------------
    # CUERPO DINÁMICO
    # ------------------------------------------------------------------
    main_content = ft.Container(
        content=ft.Column(
            [
                ft.Icon("agriculture", size=100, color="green900"),
                ft.Text("Seleccione un módulo en el menú lateral", size=20, color="grey700")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        ),
        expand=True,
        padding=30,
    )

    # ------------------------------------------------------------------
    # NAVEGACIÓN ENTRE MÓDULOS
    # ------------------------------------------------------------------
    async def route_change(e):
        index = e.control.selected_index

        # Indicador de carga mientras cambia el módulo
        main_content.content = ft.Column(
            [
                ft.ProgressRing(color="green400"),
                ft.Text("Cargando módulo...", size=16, color="grey500")
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            horizontal_alignment=ft.CrossAxisAlignment.CENTER
        )
        await page.update_async()
        await asyncio.sleep(0.2)

        if index == 0:
            content_view = _vista_inicio()
        elif index == 1:
            content_view = await _vista_inventario()
        elif index == 2:
            content_view = _vista_placeholder("🛒 VENTAS Y FACTURACIÓN", "Registro y control de ventas")
        elif index == 3:
            content_view = _vista_placeholder("👥 CLIENTES Y FIANZAS", "Administración de clientes y créditos")
        elif index == 4:
            content_view = _vista_placeholder("📊 REPORTES ESTADÍSTICOS", "Análisis y métricas del negocio")
        else:
            content_view = _vista_inicio()

        main_content.content = content_view
        await page.update_async()

    # ------------------------------------------------------------------
    # LOGOUT — vuelve al login sin cerrar la app
    # ------------------------------------------------------------------
    async def handle_logout(e):
        await navigate("login")

    # ------------------------------------------------------------------
    # VISTAS DE MÓDULOS
    # ------------------------------------------------------------------

    def _vista_inicio():
        return ft.Column(
            [
                ft.Text("🏠 RESUMEN GENERAL", size=30, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Bienvenido al panel de control del Almacén La Playa",
                        size=16, color="grey500"),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    def _vista_placeholder(titulo, subtitulo):
        """Vista temporal para módulos aún no desarrollados."""
        return ft.Column(
            [
                ft.Text(titulo, size=30, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text(subtitulo, size=16, color="grey500"),
                ft.Container(height=20),
                ft.Text("Módulo en desarrollo...", size=14, color="grey700", italic=True),
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            alignment=ft.MainAxisAlignment.CENTER,
        )

    async def _vista_inventario():
        """
        Vista del módulo de inventario.
        Por ahora retorna el placeholder; se reemplazará con el módulo completo.
        """
        return _vista_placeholder("📦 INVENTARIO Y STOCK", "Gestión de productos y existencias")

    # ------------------------------------------------------------------
    # COMPONENTES DE LAYOUT
    # ------------------------------------------------------------------

    rail = ft.NavigationRail(
        selected_index=0,
        label_type=ft.NavigationRailLabelType.ALL,
        min_width=100,
        min_extended_width=200,
        group_alignment=-0.9,
        bgcolor="#0e1419",
        indicator_color="green700",
        destinations=[
            ft.NavigationRailDestination(icon="home_outlined",          selected_icon="home",          label="Inicio"),
            ft.NavigationRailDestination(icon="inventory_2_outlined",   selected_icon="inventory_2",   label="Inventario"),
            ft.NavigationRailDestination(icon="shopping_cart_outlined", selected_icon="shopping_cart", label="Ventas"),
            ft.NavigationRailDestination(icon="people_outline",         selected_icon="people",        label="Clientes"),
            ft.NavigationRailDestination(icon="bar_chart_outlined",     selected_icon="bar_chart",     label="Reportes"),
        ],
        on_change=route_change,
    )

    header = ft.Container(
        content=ft.Row(
            [
                ft.Row([
                    ft.Icon("agriculture", color="green400", size=30),
                    ft.Text("ALMACÉN LA PLAYA", size=20, weight=ft.FontWeight.BOLD),
                ], spacing=10),
                ft.Row([
                    ft.Icon("account_circle", color="grey500", size=24),
                    ft.Text(usuario_nombre, color="grey400", size=15),
                    ft.VerticalDivider(width=20),
                    ft.IconButton(
                        icon="logout_rounded",
                        icon_color="red400",
                        tooltip="Cerrar sesión",
                        on_click=handle_logout
                    ),
                ], spacing=10)
            ],
            alignment=ft.MainAxisAlignment.SPACE_BETWEEN
        ),
        padding=ft.padding.only(left=20, right=20, top=10, bottom=10),
        bgcolor="#0e1419",
        border=ft.border.only(bottom=ft.border.BorderSide(1, "#1e252d"))
    )

    layout_body = ft.Row(
        [
            rail,
            ft.VerticalDivider(width=1, color="#1e252d"),
            main_content
        ],
        expand=True,
        spacing=0
    )

    container_final = ft.Column([header, layout_body], expand=True, spacing=0)
    page.add(container_final)


if __name__ == "__main__":
    # Para pruebas directas del dashboard sin pasar por main.py
    async def _test(page):
        async def _nav(destino, datos={}):
            print(f"Navegando a: {destino}")
        await dashboard_main(page, _nav, usuario_nombre="Admin Test")

    ft.app(target=_test)