"""
inventario.py — Módulo de Inventario v2
=========================================
- Vista de tabla con filtros y alertas
- Modal: Agregar producto con presentaciones y stock inicial
- Modal: Editar producto existente
- Modal: Registrar entrada de mercancía
- Desactivar producto (sin borrar historial)

Prueba independiente:
    python src/ui/inventario.py
"""

import flet as ft
import uuid
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

def obtener_producto_completo(db, id_producto):
    """Trae todos los datos de un producto incluyendo sus presentaciones."""
    prod = db.fetch_one("""
        SELECT p.*, tp.nombre AS tipo_nombre
        FROM producto p
        JOIN tipo_producto tp ON tp.idTipoProducto = p.idTipoProducto
        WHERE p.idProducto = %s
    """, (id_producto,))
    pres = db.fetch_query("""
        SELECT * FROM producto_presentacion
        WHERE idProducto = %s ORDER BY es_unidad_base DESC, nombre_presentacion
    """, (id_producto,))
    return prod, pres

def agrupar_por_producto(filas, es_admin=False):
    productos = {}
    for fila in filas:
        pid = fila['idProducto']
        if pid not in productos:
            entrada = {
                'id':           pid,
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
# HELPERS UI
# ─────────────────────────────────────────────────────────────

def campo(label, hint="", password=False, valor="", teclado=ft.KeyboardType.TEXT, expand=True):
    return ft.TextField(
        label=label, hint_text=hint, value=str(valor),
        password=password, keyboard_type=teclado,
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13, cursor_color=VERDE,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        expand=expand,
    )

def dropdown_tipos(tipos, valor_inicial=None):
    return ft.Dropdown(
        label="Categoría",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        options=[ft.dropdown.Option(key=t['idTipoProducto'], text=t['nombre']) for t in tipos],
        value=valor_inicial,
        expand=True,
    )

def dropdown_unidad(valor_inicial="Litro"):
    return ft.Dropdown(
        label="Unidad base",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        options=[
            ft.dropdown.Option("Litro"),
            ft.dropdown.Option("Galón"),
            ft.dropdown.Option("Kilogramo"),
            ft.dropdown.Option("Gramo"),
            ft.dropdown.Option("Unidad"),
        ],
        value=valor_inicial,
        expand=True,
    )

def seccion_titulo(texto):
    return ft.Container(
        content=ft.Text(texto, size=13, color=VERDE_CLARO, weight=ft.FontWeight.W_600),
        border=ft.border.only(bottom=ft.border.BorderSide(1, BORDE)),
        padding=ft.padding.only(bottom=8),
        margin=ft.margin.only(top=12, bottom=8),
    )

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
        bgcolor=bg, border_radius=20,
        padding=ft.padding.symmetric(horizontal=10, vertical=3),
    )

def indicador_stock(stock_actual, stock_minimo):
    s, m = float(stock_actual), float(stock_minimo)
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

def tarjeta_resumen(icono, label, valor, color=TEXTO, on_click=None, seleccionada=False):
    borde_color  = color if seleccionada else BORDE
    borde_grosor = 2     if seleccionada else 1
    bg           = "#1a2433" if seleccionada else FONDO_CARD
    extras = []
    if on_click:
        extras.append(ft.Text(
            "Clic para quitar filtro" if seleccionada else "Clic para filtrar",
            size=10, color=TEXTO_GRIS, italic=True,
        ))
    return ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon(icono, color=color, size=20),
                ft.Text(label, size=12, color=TEXTO_GRIS),
            ], spacing=8),
            ft.Text(str(valor), size=22, color=color, weight=ft.FontWeight.BOLD),
            *extras,
        ], spacing=4),
        bgcolor=bg,
        border=ft.border.all(borde_grosor, borde_color),
        border_radius=10,
        padding=ft.padding.symmetric(horizontal=20, vertical=14),
        expand=True,
        on_click=on_click,
        ink=bool(on_click),
        tooltip="Filtrar" if on_click and not seleccionada else ("Quitar filtro" if seleccionada else None),
    )

def btn_filtro(texto, activo, on_click):
    return ft.Container(
        content=ft.Text(
            texto, size=12,
            color="white" if activo else TEXTO_GRIS,
            weight=ft.FontWeight.W_600 if activo else ft.FontWeight.W_400,
        ),
        bgcolor=VERDE if activo else "#1a1f25",
        border=ft.border.all(1, VERDE if activo else BORDE),
        border_radius=20,
        padding=ft.padding.symmetric(horizontal=14, vertical=6),
        on_click=on_click, ink=True,
    )

def _hover(e, bg_original):
    e.control.bgcolor = "#1a2433" if e.data == "true" else bg_original
    e.control.update()

def encabezado_tabla(ubicaciones, es_admin=False):
    cols = [("Producto", 200), ("Categoría", 120)]
    for ub in ubicaciones:
        cols.append((ub['nombreUbicacion'], 140))
    cols += [("Stock Total", 100), ("Unidad", 90), ("Precio Venta", 110)]
    if es_admin:
        cols.append(("Precio Compra", 120))
    cols.append(("Acciones", 100))
    return ft.Container(
        content=ft.Row([
            ft.Container(
                content=ft.Text(h, size=12, color=TEXTO_GRIS, weight=ft.FontWeight.W_600),
                width=w,
                padding=ft.padding.symmetric(horizontal=12, vertical=12),
            ) for h, w in cols
        ], spacing=0),
        bgcolor="#080c10",
        border=ft.border.only(
            bottom=ft.border.BorderSide(2, VERDE),
            top=ft.border.BorderSide(1, BORDE),
        ),
    )


# ─────────────────────────────────────────────────────────────
# MODALES
# ─────────────────────────────────────────────────────────────

def modal_agregar_producto(page, db, tipos, ubicaciones, es_admin, on_guardado):
    """Modal para crear un producto nuevo con presentaciones y stock inicial."""

    presentaciones_state = []  # lista de dicts con los datos de cada presentación

    # ── Campos principales ──
    f_nombre     = campo("Nombre del producto *", "Ej: Roundup 480")
    f_precio_v   = campo("Precio venta *", "0", teclado=ft.KeyboardType.NUMBER)
    f_precio_c   = campo("Precio compra", "0", teclado=ft.KeyboardType.NUMBER) if es_admin else None
    f_stock_min  = campo("Stock mínimo *", "5", teclado=ft.KeyboardType.NUMBER)
    dd_tipo      = dropdown_tipos(tipos)
    dd_unidad    = dropdown_unidad()

    # ── Sección presentaciones ──
    lista_pres   = ft.Column(spacing=6)
    msg_pres     = ft.Text("", size=12, color=ROJO)

    f_pres_nombre    = campo("Nombre de la presentación *", "Ej: Galón, Costal, Caja x12", expand=True)
    f_pres_precio    = campo("Precio de venta *", "0", teclado=ft.KeyboardType.NUMBER, expand=False)
    f_pres_precio.width = 150
    cb_base = ft.Checkbox(label="Esta presentación ES la unidad base", value=False,
                          active_color=VERDE, check_color="white")

    # Campo de cantidad: su label cambia según la unidad base seleccionada
    f_pres_cantidad  = campo("¿Cuántas unidades base contiene? *", "1",
                             teclado=ft.KeyboardType.NUMBER, expand=False)
    f_pres_cantidad.width = 230

    # Texto de ayuda dinámico
    hint_equivalencia = ft.Text("", size=12, color=TEXTO_GRIS, italic=True)
    # Contenedor del campo cantidad (se oculta si es unidad base)
    contenedor_cantidad = ft.Column([f_pres_cantidad], spacing=4, visible=True)

    def actualizar_hint(e=None):
        nombre   = f_pres_nombre.value.strip() or "esta presentación"
        unidad   = dd_unidad.value or "unidad base"
        cantidad = f_pres_cantidad.value.strip()
        # Actualizar label del campo cantidad
        f_pres_cantidad.label = f"¿Cuántos {unidad}s tiene 1 {nombre}? *"
        try:
            cant_f = float(cantidad)
            hint_equivalencia.value = f'Equivale a {cant_f:g} {unidad}{"s" if cant_f != 1 else ""} en inventario'
        except ValueError:
            hint_equivalencia.value = ""
        page.update()

    def on_cb_base(e):
        # Si marca como unidad base, ocultar campo cantidad (factor = 1 automático)
        es_base = cb_base.value
        contenedor_cantidad.visible = not es_base
        if es_base:
            f_pres_cantidad.value = "1"
            hint_equivalencia.value = ""
        page.update()

    cb_base.on_change         = on_cb_base
    f_pres_nombre.on_change   = actualizar_hint
    f_pres_cantidad.on_change = actualizar_hint
    dd_unidad.on_change       = actualizar_hint

    def agregar_presentacion(e):
        nombre   = f_pres_nombre.value.strip()
        cantidad = f_pres_cantidad.value.strip()
        precio   = f_pres_precio.value.strip()

        if not nombre or not cantidad:
            msg_pres.value = "Nombre y cantidad son obligatorios"
            page.update()
            return

        try:
            factor_f = float(cantidad)
            precio_f = float(precio) if precio else 0
        except ValueError:
            msg_pres.value = "La cantidad y el precio deben ser números"
            page.update()
            return

        if factor_f <= 0:
            msg_pres.value = "La cantidad debe ser mayor a 0"
            page.update()
            return

        if cb_base.value:
            for p in presentaciones_state:
                p['es_base'] = False

        pres = {
            'nombre':  nombre,
            'factor':  factor_f,
            'precio':  precio_f,
            'es_base': cb_base.value,
        }
        presentaciones_state.append(pres)
        f_pres_nombre.value   = ""
        f_pres_cantidad.value = "1"
        f_pres_precio.value   = "0"
        cb_base.value         = False
        msg_pres.value        = ""
        hint_equivalencia.value = ""
        reconstruir_lista_pres()
        page.update()

    def eliminar_pres(idx):
        presentaciones_state.pop(idx)
        reconstruir_lista_pres()
        page.update()

    def reconstruir_lista_pres():
        lista_pres.controls.clear()
        for i, p in enumerate(presentaciones_state):
            base_badge = ft.Container(
                content=ft.Text("BASE", size=10, color=VERDE_CLARO, weight=ft.FontWeight.W_600),
                bgcolor="#0d2b0d", border_radius=4,
                padding=ft.padding.symmetric(horizontal=6, vertical=2),
                visible=p['es_base'],
            )
            lista_pres.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(p['nombre'], size=13, color=TEXTO, expand=True),
                        ft.Text(f"×{p['factor']}", size=12, color=TEXTO_GRIS, width=60),
                        ft.Text(f"${p['precio']:,.0f}", size=12, color=VERDE_CLARO, width=90),
                        base_badge,
                        ft.IconButton(
                            icon="delete_outline_rounded", icon_color=ROJO,
                            icon_size=18, tooltip="Eliminar",
                            on_click=lambda e, idx=i: eliminar_pres(idx),
                        ),
                    ], spacing=8),
                    bgcolor="#1a1f25",
                    border=ft.border.all(1, BORDE),
                    border_radius=8,
                    padding=ft.padding.symmetric(horizontal=12, vertical=6),
                )
            )

    # ── Sección stock inicial ──
    stocks_fields = {}
    stock_rows = ft.Column(spacing=6)
    for ub in ubicaciones:
        f = campo(ub['nombreUbicacion'], "0", teclado=ft.KeyboardType.NUMBER)
        f.value = "0"
        stocks_fields[ub['idUbicacion']] = f
        stock_rows.controls.append(f)

    # ── Mensaje de error/éxito ──
    msg_global = ft.Text("", size=13, color=ROJO)

    def guardar(e):
        # Validaciones
        nombre = f_nombre.value.strip()
        if not nombre:
            msg_global.value = "El nombre del producto es obligatorio"
            page.update()
            return
        if not dd_tipo.value:
            msg_global.value = "Selecciona una categoría"
            page.update()
            return
        if not dd_unidad.value:
            msg_global.value = "Selecciona la unidad base"
            page.update()
            return
        try:
            precio_v = float(f_precio_v.value or 0)
            precio_c = float(f_precio_c.value or 0) if f_precio_c else 0
            stk_min  = float(f_stock_min.value or 5)
        except ValueError:
            msg_global.value = "Precios y stock mínimo deben ser números"
            page.update()
            return
        if not presentaciones_state:
            msg_global.value = "Agrega al menos una presentación"
            page.update()
            return
        if not any(p['es_base'] for p in presentaciones_state):
            msg_global.value = "Marca una presentación como unidad base"
            page.update()
            return

        # Construir operaciones transaccionales
        id_producto = str(uuid.uuid4())
        ops = []

        # Insertar producto
        if es_admin:
            ops.append((
                """INSERT INTO producto
                   (idProducto, nombre, idTipoProducto, unidad_medida_base,
                    precio_lista, precio_compra, stock_minimo, activo, sincronizado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,1,0)""",
                (id_producto, nombre, dd_tipo.value, dd_unidad.value,
                 precio_v, precio_c, stk_min)
            ))
        else:
            ops.append((
                """INSERT INTO producto
                   (idProducto, nombre, idTipoProducto, unidad_medida_base,
                    precio_lista, stock_minimo, activo, sincronizado)
                   VALUES (%s,%s,%s,%s,%s,%s,1,0)""",
                (id_producto, nombre, dd_tipo.value, dd_unidad.value, precio_v, stk_min)
            ))

        # Insertar presentaciones
        for p in presentaciones_state:
            ops.append((
                """INSERT INTO producto_presentacion
                   (idPresentacion, idProducto, nombre_presentacion,
                    factor_conversion, es_unidad_base, precio_sugerido)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (str(uuid.uuid4()), id_producto, p['nombre'],
                 p['factor'], 1 if p['es_base'] else 0, p['precio'])
            ))

        # Insertar inventario inicial por ubicación
        for uid_ubic, f_stk in stocks_fields.items():
            stk_val = float(f_stk.value or 0)
            ops.append((
                """INSERT INTO inventario
                   (idInventario, idUbicacion, idProducto, stockActual)
                   VALUES (%s,%s,%s,%s)""",
                (str(uuid.uuid4()), uid_ubic, id_producto, stk_val)
            ))

        result = db.run_transaction(ops)
        if result['success']:
            msg_global.value = ""
            page.close(dlg)
            on_guardado()
        else:
            msg_global.value = f"Error al guardar: {result['error']}"
            page.update()

    # ── Construcción del modal ──
    campos_admin = [f_precio_c] if f_precio_c else []

    contenido_modal = ft.Column([
        seccion_titulo("Datos del Producto"),
        f_nombre,
        ft.Row([dd_tipo, dd_unidad], spacing=10),
        ft.Row([f_precio_v] + campos_admin + [f_stock_min], spacing=10),

        seccion_titulo("Presentaciones"),
        ft.Container(
            content=ft.Column([
                ft.Row([f_pres_nombre, f_pres_precio], spacing=8),
                ft.Row([
                    cb_base,
                    ft.Container(expand=True),
                    ft.Container(
                        content=ft.Text("+ Agregar", size=12, color="white",
                                        weight=ft.FontWeight.W_600),
                        bgcolor=VERDE, border_radius=8,
                        padding=ft.padding.symmetric(horizontal=16, vertical=8),
                        on_click=agregar_presentacion, ink=True,
                    ),
                ]),
                contenedor_cantidad,
                hint_equivalencia,
                msg_pres,
            ], spacing=8),
            bgcolor="#12181f", border=ft.border.all(1, BORDE),
            border_radius=8, padding=12,
        ),
        lista_pres,

        seccion_titulo("Stock Inicial por Ubicación"),
        stock_rows,

        ft.Container(height=8),
        msg_global,

    ], scroll=ft.ScrollMode.AUTO, spacing=6, width=580)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("add_box_rounded", color=VERDE, size=22),
            ft.Text("Agregar Producto", size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=contenido_modal,
        content_padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=FONDO_CARD,
        actions=[
            ft.TextButton("Cancelar", style=ft.ButtonStyle(color=TEXTO_GRIS),
                          on_click=lambda e: page.close(dlg)),
            ft.Container(
                content=ft.Text("Guardar Producto", size=13, color="white",
                                weight=ft.FontWeight.W_600),
                bgcolor=VERDE, border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                on_click=guardar, ink=True,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def modal_editar_producto(page, db, id_producto, tipos, es_admin, on_guardado):
    """Modal para editar un producto existente."""
    prod, pres = obtener_producto_completo(db, id_producto)
    if not prod:
        return None

    f_nombre    = campo("Nombre *", valor=prod['nombre'])
    f_precio_v  = campo("Precio venta *", teclado=ft.KeyboardType.NUMBER, valor=prod['precio_lista'])
    f_precio_c  = campo("Precio compra", teclado=ft.KeyboardType.NUMBER,
                        valor=prod.get('precio_compra', 0)) if es_admin else None
    f_stock_min = campo("Stock mínimo *", teclado=ft.KeyboardType.NUMBER, valor=prod['stock_minimo'])
    dd_tipo     = dropdown_tipos(tipos, valor_inicial=prod['idTipoProducto'])
    dd_unidad   = dropdown_unidad(valor_inicial=prod['unidad_medida_base'])

    msg_global  = ft.Text("", size=13, color=ROJO)

    # Lista de presentaciones (solo lectura en edición simple)
    pres_lista = ft.Column([
        ft.Container(
            content=ft.Row([
                ft.Text(p['nombre_presentacion'], size=13, color=TEXTO, expand=True),
                ft.Text(f"×{float(p['factor_conversion'])}", size=12, color=TEXTO_GRIS, width=60),
                ft.Text(f"${float(p['precio_sugerido']):,.0f}", size=12, color=VERDE_CLARO, width=90),
                ft.Container(
                    content=ft.Text("BASE", size=10, color=VERDE_CLARO, weight=ft.FontWeight.W_600),
                    bgcolor="#0d2b0d", border_radius=4,
                    padding=ft.padding.symmetric(horizontal=6, vertical=2),
                    visible=bool(p['es_unidad_base']),
                ),
            ], spacing=8),
            bgcolor="#1a1f25", border=ft.border.all(1, BORDE),
            border_radius=8,
            padding=ft.padding.symmetric(horizontal=12, vertical=6),
        )
        for p in pres
    ], spacing=6)

    def guardar(e):
        nombre = f_nombre.value.strip()
        if not nombre or not dd_tipo.value:
            msg_global.value = "Nombre y categoría son obligatorios"
            page.update()
            return
        try:
            precio_v = float(f_precio_v.value or 0)
            precio_c = float(f_precio_c.value or 0) if f_precio_c else None
            stk_min  = float(f_stock_min.value or 5)
        except ValueError:
            msg_global.value = "Precios y stock mínimo deben ser números"
            page.update()
            return

        if es_admin and precio_c is not None:
            result = db.run_query(
                """UPDATE producto SET nombre=%s, idTipoProducto=%s, unidad_medida_base=%s,
                   precio_lista=%s, precio_compra=%s, stock_minimo=%s WHERE idProducto=%s""",
                (nombre, dd_tipo.value, dd_unidad.value, precio_v, precio_c, stk_min, id_producto)
            )
        else:
            result = db.run_query(
                """UPDATE producto SET nombre=%s, idTipoProducto=%s, unidad_medida_base=%s,
                   precio_lista=%s, stock_minimo=%s WHERE idProducto=%s""",
                (nombre, dd_tipo.value, dd_unidad.value, precio_v, stk_min, id_producto)
            )

        if result['success']:
            page.close(dlg)
            on_guardado()
        else:
            msg_global.value = "Error al guardar cambios"
            page.update()

    campos_admin = [f_precio_c] if f_precio_c else []

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("edit_rounded", color=AMARILLO, size=22),
            ft.Text("Editar Producto", size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            seccion_titulo("Datos del Producto"),
            f_nombre,
            ft.Row([dd_tipo, dd_unidad], spacing=10),
            ft.Row([f_precio_v] + campos_admin + [f_stock_min], spacing=10),
            seccion_titulo("Presentaciones actuales"),
            pres_lista,
            ft.Container(height=8),
            msg_global,
        ], scroll=ft.ScrollMode.AUTO, spacing=6, width=560),
        content_padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=FONDO_CARD,
        actions=[
            ft.TextButton("Cancelar", style=ft.ButtonStyle(color=TEXTO_GRIS),
                          on_click=lambda e: page.close(dlg)),
            ft.Container(
                content=ft.Text("Guardar Cambios", size=13, color="white",
                                weight=ft.FontWeight.W_600),
                bgcolor=AMARILLO, border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                on_click=guardar, ink=True,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def modal_desactivar(page, db, id_producto, nombre_producto, on_guardado):
    """Modal de confirmación para desactivar un producto."""

    def confirmar(e):
        result = db.run_query(
            "UPDATE producto SET activo = 0 WHERE idProducto = %s",
            (id_producto,)
        )
        if result['success']:
            page.close(dlg)
            on_guardado()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("warning_rounded", color=ROJO, size=22),
            ft.Text("Desactivar Producto", size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            ft.Text(f'¿Desactivar "{nombre_producto}"?', size=14, color=TEXTO),
            ft.Container(height=4),
            ft.Text(
                "El producto no aparecerá en el inventario ni en ventas, "
                "pero su historial de movimientos y facturas se conserva intacto.",
                size=12, color=TEXTO_GRIS,
            ),
        ], spacing=6, width=400),
        content_padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=FONDO_CARD,
        actions=[
            ft.TextButton("Cancelar", style=ft.ButtonStyle(color=TEXTO_GRIS),
                          on_click=lambda e: page.close(dlg)),
            ft.Container(
                content=ft.Text("Sí, desactivar", size=13, color="white",
                                weight=ft.FontWeight.W_600),
                bgcolor=ROJO, border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                on_click=confirmar, ink=True,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


def modal_entrada(page, db, ubicaciones, on_guardado):
    """Modal para registrar entrada de mercancía a una ubicación."""

    # Buscar producto
    resultados_busqueda = ft.Column(spacing=4)
    producto_seleccionado = {"id": None, "nombre": None, "presentaciones": []}
    pres_seleccionada     = {"id": None, "factor": 1.0}

    f_buscar    = campo("Buscar producto *", "Escribe el nombre...")
    msg_buscar  = ft.Text("", size=12, color=TEXTO_GRIS)
    dd_pres     = ft.Dropdown(
        label="Presentación",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13, visible=False,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        expand=True,
    )
    dd_ubic     = ft.Dropdown(
        label="Ubicación destino *",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        options=[ft.dropdown.Option(key=u['idUbicacion'], text=u['nombreUbicacion'])
                 for u in ubicaciones],
        expand=True,
    )
    f_cantidad  = campo("Cantidad *", "0", teclado=ft.KeyboardType.NUMBER)
    f_obs       = campo("Observación (opcional)", "")
    msg_global  = ft.Text("", size=13, color=ROJO)
    label_prod  = ft.Text("", size=13, color=VERDE_CLARO, weight=ft.FontWeight.W_600)

    def buscar_producto(e):
        texto = f_buscar.value.strip()
        resultados_busqueda.controls.clear()
        if len(texto) < 2:
            msg_buscar.value = "Escribe al menos 2 caracteres"
            page.update()
            return
        msg_buscar.value = ""
        prods = db.fetch_query(
            "SELECT idProducto, nombre FROM producto WHERE nombre LIKE %s AND activo=1 LIMIT 6",
            (f"%{texto}%",)
        )
        if not prods:
            msg_buscar.value = "Sin resultados"
        for p in prods:
            resultados_busqueda.controls.append(
                ft.Container(
                    content=ft.Text(p['nombre'], size=13, color=TEXTO),
                    bgcolor="#1a1f25", border=ft.border.all(1, BORDE),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    on_click=lambda e, prod=p: seleccionar_producto(prod),
                    ink=True,
                )
            )
        page.update()

    def seleccionar_producto(prod):
        producto_seleccionado['id']     = prod['idProducto']
        producto_seleccionado['nombre'] = prod['nombre']
        label_prod.value = f"✔ {prod['nombre']}"
        f_buscar.value   = prod['nombre']
        resultados_busqueda.controls.clear()

        pres = db.fetch_query(
            "SELECT idPresentacion, nombre_presentacion, factor_conversion "
            "FROM producto_presentacion WHERE idProducto=%s ORDER BY es_unidad_base DESC",
            (prod['idProducto'],)
        )
        producto_seleccionado['presentaciones'] = pres
        dd_pres.options = [
            ft.dropdown.Option(key=p['idPresentacion'],
                               text=f"{p['nombre_presentacion']} (×{float(p['factor_conversion'])})")
            for p in pres
        ]
        dd_pres.value   = pres[0]['idPresentacion'] if pres else None
        dd_pres.visible = True
        if pres:
            pres_seleccionada['id']     = pres[0]['idPresentacion']
            pres_seleccionada['factor'] = float(pres[0]['factor_conversion'])
        page.update()

    def on_pres_change(e):
        for p in producto_seleccionado['presentaciones']:
            if p['idPresentacion'] == e.control.value:
                pres_seleccionada['id']     = p['idPresentacion']
                pres_seleccionada['factor'] = float(p['factor_conversion'])
                break

    dd_pres.on_change = on_pres_change
    f_buscar.on_change = buscar_producto

    def guardar(e):
        if not producto_seleccionado['id']:
            msg_global.value = "Selecciona un producto"
            page.update()
            return
        if not dd_ubic.value:
            msg_global.value = "Selecciona la ubicación destino"
            page.update()
            return
        try:
            cantidad = float(f_cantidad.value or 0)
        except ValueError:
            msg_global.value = "La cantidad debe ser un número"
            page.update()
            return
        if cantidad <= 0:
            msg_global.value = "La cantidad debe ser mayor a 0"
            page.update()
            return

        cantidad_base = cantidad * pres_seleccionada['factor']
        id_mov        = str(uuid.uuid4())
        id_det        = str(uuid.uuid4())

        ops = [
            # Cabecera del movimiento
            ("""INSERT INTO movimiento
                (idMovimiento, tipo, fecha, idUbicacionDestino, idUsuario, observacion, sincronizado)
                VALUES (%s,'ENTRADA',NOW(),%s,
                (SELECT idUsuario FROM usuario WHERE estado=1 LIMIT 1),
                %s, 0)""",
             (id_mov, dd_ubic.value, f_obs.value.strip() or "Entrada de mercancía")),

            # Detalle
            ("""INSERT INTO movimiento_detalle
                (idDetalle, idMovimiento, idProducto, idPresentacion,
                 cantidad, cantidad_base, precio_unitario_aplicado)
                VALUES (%s,%s,%s,%s,%s,%s,0)""",
             (id_det, id_mov, producto_seleccionado['id'],
              pres_seleccionada['id'], cantidad, cantidad_base)),

            # Actualizar inventario
            ("""INSERT INTO inventario (idInventario, idUbicacion, idProducto, stockActual)
                VALUES (%s,%s,%s,%s)
                ON DUPLICATE KEY UPDATE stockActual = stockActual + %s""",
             (str(uuid.uuid4()), dd_ubic.value, producto_seleccionado['id'],
              cantidad_base, cantidad_base)),
        ]

        result = db.run_transaction(ops)
        if result['success']:
            page.close(dlg)
            on_guardado()
        else:
            msg_global.value = f"Error: {result['error']}"
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("move_to_inbox_rounded", color=VERDE_CLARO, size=22),
            ft.Text("Registrar Entrada de Mercancía", size=18,
                    weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            seccion_titulo("Producto"),
            f_buscar,
            msg_buscar,
            resultados_busqueda,
            label_prod,
            dd_pres,
            seccion_titulo("Cantidad y Destino"),
            ft.Row([f_cantidad, dd_ubic], spacing=10),
            f_obs,
            ft.Container(height=8),
            msg_global,
        ], scroll=ft.ScrollMode.AUTO, spacing=6, width=520),
        content_padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=FONDO_CARD,
        actions=[
            ft.TextButton("Cancelar", style=ft.ButtonStyle(color=TEXTO_GRIS),
                          on_click=lambda e: page.close(dlg)),
            ft.Container(
                content=ft.Text("Registrar Entrada", size=13, color="white",
                                weight=ft.FontWeight.W_600),
                bgcolor=VERDE_CLARO, border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                on_click=guardar, ink=True,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


# ─────────────────────────────────────────────────────────────
# FILA DE PRODUCTO CON ACCIONES
# ─────────────────────────────────────────────────────────────

def fila_producto(producto, ubicaciones, indice, es_admin, on_editar, on_desactivar):
    bg = FONDO_FILA if indice % 2 == 0 else FONDO_FILA_ALT
    stock_total = sum(float(v) for v in producto['stocks'].values())

    celdas = [
        celda(ft.Text(producto['nombre'], size=13, color=TEXTO,
                      weight=ft.FontWeight.W_500), ancho=200),
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
        celdas.append(celda(ft.Text(f"${pc:,.0f}", size=13, color="#ef9a9a"), ancho=120))

    # Acciones inline
    celdas.append(celda(
        ft.Row([
            ft.IconButton(
                icon="edit_rounded", icon_color=AMARILLO,
                icon_size=18, tooltip="Editar",
                on_click=lambda e, pid=producto['id'], pnom=producto['nombre']:
                    on_editar(pid, pnom),
            ),
            ft.IconButton(
                icon="visibility_off_rounded", icon_color=ROJO,
                icon_size=18, tooltip="Desactivar",
                on_click=lambda e, pid=producto['id'], pnom=producto['nombre']:
                    on_desactivar(pid, pnom),
            ),
        ], spacing=0),
        ancho=100
    ))

    return ft.Container(
        content=ft.Row(celdas, spacing=0),
        bgcolor=bg,
        border=ft.border.only(bottom=ft.border.BorderSide(1, BORDE)),
        on_hover=lambda e: _hover(e, bg),
    )


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────

async def vista_inventario(page: ft.Page, db: DBManager, nombre_rol: str = ROL_ADMIN):

    es_admin    = (nombre_rol == ROL_ADMIN)
    ubicaciones = obtener_ubicaciones(db)
    tipos       = obtener_tipos(db)

    estado = {"tipo": None, "texto": None, "alerta": None}

    resumen_row  = ft.Row(spacing=12)
    filtros_row  = ft.Row(spacing=8, wrap=True)
    cuerpo_tabla = ft.Column(spacing=0)

    tabla_scroll   = ft.Row(controls=[cuerpo_tabla], scroll=ft.ScrollMode.AUTO, spacing=0)
    tabla_vertical = ft.Column(controls=[tabla_scroll], scroll=ft.ScrollMode.AUTO,
                               expand=True, spacing=0)

    # ── Helpers ──

    def calcular_resumen(prods):
        total    = len(prods)
        criticos = sum(1 for p in prods if any(
            float(v) <= float(p['stock_minimo']) for v in p['stocks'].values()
        ))
        sin_stk  = sum(1 for p in prods if any(
            float(v) <= 0 for v in p['stocks'].values()
        ))
        return total, criticos, sin_stk

    def refrescar_todo():
        filas = obtener_stock(db, estado["tipo"], estado["texto"], es_admin)
        prods = agrupar_por_producto(filas, es_admin)
        if estado["alerta"] == "critico":
            prods_tabla = [p for p in prods if any(
                float(v) <= float(p['stock_minimo']) for v in p['stocks'].values()
            )]
        elif estado["alerta"] == "sin_stock":
            prods_tabla = [p for p in prods if any(
                float(v) <= 0 for v in p['stocks'].values()
            )]
        else:
            prods_tabla = prods
        reconstruir_resumen(prods)
        reconstruir_tabla(prods_tabla)
        page.update()

    def reconstruir_resumen(prods):
        filas_base = obtener_stock(db, estado["tipo"], estado["texto"], es_admin)
        base       = agrupar_por_producto(filas_base, es_admin)
        total, criticos, sin_stk = calcular_resumen(base)

        def click_critico(e):
            estado["alerta"] = None if estado["alerta"] == "critico" else "critico"
            refrescar_todo()

        def click_sin_stock(e):
            estado["alerta"] = None if estado["alerta"] == "sin_stock" else "sin_stock"
            refrescar_todo()

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
                alignment=ft.alignment.center, padding=60, width=800,
            ))
        else:
            for i, prod in enumerate(prods):
                cuerpo_tabla.controls.append(
                    fila_producto(prod, ubicaciones, i, es_admin,
                                  on_editar=abrir_editar,
                                  on_desactivar=abrir_desactivar)
                )

    def reconstruir_filtros():
        filtros_row.controls.clear()
        filtros_row.controls.append(btn_filtro(
            "Todos", activo=(estado["tipo"] is None),
            on_click=lambda e: _filtrar_tipo(None)
        ))
        for t in tipos:
            tid, nombre = t['idTipoProducto'], t['nombre']
            filtros_row.controls.append(btn_filtro(
                nombre, activo=(estado["tipo"] == tid),
                on_click=lambda e, i=tid: _filtrar_tipo(i)
            ))

    def _filtrar_tipo(tipo_id):
        estado["tipo"] = tipo_id
        reconstruir_filtros()
        refrescar_todo()

    def on_buscar(e):
        estado["texto"] = e.control.value.strip() or None
        refrescar_todo()

    def on_refrescar(e):
        btn_refrescar.disabled   = True
        btn_refrescar.icon_color = TEXTO_GRIS
        page.update()
        estado["tipo"]   = None
        estado["texto"]  = None
        estado["alerta"] = None
        buscador.value   = ""
        reconstruir_filtros()
        refrescar_todo()
        btn_refrescar.disabled   = False
        btn_refrescar.icon_color = VERDE_CLARO
        page.update()

    # ── Acciones de filas ──

    def abrir_editar(id_producto, nombre_producto):
        dlg = modal_editar_producto(page, db, id_producto, tipos, es_admin,
                                    on_guardado=refrescar_todo)
        if dlg:
            page.open(dlg)

    def abrir_desactivar(id_producto, nombre_producto):
        dlg = modal_desactivar(page, db, id_producto, nombre_producto,
                               on_guardado=refrescar_todo)
        page.open(dlg)

    def abrir_agregar(e):
        dlg = modal_agregar_producto(page, db, tipos, ubicaciones, es_admin,
                                     on_guardado=refrescar_todo)
        page.open(dlg)

    def abrir_entrada(e):
        dlg = modal_entrada(page, db, ubicaciones, on_guardado=refrescar_todo)
        page.open(dlg)

    # ── Componentes ──

    buscador = ft.TextField(
        hint_text="Buscar producto por nombre...",
        prefix_icon="search_rounded",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13, height=42, cursor_color=VERDE,
        expand=True, on_change=on_buscar,
    )

    btn_refrescar = ft.IconButton(
        icon="refresh_rounded", icon_color=VERDE_CLARO,
        tooltip="Refrescar tabla", on_click=on_refrescar,
    )

    btn_agregar = ft.Container(
        content=ft.Row([
            ft.Icon("add_rounded", color="white", size=18),
            ft.Text("Agregar Producto", size=13, color="white", weight=ft.FontWeight.W_600),
        ], spacing=6),
        bgcolor=VERDE, border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        on_click=abrir_agregar, ink=True,
        visible=es_admin,
    )

    btn_entrada = ft.Container(
        content=ft.Row([
            ft.Icon("move_to_inbox_rounded", color="white", size=18),
            ft.Text("Registrar Entrada", size=13, color="white", weight=ft.FontWeight.W_600),
        ], spacing=6),
        bgcolor="#1565c0", border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        on_click=abrir_entrada, ink=True,
    )

    reconstruir_filtros()

    # ── Layout ──
    contenido = ft.Column([

        ft.Row([
            ft.Column([
                ft.Text("Inventario y Stock", size=26,
                        weight=ft.FontWeight.BOLD, color=TEXTO),
                ft.Text("Productos disponibles por ubicación", size=13, color=TEXTO_GRIS),
            ], spacing=2, expand=True),
            ft.Row([btn_entrada, btn_agregar, btn_refrescar], spacing=8),
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
            bgcolor=FONDO_CARD, border=ft.border.all(1, BORDE),
            border_radius=10,
            padding=ft.padding.symmetric(horizontal=16, vertical=12),
        ),

        ft.Container(height=12),

        ft.Container(
            content=tabla_vertical,
            bgcolor=FONDO_CARD, border=ft.border.all(1, BORDE),
            border_radius=10, expand=True,
            clip_behavior=ft.ClipBehavior.ANTI_ALIAS, padding=0,
        ),

    ], expand=True, spacing=0)

    # ── Carga inicial ──
    filas_ini = obtener_stock(db, None, None, es_admin)
    prods_ini = agrupar_por_producto(filas_ini, es_admin)
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
    contenido = await vista_inventario(page, db, nombre_rol="Administrador")
    page.add(contenido)

if __name__ == "__main__":
    ft.app(target=_main_standalone)