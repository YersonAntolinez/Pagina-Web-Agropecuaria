"""
inventario.py — Módulo de Inventario v3
=========================================
- Sin tabla producto_presentacion
- Vista de tabla con filtros y alertas
- Modal: Agregar producto con stock inicial por ubicación
- Modal: Editar producto
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
# UTILIDADES DE FORMATO
# ─────────────────────────────────────────────────────────────

def leer_num(valor_str):
    """Lee un número desde un campo formateado en colombiano. Ej: '100.000' -> 100000.0"""
    try:
        limpio = str(valor_str).strip().replace(".", "").replace(",", ".")
        return float(limpio) if limpio else 0.0
    except ValueError:
        return 0.0

def fmt_num(valor, decimales=1):
    """Formatea un número con separador de miles colombiano (punto)."""
    try:
        v = float(valor)
        if decimales == 0:
            return f"{v:,.0f}".replace(",", ".")
        else:
            # Formatear con decimales, luego convertir separadores
            s = f"{v:,.{decimales}f}"          # "1,234.5"
            partes = s.split(".")
            entero = partes[0].replace(",", ".")
            return f"{entero},{partes[1]}" if len(partes) > 1 else entero
    except (ValueError, TypeError):
        return str(valor)

def fmt_precio(valor):
    """Formatea un precio como $100.000"""
    try:
        return f"${float(valor):,.0f}".replace(",", ".")
    except (ValueError, TypeError):
        return "$0"

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

def obtener_unidades(db):
    return db.fetch_query(
        "SELECT nombre FROM unidad_medida ORDER BY nombre"
    )

def obtener_stock(db, filtro_tipo=None, filtro_texto=None, es_admin=False):
    campos_extra = ", p.costo_promedio" if es_admin else ""
    query = f"""
        SELECT
            p.idProducto,
            p.nombre             AS producto,
            tp.nombre            AS tipo,
            p.unidad_medida_base AS unidad,
            p.stock_minimo,
            p.precio_lista,
            p.precio_compra
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

def obtener_producto(db, id_producto):
    return db.fetch_one("""
        SELECT p.*, tp.nombre AS tipo_nombre
        FROM producto p
        JOIN tipo_producto tp ON tp.idTipoProducto = p.idTipoProducto
        WHERE p.idProducto = %s
    """, (id_producto,))

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
            entrada['precio_compra'] = fila.get('precio_compra', 0) or 0
            if es_admin:
                entrada['costo_promedio'] = fila.get('costo_promedio', 0) or 0
            productos[pid] = entrada
        productos[pid]['stocks'][fila['idUbicacion']] = fila['stock']
    return list(productos.values())


# ─────────────────────────────────────────────────────────────
# HELPERS UI
# ─────────────────────────────────────────────────────────────

def campo(label, hint="", valor="", teclado=ft.KeyboardType.TEXT, expand=True, ancho=None):
    """Retorna siempre un ft.TextField. Para campos numéricos, muestra preview formateado
    en un atributo .preview (ft.Text) que el caller puede agregar al layout si quiere."""

    def on_change(e):
        if teclado != ft.KeyboardType.NUMBER:
            return
        raw = e.control.value.strip()
        if not raw:
            e.control.preview.value = ""
        else:
            try:
                num = int(raw)
                e.control.preview.value = f"{num:,}".replace(",", ".")
            except ValueError:
                e.control.preview.value = ""
        e.control.preview.update()

    def on_focus(e):
        if teclado != ft.KeyboardType.NUMBER:
            return
        if e.control.value in ("0", ""):
            e.control.value = ""
            e.control.update()

    val_inicial = "" if str(valor) in ("0", "0.0", "") and teclado == ft.KeyboardType.NUMBER else str(valor)

    tf = ft.TextField(
        label=label, hint_text=hint, value=val_inicial,
        keyboard_type=teclado,
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=14, cursor_color=VERDE,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=13),
        on_change=on_change,
        on_focus=on_focus,
        expand=expand,
    )
    if ancho:
        tf.width = ancho

    # Adjuntar preview al TextField para acceso fácil
    tf.preview = ft.Text("", size=11, color=TEXTO_GRIS, italic=True)
    return tf

def campo_con_preview(f):
    """Envuelve un campo numérico con su preview alineado debajo."""
    return ft.Column([f, f.preview], spacing=2, expand=f.expand)

def dropdown_tipos(tipos, valor_inicial=None):
    return ft.Dropdown(
        label="Categoría *",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        options=[ft.dropdown.Option(key=t['idTipoProducto'], text=t['nombre']) for t in tipos],
        value=valor_inicial,
        expand=True,
    )

def dropdown_unidad(unidades, valor_inicial=None):
    return ft.Dropdown(
        label="Unidad de medida *",
        border_radius=8, bgcolor="#1a1f25",
        border_color=BORDE, focused_border_color=VERDE,
        text_size=13,
        label_style=ft.TextStyle(color=TEXTO_GRIS, size=12),
        options=[ft.dropdown.Option(u['nombre']) for u in unidades],
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
        color, icono, tip = AMARILLO,    "warning_rounded",      f"Crítico (mínimo: {fmt_num(m, 1)})"
    else:
        color, icono, tip = VERDE_STOCK, "check_circle_rounded", "Stock normal"
    return ft.Container(
        content=ft.Row([
            ft.Icon(icono, color=color, size=16),
            ft.Text(fmt_num(s, 1), size=13, color=color, weight=ft.FontWeight.W_600),
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
    cols += [("Stock Total", 100), ("Unidad", 90), ("Precio Venta", 110), ("Precio Compra", 120)]
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
        celda(ft.Text(fmt_num(stock_total, 1), size=13, color=TEXTO_GRIS), ancho=100),
        celda(ft.Text(producto['unidad'],     size=13, color=TEXTO_GRIS), ancho=90),
        celda(ft.Text(fmt_precio(producto['precio_lista']),
                      size=13, color=VERDE_CLARO), ancho=110),
    ]
    pc = float(producto.get('precio_compra') or 0)
    celdas.append(celda(ft.Text(fmt_precio(pc), size=13, color="#ef9a9a"), ancho=120))

    celdas.append(celda(
        ft.Row([
            ft.IconButton(
                icon="edit_rounded", icon_color=AMARILLO,
                icon_size=18, tooltip="Editar producto",
                on_click=lambda e, pid=producto['id']: on_editar(pid),
            ),
            ft.IconButton(
                icon="visibility_off_rounded", icon_color=ROJO,
                icon_size=18, tooltip="Desactivar producto",
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
# MODALES
# ─────────────────────────────────────────────────────────────

def modal_agregar_producto(page, db, tipos, ubicaciones, unidades, es_admin, on_guardado):
    f_nombre    = campo("Nombre del producto *", "Ej: Roundup 480")
    f_precio_v  = campo("Precio de venta *", teclado=ft.KeyboardType.NUMBER, valor="0")
    f_precio_c  = campo("Precio de compra", teclado=ft.KeyboardType.NUMBER, valor="0") if es_admin else None
    f_stock_min = campo("Stock mínimo *", teclado=ft.KeyboardType.NUMBER, valor="5", expand=False, ancho=160)
    dd_tipo     = dropdown_tipos(tipos)
    dd_unidad   = dropdown_unidad(unidades)
    msg_global  = ft.Text("", size=13, color=ROJO)

    # Stock inicial por ubicación
    stocks_fields = {}
    stock_rows = ft.Column(spacing=8)
    for ub in ubicaciones:
        f = campo(f"Stock inicial — {ub['nombreUbicacion']}",
                  "0", teclado=ft.KeyboardType.NUMBER, valor="0")
        stocks_fields[ub['idUbicacion']] = f
        stock_rows.controls.append(campo_con_preview(f))

    def guardar(e):
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
            msg_global.value = "Selecciona la unidad de medida"
            page.update()
            return
        try:
            precio_v = leer_num(f_precio_v.value)
            precio_c = leer_num(f_precio_c.value) if f_precio_c else 0
            stk_min  = float(f_stock_min.value or 5)
        except ValueError:
            msg_global.value = "Precios y stock mínimo deben ser números"
            page.update()
            return

        id_producto = str(uuid.uuid4())
        ops = []

        if es_admin:
            ops.append((
                """INSERT INTO producto
                   (idProducto, nombre, idTipoProducto, unidad_medida_base,
                    precio_lista, precio_compra, costo_promedio, stock_minimo, activo, sincronizado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s,%s,1,0)""",
                (id_producto, nombre, dd_tipo.value, dd_unidad.value,
                 precio_v, precio_c, precio_c, stk_min)
            ))
        else:
            ops.append((
                """INSERT INTO producto
                   (idProducto, nombre, idTipoProducto, unidad_medida_base,
                    precio_lista, stock_minimo, activo, sincronizado)
                   VALUES (%s,%s,%s,%s,%s,%s,1,0)""",
                (id_producto, nombre, dd_tipo.value, dd_unidad.value, precio_v, stk_min)
            ))

        for uid_ubic, f_stk in stocks_fields.items():
            try:
                stk_val = leer_num(f_stk.value)
            except ValueError:
                stk_val = 0
            ops.append((
                """INSERT INTO inventario
                   (idInventario, idUbicacion, idProducto, stockActual)
                   VALUES (%s,%s,%s,%s)""",
                (str(uuid.uuid4()), uid_ubic, id_producto, stk_val)
            ))

        result = db.run_transaction(ops)
        if result['success']:
            page.close(dlg)
            on_guardado()
        else:
            msg_global.value = f"Error al guardar: {result.get('error', 'Error desconocido')}"
            page.update()

    campos_precio = [f_precio_v]
    if f_precio_c:
        campos_precio.append(f_precio_c)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("add_box_rounded", color=VERDE, size=22),
            ft.Text("Agregar Producto", size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            seccion_titulo("Datos del Producto"),
            f_nombre,
            ft.Container(height=4),
            ft.Row([dd_tipo, dd_unidad], spacing=12),
            ft.Container(height=4),
            ft.Row([campo_con_preview(c) for c in campos_precio] + [campo_con_preview(f_stock_min)], spacing=12),

            seccion_titulo("Stock Inicial por Ubicación"),
            ft.Text(
                "Ingresa el stock con el que arranca el producto en cada ubicación. "
                "Puedes dejar en 0 si aún no hay existencias.",
                size=13, color=TEXTO_GRIS,
            ),
            ft.Container(height=4),
            stock_rows,

            ft.Container(height=12),
            msg_global,
        ], scroll=ft.ScrollMode.AUTO, spacing=10, width=540),
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


def modal_editar_producto(page, db, id_producto, tipos, unidades, es_admin, on_guardado):
    prod = obtener_producto(db, id_producto)
    if not prod:
        return None

    f_nombre    = campo("Nombre *", valor=prod['nombre'])
    f_precio_v  = campo("Precio de venta *", teclado=ft.KeyboardType.NUMBER,
                        valor=prod['precio_lista'])
    f_precio_c  = campo("Precio de compra", teclado=ft.KeyboardType.NUMBER,
                        valor=prod.get('precio_compra', 0)) if es_admin else None
    f_stock_min = campo("Stock mínimo *", teclado=ft.KeyboardType.NUMBER,
                        valor=prod['stock_minimo'], expand=False, ancho=160)
    dd_tipo     = dropdown_tipos(tipos, valor_inicial=prod['idTipoProducto'])
    dd_unidad   = dropdown_unidad(unidades, valor_inicial=prod['unidad_medida_base'])
    msg_global  = ft.Text("", size=13, color=ROJO)

    def guardar(e):
        nombre = f_nombre.value.strip()
        if not nombre or not dd_tipo.value:
            msg_global.value = "Nombre y categoría son obligatorios"
            page.update()
            return
        try:
            precio_v = leer_num(f_precio_v.value)
            precio_c = leer_num(f_precio_c.value) if f_precio_c else None
            stk_min  = float(f_stock_min.value or 5)
        except ValueError:
            msg_global.value = "Precios y stock mínimo deben ser números"
            page.update()
            return

        if es_admin and precio_c is not None:
            result = db.run_query(
                """UPDATE producto SET nombre=%s, idTipoProducto=%s, unidad_medida_base=%s,
                   precio_lista=%s, precio_compra=%s, costo_promedio=%s, stock_minimo=%s WHERE idProducto=%s""",
                (nombre, dd_tipo.value, dd_unidad.value, precio_v, precio_c, precio_c, stk_min, id_producto)
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

    campos_precio = [f_precio_v]
    if f_precio_c:
        campos_precio.append(f_precio_c)

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("edit_rounded", color=AMARILLO, size=22),
            ft.Text("Editar Producto", size=18, weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            seccion_titulo("Datos del Producto"),
            f_nombre,
            ft.Container(height=4),
            ft.Row([dd_tipo, dd_unidad], spacing=12),
            ft.Container(height=4),
            ft.Row([campo_con_preview(c) for c in campos_precio] + [campo_con_preview(f_stock_min)], spacing=12),
            ft.Container(height=12),
            msg_global,
        ], scroll=ft.ScrollMode.AUTO, spacing=10, width=540),
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
    def confirmar(e):
        result = db.run_query(
            "UPDATE producto SET activo = 0 WHERE idProducto = %s", (id_producto,)
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
                "El producto desaparecerá del inventario y no podrá usarse en ventas, "
                "pero su historial de movimientos y facturas queda intacto.",
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
    resultados_busqueda   = ft.Column(spacing=4)
    producto_seleccionado = {"id": None, "nombre": None, "unidad": None,
                             "precio_compra": 0, "precio_lista": 0, "stock_total": 0}

    f_buscar     = campo("Buscar producto *", "Escribe el nombre...")
    msg_buscar   = ft.Text("", size=12, color=TEXTO_GRIS)
    label_prod   = ft.Text("", size=13, color=VERDE_CLARO, weight=ft.FontWeight.W_600)
    label_unidad = ft.Text("", size=12, color=TEXTO_GRIS, italic=True)

    f_precio_c   = campo("Precio de compra por unidad *", "0", teclado=ft.KeyboardType.NUMBER)
    f_obs        = campo("Observación (opcional)", "Ej: Pedido proveedor Agroquímicos S.A.")
    msg_global   = ft.Text("", size=13, color=ROJO)
    info_costo   = ft.Text("", size=12, color=TEXTO_GRIS, italic=True)

    # Panel de actualización de precio de venta
    panel_precio_venta = ft.Container(visible=False)
    f_precio_v_nuevo   = campo("Nuevo precio de venta", "0", teclado=ft.KeyboardType.NUMBER)
    cb_actualizar_pv   = ft.Checkbox(
        label="Actualizar precio de venta del producto",
        value=False, active_color=VERDE, check_color="white",
    )

    # Campos de cantidad por ubicación
    stocks_fields = {}
    stocks_col    = ft.Column(spacing=8)

    def construir_campos_ubicaciones(unidad="unidad"):
        stocks_col.controls.clear()
        stocks_fields.clear()
        for ub in ubicaciones:
            f = campo(
                f"{ub['nombreUbicacion']}",
                f"0 {unidad}",
                teclado=ft.KeyboardType.NUMBER,
                valor="0",
            )
            f.on_change = actualizar_info_costo
            stocks_fields[ub['idUbicacion']] = f
            stocks_col.controls.append(f)
            stocks_col.controls.append(f.preview)

    def cantidad_total():
        total = 0
        for f in stocks_fields.values():
            try:
                total += float(f.value or 0)
            except ValueError:
                pass
        return total

    def actualizar_info_costo(e=None):
        if not producto_seleccionado['id']:
            return
        try:
            cant_nueva  = cantidad_total()
            costo_nuevo = leer_num(f_precio_c.value)
        except ValueError:
            return

        stock_actual   = producto_seleccionado['stock_total']
        costo_actual   = producto_seleccionado['costo_promedio']
        total_unidades = stock_actual + cant_nueva

        if total_unidades > 0 and cant_nueva > 0:
            costo_promedio = ((stock_actual * costo_actual) + (cant_nueva * costo_nuevo)) / total_unidades
            info_costo.value = (
                f"Total a recibir: {fmt_num(cant_nueva)}  ·  "
                f"Stock actual: {fmt_num(stock_actual)}  ·  "
                f"Costo actual: {fmt_precio(costo_actual)}  →  "
                f"Nuevo costo promedio: {fmt_precio(costo_promedio)}"
            )
            costo_cambio = abs(costo_nuevo - costo_actual) > 0.01
            panel_precio_venta.visible = costo_cambio
            if costo_cambio:
                margen = producto_seleccionado['precio_lista'] - costo_actual
                f_precio_v_nuevo.value = str(int(costo_nuevo + margen)) if margen > 0 else str(int(producto_seleccionado['precio_lista']))
        else:
            info_costo.value = ""
            panel_precio_venta.visible = False
        page.update()

    f_precio_c.on_change = actualizar_info_costo

    def buscar_producto(e):
        texto = f_buscar.value.strip()
        resultados_busqueda.controls.clear()
        if len(texto) < 2:
            msg_buscar.value = "Escribe al menos 2 caracteres"
            page.update()
            return
        msg_buscar.value = ""
        prods = db.fetch_query(
            """SELECT idProducto, nombre, unidad_medida_base, precio_compra, costo_promedio, precio_lista
               FROM producto WHERE nombre LIKE %s AND activo=1 LIMIT 6""",
            (f"%{texto}%",)
        )
        if not prods:
            msg_buscar.value = "No se encontraron productos"
        for p in prods:
            resultados_busqueda.controls.append(
                ft.Container(
                    content=ft.Row([
                        ft.Text(p['nombre'], size=13, color=TEXTO, expand=True),
                        ft.Text(p['unidad_medida_base'], size=12, color=TEXTO_GRIS),
                    ]),
                    bgcolor="#1a1f25", border=ft.border.all(1, BORDE),
                    border_radius=6,
                    padding=ft.padding.symmetric(horizontal=12, vertical=8),
                    on_click=lambda e, prod=p: seleccionar_producto(prod),
                    ink=True,
                )
            )
        page.update()

    def seleccionar_producto(prod):
        stock_row = db.fetch_one(
            "SELECT COALESCE(SUM(stockActual),0) AS total FROM inventario WHERE idProducto=%s",
            (prod['idProducto'],)
        )
        stock_total = float(stock_row['total']) if stock_row else 0

        producto_seleccionado['id']           = prod['idProducto']
        producto_seleccionado['nombre']        = prod['nombre']
        producto_seleccionado['unidad']        = prod['unidad_medida_base']
        producto_seleccionado['precio_compra'] = float(prod.get('precio_compra') or 0)
        producto_seleccionado['costo_promedio']  = float(prod.get('costo_promedio') or 0)
        producto_seleccionado['precio_lista']  = float(prod['precio_lista'] or 0)
        producto_seleccionado['stock_total']   = stock_total

        f_buscar.value     = prod['nombre']
        label_prod.value   = f"✔  {prod['nombre']}"
        label_unidad.value = f"Unidad: {prod['unidad_medida_base']}"
        f_precio_c.value   = str(int(float(prod['precio_compra'] or 0)))
        resultados_busqueda.controls.clear()
        msg_buscar.value   = ""
        info_costo.value   = ""
        panel_precio_venta.visible = False
        construir_campos_ubicaciones(prod['unidad_medida_base'])
        page.update()

    f_buscar.on_change = buscar_producto

    panel_precio_venta.content = ft.Container(
        content=ft.Column([
            ft.Row([
                ft.Icon("info_outline_rounded", color=AMARILLO, size=16),
                ft.Text("El precio de compra cambió respecto al anterior",
                        size=12, color=AMARILLO),
            ], spacing=6),
            ft.Container(height=4),
            cb_actualizar_pv,
            f_precio_v_nuevo,
        ], spacing=6),
        bgcolor="#1a1a0a",
        border=ft.border.all(1, AMARILLO),
        border_radius=8,
        padding=12,
    )

    # Construir campos de ubicación vacíos al iniciar
    construir_campos_ubicaciones()

    def guardar(e):
        if not producto_seleccionado['id']:
            msg_global.value = "Selecciona un producto de la búsqueda"
            page.update()
            return
        try:
            precio_c = leer_num(f_precio_c.value)
        except ValueError:
            msg_global.value = "El precio de compra debe ser un número"
            page.update()
            return
        if precio_c < 0:
            msg_global.value = "El precio de compra no puede ser negativo"
            page.update()
            return

        # Validar que al menos una ubicación tenga cantidad > 0
        distribuciones = []
        for uid, f in stocks_fields.items():
            try:
                cant = float(f.value or 0)
            except ValueError:
                cant = 0
            if cant > 0:
                distribuciones.append((uid, cant))

        if not distribuciones:
            msg_global.value = "Ingresa la cantidad en al menos una ubicación"
            page.update()
            return

        cantidad_total_entrada = sum(c for _, c in distribuciones)

        # Calcular costo promedio ponderado
        stock_actual   = producto_seleccionado['stock_total']
        costo_actual   = producto_seleccionado['costo_promedio']
        total_unidades = stock_actual + cantidad_total_entrada
        costo_promedio = (
            ((stock_actual * costo_actual) + (cantidad_total_entrada * precio_c)) / total_unidades
            if total_unidades > 0 else precio_c
        )

        pid      = producto_seleccionado['id']
        obs      = f_obs.value.strip() or "Recepción de mercancía"
        id_mov   = str(uuid.uuid4())

        usuario = db.fetch_one("SELECT idUsuario FROM usuario WHERE estado=1 LIMIT 1")
        if not usuario:
            msg_global.value = "Error: no hay usuario activo en el sistema"
            page.update()
            return
        id_usuario = usuario['idUsuario']

        ops = [
            # Cabecera del movimiento (sin ubicación destino fija, va en los detalles)
            ("""INSERT INTO movimiento
                (idMovimiento, tipo, fecha, idUsuario, observacion, sincronizado)
                VALUES (%s,'ENTRADA',NOW(),%s,%s,0)""",
             (id_mov, id_usuario, obs)),

            # Actualizar costo promedio y precio de compra reciente
            ("UPDATE producto SET costo_promedio = %s, precio_compra = %s WHERE idProducto = %s",
             (round(costo_promedio, 2), precio_c, pid)),
        ]

        # Un detalle e inventario por cada ubicación con cantidad > 0
        for uid, cant in distribuciones:
            ops.append((
                """INSERT INTO movimiento_detalle
                   (idDetalle, idMovimiento, idProducto,
                    cantidad, cantidad_base, precio_unitario_aplicado, precio_costo)
                   VALUES (%s,%s,%s,%s,%s,0,%s)""",
                (str(uuid.uuid4()), id_mov, pid, cant, cant, precio_c)
            ))
            ops.append((
                """INSERT INTO inventario (idInventario, idUbicacion, idProducto, stockActual)
                   VALUES (%s,%s,%s,%s)
                   ON DUPLICATE KEY UPDATE stockActual = stockActual + %s""",
                (str(uuid.uuid4()), uid, pid, cant, cant)
            ))

        # Actualizar precio de venta si se marcó
        if cb_actualizar_pv.value and panel_precio_venta.visible:
            try:
                nuevo_pv = leer_num(f_precio_v_nuevo.value)
                if nuevo_pv > 0:
                    ops.append((
                        "UPDATE producto SET precio_lista = %s WHERE idProducto = %s",
                        (nuevo_pv, pid)
                    ))
            except ValueError:
                pass

        result = db.run_transaction(ops)
        if result['success']:
            page.close(dlg)
            on_guardado()
        else:
            msg_global.value = f"Error: {result.get('error', 'Error desconocido')}"
            page.update()

    dlg = ft.AlertDialog(
        modal=True,
        title=ft.Row([
            ft.Icon("move_to_inbox_rounded", color=VERDE_CLARO, size=22),
            ft.Text("Recepción de Mercancía", size=18,
                    weight=ft.FontWeight.BOLD, color=TEXTO),
        ], spacing=10),
        content=ft.Column([
            seccion_titulo("Producto"),
            f_buscar,
            msg_buscar,
            resultados_busqueda,
            label_prod,
            label_unidad,
            seccion_titulo("Precio de Compra"),
            campo_con_preview(f_precio_c),
            seccion_titulo("Distribución por Ubicación"),
            ft.Text(
                "Ingresa cuántas unidades van a cada ubicación. "
                "Deja en 0 las que no reciben mercancía.",
                size=13, color=TEXTO_GRIS,
            ),
            ft.Container(height=4),
            stocks_col,
            ft.Container(height=4),
            info_costo,
            panel_precio_venta,
            seccion_titulo("Observación"),
            f_obs,
            ft.Container(height=8),
            msg_global,
        ], scroll=ft.ScrollMode.AUTO, spacing=8, width=520),
        content_padding=ft.padding.symmetric(horizontal=20, vertical=16),
        bgcolor=FONDO_CARD,
        actions=[
            ft.TextButton("Cancelar", style=ft.ButtonStyle(color=TEXTO_GRIS),
                          on_click=lambda e: page.close(dlg)),
            ft.Container(
                content=ft.Text("Confirmar Recepción", size=13, color="white",
                                weight=ft.FontWeight.W_600),
                bgcolor="#1565c0", border_radius=8,
                padding=ft.padding.symmetric(horizontal=20, vertical=10),
                on_click=guardar, ink=True,
            ),
        ],
        actions_alignment=ft.MainAxisAlignment.END,
    )
    return dlg


# ─────────────────────────────────────────────────────────────
# VISTA PRINCIPAL
# ─────────────────────────────────────────────────────────────

async def vista_inventario(page: ft.Page, db: DBManager, nombre_rol: str = ROL_ADMIN):

    es_admin    = (nombre_rol == ROL_ADMIN)
    ubicaciones = obtener_ubicaciones(db)
    tipos       = obtener_tipos(db)
    unidades    = obtener_unidades(db)

    estado = {"tipo": None, "texto": None, "alerta": None}

    resumen_row  = ft.Row(spacing=12)
    filtros_row  = ft.Row(spacing=8, wrap=True)
    cuerpo_tabla = ft.Column(spacing=0)

    tabla_scroll   = ft.Row(controls=[cuerpo_tabla], scroll=ft.ScrollMode.AUTO, spacing=0)
    tabla_vertical = ft.Column(controls=[tabla_scroll], scroll=ft.ScrollMode.AUTO,
                               expand=True, spacing=0)

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
        total, criticos, sin_stk = calcular_resumen(prods)

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

    def abrir_editar(id_producto):
        dlg = modal_editar_producto(page, db, id_producto, tipos, unidades, es_admin,
                                    on_guardado=refrescar_todo)
        if dlg:
            page.open(dlg)

    def abrir_desactivar(id_producto, nombre_producto):
        dlg = modal_desactivar(page, db, id_producto, nombre_producto,
                               on_guardado=refrescar_todo)
        page.open(dlg)

    def abrir_agregar(e):
        dlg = modal_agregar_producto(page, db, tipos, ubicaciones, unidades, es_admin,
                                     on_guardado=refrescar_todo)
        page.open(dlg)

    def abrir_entrada(e):
        dlg = modal_entrada(page, db, ubicaciones, on_guardado=refrescar_todo)
        page.open(dlg)

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
            ft.Text("Recepción de Mercancía", size=13, color="white", weight=ft.FontWeight.W_600),
        ], spacing=6),
        bgcolor="#1565c0", border_radius=8,
        padding=ft.padding.symmetric(horizontal=16, vertical=10),
        on_click=abrir_entrada, ink=True,
    )

    reconstruir_filtros()

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

    # Carga inicial
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