"""
inventario.py — Módulo de Inventario
=====================================
Filtros síncronos compatibles con Flet 0.26.0.
Scroll horizontal unificado para toda la tabla.
precio_compra visible solo para Administrador.

Prueba independiente:
    python src/ui/inventario.py
"""

import flet as ft
import sys
import os

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from database.db_manager import DBManager

# ─────────────────────────────────────────────────────────────
# COLORES
# ─────────────────────────────────────────────────────────────
VERDE          = "#1e7e34"
VERDE_CLARO    = "#2d9e47"
FONDO          = "#0a0e12"
FONDO_CARD     = "#0e1419"
FONDO_FILA     = "#12181f"
FONDO_FILA_ALT = "#0e1419"
BORDE          = "#1e252d"
TEXTO          = "#e0e6ed"
TEXTO_GRIS     = "#6b7a8d"
ROJO           = "#e53935"
AMARILLO       = "#f9a825"
VERDE_STOCK    = "#43a047"

ROL_ADMIN = "Administrador"

# ─────────────────────────────────────────────────────────────
# CONSULTAS
# ─────────────────────────────────────────────────────────────

def obtener_ubicaciones(db):
    return db.fetch_query(
        "SELECT idUbicacion, nombreUbicacion, tipo FROM ubicacion ORDER BY tipo DESC"
    )

def obtener_tipos(db):
    return db.fetch_query(
        "SELECT idTipoProducto, nombre FROM tipo_producto ORDER BY nombre"
    )

def obtener_stock(db, filtro_tipo=None, filtro_texto=None, es_admin=False):
    campos_extra = ", p.precio_compra" if es_admin else ""
    query = f"""
        SELECT
            p.idProducto,
            p.nombre             AS producto,
            tp.nombre            AS tipo,
            p.unidad_medida_base AS unidad,
            p.stock_minimo,
            p.precio_lista
            {campos_extra},
            u.idUbicacion,
            u.nombreUbicacion,
            COALESCE(i.stockActual, 0) AS stock
        FROM producto p
        JOIN tipo_producto tp ON tp.idTipoProducto = p.idTipoProducto
        CROSS JOIN ubicacion u
        LEFT JOIN inventario i
            ON i.idProducto   = p.idProducto
            AND i.idUbicacion = u.idUbicacion
        WHERE p.activo = 1
    """
    params = []
    if filtro_tipo:
        query += " AND tp.idTipoProducto = %s"
        params.append(filtro_tipo)
    if filtro_texto:
        query += " AND p.nombre LIKE %s"
        params.append(f"%{filtro_texto}%")

    query += " ORDER BY tp.nombre, p.nombre, u.tipo DESC"
    return db.fetch_query(query, params or None)

def agrupar_por_producto(filas, es_admin=False):
    productos = {}
    for fila in filas:
        pid = fila['idProducto']
        if pid not in productos:
            entrada = {
                'nombre':       fila['producto'],
                'tipo':         fila['tipo'],
                'unidad':       fila['unidad'],
                'stock_minimo': fila['stock_minimo'],
                'precio_lista': fila['precio_lista'],
                'stocks':       {},
            }
            if es_admin:
                entrada['precio_compra'] = fila.get('precio_compra', 0) or 0
            productos[pid] = entrada
        productos[pid]['stocks'][fila['idUbicacion']] = fila['stock']
    return list(productos.values())

# ─────────────────────────────────────────────────────────────
# COMPONENTES UI
# ─────────────────────────────────────────────────────────────

def badge_tipo(tipo):
    colores = {
        "Fungicida":    ("#1a3a4a", "#4fc3f7"),
        "Herbicida":    ("#2a3a1a", "#aed581"),
        "Insecticida":  ("#3a1a2a", "#f48fb1"),
        "Fertilizante": ("#2a2a1a", "#fff176"),
        "Acaricida":    ("#3a2a1a", "#ffcc80"),
    }
    bg, color = colores.get(tipo, ("#1e252d", "#90a4ae"))
    return ft.Container(
        content=ft.Text(tipo, size=11, color=color, weight=ft.FontWeight.W_600),
        bgcolor=bg,
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
    )

def indicador_stock(stock_actual, stock_minimo):
    s = float(stock_actual)
    m = float(stock_minimo)
    if s <= 0:
        color, icono, tip = ROJO,        "error_rounded",        "Sin stock"
    elif s <= m:
        color, icono, tip = AMARILLO,    "warning_rounded",      f"Crítico (mínimo: {m:,.1f})"
    else:
        color, icono, tip = VERDE_STOCK, "check_circle_rounded", "Stock normal"

    return ft.Container(
        content=ft.Row([
            ft.Icon(icono, color=color, size=16),
            ft.Text(f"{s:,.1f}", size=13, color=color, weight=ft.FontWeight.W_600),
        ], spacing=4),
        tooltip=tip,
    )

def celda(contenido, ancho=None):
    return ft.Container(
        content=contenido if isinstance(contenido, ft.Control)
                else ft.Text(str(contenido), size=13, color=TEXTO),
        width=ancho,
        padding=ft.padding.symmetric(horizontal=12, vertical=10),
    )

def fila_producto(producto, ubicaciones, indice, es_admin=False):
    bg = FONDO_FILA if indice % 2 == 0 else FONDO_FILA_ALT
    stock_total = sum(float(v) for v in producto['stocks'].values())

    celdas = [
        celda(ft.Text(producto['nombre'], size=13, color=TEXTO,
                      weight=ft.FontWeight.W_500), ancho=220),
        celda(badge_tipo(producto['tipo']), ancho=120),
    ]
    for ub in ubicaciones:
        stock = producto['stocks'].get(ub['idUbicacion'], 0)
        celdas.append(celda(indicador_stock(stock, producto['stock_minimo']), ancho=140))

    celdas += [
        celda(ft.Text(f"{stock_total:,.1f}", size=13, color=TEXTO_GRIS), ancho=100),
        celda(ft.Text(producto['unidad'],     size=13, color=TEXTO_GRIS), ancho=90),
        celda(ft.Text(f"${float(producto['precio_lista']):,.0f}",
                      size=13, color=VERDE_CLARO), ancho=110),
    ]
    if es_admin:
        pc = float(producto.get('precio_compra') or 0)
        celdas.append(celda(
            ft.Text(f"${pc:,.0f}", size=13, color="#ef9a9a"), ancho=120
        ))

    return ft.Container(
        content=ft.Row(celdas, spacing=0),
        bgcolor=bg,
        border=ft.border.only(bottom=ft.border.BorderSide(1, BORDE)),
        on_hover=lambda e: _hover(e, bg),
    )

def _hover(e, bg_original):
    e.control.bgcolor = "#1a2433" if e.data == "true" else bg_original
    e.control.update()

def encabezado_tabla(ubicaciones, es_admin=False):
    cols = [("Producto", 220), ("Categoría", 120)]
    for ub in ubicaciones:
        cols.append((ub['nombreUbicacion'], 140))
    cols += [("Stock Total", 100), ("Unidad", 90), ("Precio Venta", 110)]
    if es_admin:
        cols.append(("Precio Compra", 120))

    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(h, size=12, color=TEXTO_GRIS,
                                weight=ft.FontWeight.W_600),
                width=w,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
            )
            for h, w in cols
        ], spacing=0),
        bgcolor="#080c10",
        border=ft.border.only(
            bottom=ft.border.BorderSide(2, VERDE),
            top=ft.border.BorderSide(1, BORDE),
        ),
    )

def tarjeta_resumen(icono, label, valor, color=TEXTO, on_click=None, seleccionada=False):
    borde_color  = color if seleccionada else BORDE
    borde_grosor = 2     if seleccionada else 1
    bg           = "#1a2433" if seleccionada else FONDO_CARD
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icono, color=color, size=20),
                ft.Text(label, size=12, color=TEXTO_GRIS),
            ], spacing=8),
            ft.Text(str(valor), size=22, color=color, weight=ft.FontWeight.BOLD),
            ft.Text(
                "Clic para filtrar" if on_click and not seleccionada else ("Clic para quitar filtro" if seleccionada else ""),
                size=10, color=TEXTO_GRIS, italic=True,
            ),
        ], spacing=4),
        bgcolor=bg,
        border=ft.border.all(borde_grosor, borde_color),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        expand=True,
        on_click=on_click,
        ink=True if on_click else False,
        tooltip="Filtrar por esta alerta" if on_click and not seleccionada else ("Quitar filtro" if seleccionada else None),
    )


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────

async def vista_inventario(page: ft.Page, db: DBManager, nombre_rol: str = ROL_ADMIN):

    es_admin    = (nombre_rol == ROL_ADMIN)
    ubicaciones = obtener_ubicaciones(db)
    tipos       = obtener_tipos(db)

    # Estado mutable
    estado = {"tipo": None, "texto": None, "alerta": None}

    # Contenedores reactivos
    resumen_row  = ft.Row(spacing=12)
    filtros_row  = ft.Row(spacing=8, wrap=True)
    cuerpo_tabla = ft.Column(spacing=0)

    # Scroll unificado: un solo Row con scroll horizontal
    # que contiene todo el cuerpo (encabezado + filas)
    tabla_scroll = ft.Row(
        controls=[cuerpo_tabla],
        scroll=ft.ScrollMode.AUTO,
        spacing=0,
    )
    tabla_vertical = ft.Column(
        controls=[tabla_scroll],
        scroll=ft.ScrollMode.AUTO,
        expand=True,
        spacing=0,
    )

    # ── Helpers de reconstrucción (síncronos) ──

    def calcular_resumen(prods):
        total    = len(prods)
        criticos = sum(1 for p in prods if any(
            float(v) <= float(p['stock_minimo']) for v in p['stocks'].values()
        ))
        sin_stk  = sum(1 for p in prods if any(
            float(v) <= 0 for v in p['stocks'].values()
        ))
        return total, criticos, sin_stk

    def reconstruir_resumen(prods_todos):
        # Siempre calcular sobre TODOS los productos (sin filtro de alerta)
        # para que los contadores no cambien al filtrar
        filas_todos = obtener_stock(db, estado["tipo"], estado["texto"], es_admin)
        base = agrupar_por_producto(filas_todos, es_admin)
        total, criticos, sin_stk = calcular_resumen(base)

        def click_critico(e):
            estado["alerta"] = None if estado["alerta"] == "critico" else "critico"
            aplicar_filtro_alerta()

        def click_sin_stock(e):
            estado["alerta"] = None if estado["alerta"] == "sin_stock" else "sin_stock"
            aplicar_filtro_alerta()

        resumen_row.controls = [
            tarjeta_resumen("inventory_2",     "Total Productos", total),
            tarjeta_resumen("warning_rounded", "Stock Crítico",   criticos,
                            AMARILLO if criticos else TEXTO,
                            on_click=click_critico if criticos else None,
                            seleccionada=(estado["alerta"] == "critico")),
            tarjeta_resumen("error_rounded",   "Sin Stock",       sin_stk,
                            ROJO if sin_stk else TEXTO,
                            on_click=click_sin_stock if sin_stk else None,
                            seleccionada=(estado["alerta"] == "sin_stock")),
            tarjeta_resumen("store",           "Ubicaciones",     len(ubicaciones)),
        ]

    def reconstruir_tabla(prods):
        cuerpo_tabla.controls.clear()
        cuerpo_tabla.controls.append(encabezado_tabla(ubicaciones, es_admin))
        if not prods:
            cuerpo_tabla.controls.append(ft.Container(
                content=ft.Column([
                    ft.Icon("search_off_rounded", size=48, color=TEXTO_GRIS),
                    ft.Text("No se encontraron productos", size=16, color=TEXTO_GRIS),
                ], horizontal_alignment=ft.CrossAxisAlignment.CENTER, spacing=10),
                alignment=ft.alignment.center,
                padding=60,
                width=800,
            ))
        else:
            for i, prod in enumerate(prods):
                cuerpo_tabla.controls.append(fila_producto(prod, ubicaciones, i, es_admin))

    def aplicar_filtro_alerta():
        """Filtra la tabla según la alerta seleccionada en las tarjetas."""
        filas = obtener_stock(db, estado["tipo"], estado["texto"], es_admin)
        prods = agrupar_por_producto(filas, es_admin)

        if estado["alerta"] == "critico":
            prods = [p for p in prods if any(
                float(v) <= float(p['stock_minimo']) for v in p['stocks'].values()
            )]
        elif estado["alerta"] == "sin_stock":
            prods = [p for p in prods if any(
                float(v) <= 0 for v in p['stocks'].values()
            )]

        reconstruir_resumen(prods)
        reconstruir_tabla(prods)
        page.update()

    def reconstruir_filtros():
        """Redibuja los botones de filtro reflejando el estado activo."""
        filtros_row.controls.clear()

        def hacer_click_todos(e):
            estado["tipo"] = None
            reconstruir_filtros()
            filas = obtener_stock(db, None, estado["texto"], es_admin)
            prods = agrupar_por_producto(filas, es_admin)
            reconstruir_resumen(prods)
            reconstruir_tabla(prods)
            page.update()

        filtros_row.controls.append(
            ft.Container(
                content=ft.Text(
                    "Todos", size=12,
                    color="white" if estado["tipo"] is None else TEXTO_GRIS,
                    weight=ft.FontWeight.W_600 if estado["tipo"] is None else ft.FontWeight.W_400,
                ),
                bgcolor=VERDE if estado["tipo"] is None else "#1a1f25",
                border=ft.border.all(1, VERDE if estado["tipo"] is None else BORDE),
                border_radius=20,
                padding=ft.padding.symmetric(horizontal=14, vertical=6),
                on_click=hacer_click_todos,
                ink=True,
            )
        )

        for t in tipos:
            tid    = t['idTipoProducto']
            nombre = t['nombre']
            activo = (estado["tipo"] == tid)

            def hacer_click_tipo(e, tipo_id=tid):
                estado["tipo"] = tipo_id
                reconstruir_filtros()
                filas = obtener_stock(db, tipo_id, estado["texto"], es_admin)
                prods = agrupar_por_producto(filas, es_admin)
                reconstruir_resumen(prods)
                reconstruir_tabla(prods)
                page.update()

            filtros_row.controls.append(
                ft.Container(
                    content=ft.Text(
                        nombre, size=12,
                        color="white" if activo else TEXTO_GRIS,
                        weight=ft.FontWeight.W_600 if activo else ft.FontWeight.W_400,
                    ),
                    bgcolor=VERDE if activo else "#1a1f25",
                    border=ft.border.all(1, VERDE if activo else BORDE),
                    border_radius=20,
                    padding=ft.padding.symmetric(horizontal=14, vertical=6),
                    on_click=hacer_click_tipo,
                    ink=True,
                )
            )

    def on_buscar(e):
        estado["texto"] = e.control.value.strip() or None
        filas = obtener_stock(db, estado["tipo"], estado["texto"], es_admin)
        prods = agrupar_por_producto(filas, es_admin)
        reconstruir_resumen(prods)
        reconstruir_tabla(prods)
        page.update()

    def on_refrescar(e):
        btn_refrescar.disabled = True
        btn_refrescar.icon_color = TEXTO_GRIS
        page.update()
        estado["tipo"]  = None
        estado["texto"] = None
        buscador.value  = ""
        filas = obtener_stock(db, None, None, es_admin)
        prods = agrupar_por_producto(filas, es_admin)
        reconstruir_filtros()
        reconstruir_resumen(prods)
        reconstruir_tabla(prods)
        btn_refrescar.disabled = False
        btn_refrescar.icon_color = VERDE_CLARO
        page.update()

    # ── Componentes ──

    buscador = ft.TextField(
        hint_text="Buscar producto por nombre...",
        prefix_icon="search_rounded",
        border_radius=8,
        bgcolor="#1a1f25",
        border_color=BORDE,
        focused_border_color=VERDE,
        text_size=13,
        height=42,
        cursor_color=VERDE,
        expand=True,
        on_change=on_buscar,
    )

    btn_refrescar = ft.IconButton(
        icon="refresh_rounded",
        icon_color=VERDE_CLARO,
        tooltip="Refrescar tabla",
        on_click=on_refrescar,
    )

    # ── Layout ──
    contenido = ft.Column([

        ft.Row([
            ft.Column([
                ft.Text("Inventario y Stock", size=26,
                        weight=ft.FontWeight.BOLD, color=TEXTO),
                ft.Text("Productos disponibles por ubicación",
                        size=13, color=TEXTO_GRIS),
            ], spacing=2, expand=True),
            btn_refrescar,
        ], alignment=ft.MainAxisAlignment.SPACE_BETWEEN),

        ft.Container(height=14),
        resumen_row,
        ft.Container(height=14),

        ft.Container(
            content=ft.Column([
                ft.Row([buscador]),
                ft.Container(height=8),
                filtros_row,
            ], spacing=0),
            bgcolor=FONDO_CARD,
            border=ft.border.all(1, BORDE),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        ),

        ft.Container(height=12),

        ft.Container(
            content=tabla_vertical,
            bgcolor=FONDO_CARD,
            border=ft.border.all(1, BORDE),
            border_radius=10,
            expand=True,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS,
            padding=0,
        ),

    ], expand=True, spacing=0)

    # ── Carga inicial (sin update_async — página aún sin controles) ──
    filas_ini = obtener_stock(db, None, None, es_admin)
    prods_ini = agrupar_por_producto(filas_ini, es_admin)
    reconstruir_filtros()
    reconstruir_resumen(prods_ini)
    reconstruir_tabla(prods_ini)

    return contenido


# ─────────────────────────────────────────────────────────────
# STANDALONE
# ─────────────────────────────────────────────────────────────

async def _main_standalone(page: ft.Page):
    page.title = "La Playa | Inventario"
    page.window.maximized = True
    page.theme_mode = ft.ThemeMode.DARK
    page.bgcolor = FONDO
    page.padding = 20
    page.spacing = 0

    db = DBManager()
    # Cambia a "Operario" para probar sin precio_compra
    contenido = await vista_inventario(page, db, nombre_rol="Administrador")
    page.add(contenido)

if __name__ == "__main__":
    ft.app(target=_main_standalone)