import flet as ft
import asyncio
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DBManager

async def login_window(page: ft.Page, navigate):
    """
    Vista de inicio de sesión.

    Parámetros:
      page:     objeto de página de Flet.
      navigate: callback del main.py para redirigir a otras vistas.
                Uso: await navigate('dashboard', {'nombre': ..., 'id_rol': ...})
    """

    page.title = "La Playa | Sistema de Gestión Agropecuaria"
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = "#0a0e12"
    page.padding = 0
    page.spacing = 0

    async def handle_login(e):
        error_text.value = ""

        if not user_input.value or not pass_input.value:
            error_text.value = "⚠️ Por favor, completa todos los campos"
            error_text.color = "orange400"
            await page.update_async()
            return

        # Estado de carga
        login_btn.disabled = True
        login_btn.content = ft.Row(
            [
                ft.ProgressRing(width=20, height=20, color="white", stroke_width=2),
                ft.Text("Verificando...", size=15, weight=ft.FontWeight.BOLD)
            ],
            alignment=ft.MainAxisAlignment.CENTER,
            spacing=10
        )
        await page.update_async()

        try:
            db = DBManager()
            query = """
                SELECT u.idUsuario, u.nombreUsuario, u.idRol, r.nombreRol
                FROM usuario u
                JOIN rol r ON u.idRol = r.idRol
                WHERE u.nombreUsuario = %s
                  AND u.contrasena = %s
                  AND u.estado = 1
            """
            usuario = db.fetch_one(query, (user_input.value.strip(), pass_input.value))

            if usuario:
                # Feedback de éxito
                login_btn.bgcolor = "green700"
                login_btn.content = ft.Row(
                    [
                        ft.Icon("check_circle_rounded", color="white", size=22),
                        ft.Text("¡Acceso concedido!", size=15, weight=ft.FontWeight.BOLD)
                    ],
                    alignment=ft.MainAxisAlignment.CENTER,
                    spacing=10
                )
                error_text.color = "green400"
                error_text.value = f"Bienvenido, {usuario['nombreUsuario']}"
                await page.update_async()
                await asyncio.sleep(1.2)

                # Redirigir al dashboard pasando los datos del usuario
                await navigate("dashboard", {
                    "nombre": usuario['nombreUsuario'],
                    "id_rol": usuario['idRol'],
                    "nombre_rol": usuario['nombreRol'],
                })

            else:
                error_text.value = "❌ Credenciales incorrectas"
                error_text.color = "red400"
                login_btn.disabled = False
                login_btn.bgcolor = "#1e7e34"
                login_btn.content = ft.Text("INICIAR SESIÓN", size=15, weight=ft.FontWeight.BOLD)
                pass_input.value = ""
                user_input.focus()
                await page.update_async()

        except Exception as ex:
            error_text.value = f"⚠️ Error del sistema: {str(ex)}"
            error_text.color = "red400"
            login_btn.disabled = False
            login_btn.bgcolor = "#1e7e34"
            login_btn.content = ft.Text("INICIAR SESIÓN", size=15, weight=ft.FontWeight.BOLD)
            await page.update_async()

    # --- Imagen de fondo ---
    RUTA_IMAGEN_FONDO = "assets/images/PlayaIcono.jpg"

    left_panel = ft.Container(
        expand=True,
        content=ft.Stack(
            expand=True,
            controls=[
                ft.Image(
                    src=RUTA_IMAGEN_FONDO,
                    fit=ft.ImageFit.COVER,
                    expand=True,
                ),
                ft.Container(
                    expand=True,
                    alignment=ft.alignment.center,
                    padding=40,
                    content=ft.Column(
                        [
                            ft.Icon("agriculture_rounded", size=100, color="white"),
                            ft.Container(height=20),
                            ft.Text("ALMACÉN AGROPECUARIO", size=38, weight=ft.FontWeight.BOLD,
                                    color="white", text_align=ft.TextAlign.CENTER),
                            ft.Text("LA PLAYA", size=46, weight=ft.FontWeight.BOLD,
                                    color="white", text_align=ft.TextAlign.CENTER),
                            ft.Container(height=40),
                            ft.Text('"Cosechando eficiencia,\nsembrando prosperidad"',
                                    size=18, color="white", text_align=ft.TextAlign.CENTER, italic=True),
                        ],
                        horizontal_alignment=ft.CrossAxisAlignment.CENTER,
                        alignment=ft.MainAxisAlignment.CENTER,
                    ),
                )
            ]
        ),
    )

    user_input = ft.TextField(
        label="Usuario",
        hint_text="Ingresa tu nombre de usuario",
        prefix_icon="person_outline_rounded",
        border_radius=10,
        bgcolor="#1a1f25",
        border_color="#2d3748",
        focused_border_color="green400",
        focused_bgcolor="#1e252d",
        text_size=15,
        height=60,
        autofocus=True,
        cursor_color="green400"
    )

    pass_input = ft.TextField(
        label="Contraseña",
        hint_text="Ingresa tu contraseña",
        password=True,
        can_reveal_password=True,
        prefix_icon="lock_outline_rounded",
        border_radius=10,
        bgcolor="#1a1f25",
        border_color="#2d3748",
        focused_border_color="green400",
        focused_bgcolor="#1e252d",
        text_size=15,
        height=60,
        on_submit=handle_login,
        cursor_color="green400"
    )

    error_text = ft.Text("", size=13, weight=ft.FontWeight.W_500, text_align=ft.TextAlign.CENTER)

    login_btn = ft.Container(
        content=ft.Text("INICIAR SESIÓN", size=15, weight=ft.FontWeight.BOLD),
        alignment=ft.alignment.center,
        bgcolor="#1e7e34",
        height=55,
        border_radius=10,
        on_click=handle_login,
        ink=True,
        animate=ft.animation.Animation(200, ft.AnimationCurve.EASE_IN_OUT),
    )

    right_panel = ft.Container(
        content=ft.Column(
            [
                ft.Container(height=80),
                ft.Text("Iniciar Sesión", size=32, weight=ft.FontWeight.BOLD, color="white"),
                ft.Text("Ingresa tus credenciales para acceder al sistema", size=14, color="grey500"),
                ft.Container(height=40),
                user_input,
                ft.Container(height=5),
                pass_input,
                ft.Container(height=5),
                error_text,
                ft.Container(height=25),
                login_btn,
                ft.Container(height=20),
                ft.Row([
                    ft.Container(
                        content=ft.Text("¿Olvidaste tu contraseña?", size=13, color="green400"),
                        on_click=lambda _: print("Recuperar contraseña"),
                        ink=True,
                        border_radius=5,
                        padding=5,
                    )
                ], alignment=ft.MainAxisAlignment.CENTER),
                ft.Container(expand=True),
                ft.Divider(color="#2d3748", height=1),
                ft.Container(height=15),
                ft.Text("v1.0.0 Stable • 2025", size=11, color="grey700", text_align=ft.TextAlign.CENTER)
            ],
            horizontal_alignment=ft.CrossAxisAlignment.CENTER,
            spacing=0
        ),
        expand=3,
        bgcolor="#0e1419",
        padding=ft.padding.only(left=80, right=80, top=20, bottom=20)
    )

    main_layout = ft.Row([left_panel, right_panel], spacing=0, expand=True)
    page.add(main_layout)


if __name__ == "__main__":
    # Para pruebas directas del login sin pasar por main.py
    async def _test(page):
        async def _nav(destino, datos={}):
            print(f"Navegando a: {destino} con datos: {datos}")
        await login_window(page, _nav)

    ft.app(target=_test)