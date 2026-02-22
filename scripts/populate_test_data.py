"""
populate_test_data.py — Datos de prueba para todas las tablas
==============================================================
Puebla la base de datos con datos realistas del sector agropecuario.
Ejecutar UNA SOLA VEZ después de seed_data.py y create_admin.py.

IMPORTANTE: Este script asume que ya existen:
  - Los roles (Administrador, Operario)
  - Las ubicaciones (Punto de Venta, Bodega)
  - El usuario admin

Uso:
    python scripts/populate_test_data.py
"""

import uuid
import sys
import os
from datetime import datetime, timedelta
import random

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'src')))
from database.db_manager import DBManager

db = DBManager()

# ─────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────

def uid():
    return str(uuid.uuid4())

def fecha(dias_atras=0):
    return (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d %H:%M:%S')

def fecha_solo(dias_atras=0):
    return (datetime.now() - timedelta(days=dias_atras)).strftime('%Y-%m-%d')

def ok(label, result):
    if result['success']:
        print(f"  ✔ {label}")
    else:
        print(f"  ✘ {label} — ERROR")

# ─────────────────────────────────────────────
# 1. OBTENER IDs YA EXISTENTES
# ─────────────────────────────────────────────

def get_existing():
    roles     = db.fetch_query("SELECT idRol, nombreRol FROM rol")
    usuarios  = db.fetch_query("SELECT idUsuario, nombreUsuario FROM usuario")
    ubicaciones = db.fetch_query("SELECT idUbicacion, nombreUbicacion, tipo FROM ubicacion")

    id_admin    = next((r['idRol'] for r in roles if r['nombreRol'] == 'Administrador'), None)
    id_operario = next((r['idRol'] for r in roles if r['nombreRol'] == 'Operario'), None)
    id_usuario_admin = next((u['idUsuario'] for u in usuarios if u['nombreUsuario'] == 'admin'), None)
    id_pv    = next((u['idUbicacion'] for u in ubicaciones if u['tipo'] == 'PUNTO_VENTA'), None)
    id_bodega = next((u['idUbicacion'] for u in ubicaciones if u['tipo'] == 'BODEGA'), None)

    if not all([id_admin, id_operario, id_usuario_admin, id_pv, id_bodega]):
        print("❌ Faltan datos base. Ejecuta primero seed_data.py y create_admin.py")
        sys.exit(1)

    return id_admin, id_operario, id_usuario_admin, id_pv, id_bodega


# ─────────────────────────────────────────────
# 2. USUARIO OPERARIO
# ─────────────────────────────────────────────

def insertar_operario(id_rol_operario):
    print("\n[2] Creando usuario operario...")
    existente = db.fetch_one("SELECT idUsuario FROM usuario WHERE nombreUsuario = 'operario1'")
    if existente:
        print("  ⚠ El operario ya existe, se omite.")
        return existente['idUsuario']

    id_op = uid()
    ok("Operario", db.run_query(
        "INSERT INTO usuario (idUsuario, nombreUsuario, contrasena, idRol, estado) VALUES (%s,%s,%s,%s,%s)",
        (id_op, "operario1", "1234", id_rol_operario, 1)
    ))
    return id_op


# ─────────────────────────────────────────────
# 3. TIPOS DE PRODUCTO
# ─────────────────────────────────────────────

def insertar_tipos():
    print("\n[3] Insertando tipos de producto...")
    tipos = [
        ("Fungicida",    uid()),
        ("Herbicida",    uid()),
        ("Insecticida",  uid()),
        ("Fertilizante", uid()),
        ("Acaricida",    uid()),
    ]
    for nombre, tid in tipos:
        ok(nombre, db.run_query(
            "INSERT IGNORE INTO tipo_producto (idTipoProducto, nombre) VALUES (%s,%s)",
            (tid, nombre)
        ))
    return {nombre: tid for nombre, tid in tipos}


# ─────────────────────────────────────────────
# 4. PRODUCTOS Y PRESENTACIONES
# ─────────────────────────────────────────────

def insertar_productos(tipos):
    print("\n[4] Insertando productos y presentaciones...")

    # Cada producto: (nombre, tipo, unidad_base, precio_lista, stock_minimo)
    productos_def = [
        ("Mancozeb 80%",       "Fungicida",    "Kilogramo", 45000,  10),
        ("Ridomil Gold",       "Fungicida",    "Litro",     120000, 5),
        ("Roundup",            "Herbicida",    "Litro",     38000,  8),
        ("Gramoxone",          "Herbicida",    "Litro",     42000,  6),
        ("Lorsban",            "Insecticida",  "Litro",     55000,  5),
        ("Cipermetrina 25%",   "Insecticida",  "Litro",     32000,  8),
        ("Abamectina 1.8%",    "Acaricida",    "Litro",     98000,  4),
        ("Urea 46%",           "Fertilizante", "Kilogramo", 2800,   50),
        ("DAP 18-46-0",        "Fertilizante", "Kilogramo", 3200,   50),
        ("Folimax Calcio-Boro","Fertilizante", "Litro",     68000,  5),
    ]

    # Presentaciones por unidad base
    presentaciones_por_unidad = {
        "Litro": [
            ("Litro",    1.0000, True),
            ("Galón",    3.7850, False),
            ("Cuarto",   0.9460, False),
            ("Caja x12", 12.000, False),
        ],
        "Kilogramo": [
            ("Kilogramo", 1.0000, True),
            ("Bulto x25", 25.000, False),
            ("Bulto x50", 50.000, False),
        ],
    }

    productos_ids = {}
    pres_ids = {}  # (id_producto, nombre_presentacion) → id_presentacion

    for nombre, tipo_nombre, unidad, precio, stock_min in productos_def:
        id_prod = uid()
        id_tipo = tipos[tipo_nombre]

        ok(nombre, db.run_query(
            """INSERT INTO producto
               (idProducto, nombre, idTipoProducto, unidad_medida_base, precio_lista, stock_minimo, activo, sincronizado)
               VALUES (%s,%s,%s,%s,%s,%s,1,0)""",
            (id_prod, nombre, id_tipo, unidad, precio, stock_min)
        ))
        productos_ids[nombre] = id_prod

        # Insertar presentaciones
        for pres_nombre, factor, es_base in presentaciones_por_unidad[unidad]:
            id_pres = uid()
            precio_sugerido = round(precio * factor, 2)
            db.run_query(
                """INSERT INTO producto_presentacion
                   (idPresentacion, idProducto, nombre_presentacion, factor_conversion, es_unidad_base, precio_sugerido)
                   VALUES (%s,%s,%s,%s,%s,%s)""",
                (id_pres, id_prod, pres_nombre, factor, 1 if es_base else 0, precio_sugerido)
            )
            pres_ids[(id_prod, pres_nombre)] = id_pres

    return productos_ids, pres_ids


# ─────────────────────────────────────────────
# 5. INVENTARIO INICIAL
# ─────────────────────────────────────────────

def insertar_inventario(productos_ids, id_pv, id_bodega):
    print("\n[5] Insertando inventario inicial...")

    # Stock en punto de venta y bodega para cada producto
    stocks = {
        "Mancozeb 80%":        (15, 80),
        "Ridomil Gold":        (8,  40),
        "Roundup":             (12, 60),
        "Gramoxone":           (6,  35),
        "Lorsban":             (10, 45),
        "Cipermetrina 25%":    (14, 70),
        "Abamectina 1.8%":     (5,  20),
        "Urea 46%":            (120, 500),
        "DAP 18-46-0":         (80, 400),
        "Folimax Calcio-Boro": (7,  30),
    }

    for nombre, (stock_pv, stock_bod) in stocks.items():
        id_prod = productos_ids[nombre]

        ok(f"{nombre} — Punto de Venta", db.run_query(
            "INSERT INTO inventario (idInventario, idUbicacion, idProducto, stockActual) VALUES (%s,%s,%s,%s)",
            (uid(), id_pv, id_prod, stock_pv)
        ))
        ok(f"{nombre} — Bodega", db.run_query(
            "INSERT INTO inventario (idInventario, idUbicacion, idProducto, stockActual) VALUES (%s,%s,%s,%s)",
            (uid(), id_bodega, id_prod, stock_bod)
        ))


# ─────────────────────────────────────────────
# 6. CLIENTES
# ─────────────────────────────────────────────

def insertar_clientes():
    print("\n[6] Insertando clientes...")

    clientes = [
        (uid(), "10456789",  "Carlos Andrés Muñoz",     "3145678901", "Vereda El Pomo, Cerrito",      0.00),
        (uid(), "25678901",  "María Elena Vargas",       "3167890123", "Calle 5 #3-20, Cerrito",       4500000.00),
        (uid(), "800123456", "Agropecuaria El Retiro SAS","3189012345","Carrera 10 #8-15, Cerrito",    0.00),
        (uid(), "37890123",  "José Ignacio Herrera",     "3201234567", "Vereda La Tulia, Cerrito",     8500000.00),
        (uid(), "48901234",  "Ana Lucía Ospina",         "3223456789", "Finca La Esperanza, Cerrito",  1200000.00),
        (uid(), "59012345",  "Luis Fernando Castro",     "3245678901", "Vereda Chontaduro, Cerrito",   0.00),
        (uid(), "60123456",  "Rosa Inés Castaño",        "3267890123", "Calle 12 #5-30, Cerrito",      9200000.00),
        (uid(), "71234567",  "Hernando Salcedo",         "3289012345", "Vereda Agua Fría, Cerrito",    0.00),
    ]

    ids = {}
    for id_cli, doc, nombre, cel, dir_, saldo in clientes:
        ok(nombre, db.run_query(
            """INSERT INTO cliente (idCliente, documento, nombre, celular, direccion, saldo_pendiente, sincronizado)
               VALUES (%s,%s,%s,%s,%s,%s,0)""",
            (id_cli, doc, nombre, cel, dir_, saldo)
        ))
        ids[nombre] = id_cli

    return ids, clientes


# ─────────────────────────────────────────────
# 7. CONSECUTIVO DE FACTURA
# ─────────────────────────────────────────────

def init_consecutivo():
    print("\n[7] Inicializando consecutivo de factura...")
    existente = db.fetch_one("SELECT ultimo_valor FROM consecutivo_factura WHERE id = 1")
    if existente:
        print("  ⚠ Consecutivo ya existe, se omite.")
    else:
        ok("Consecutivo", db.run_query(
            "INSERT INTO consecutivo_factura (id, ultimo_valor) VALUES (1, 0)"
        ))


# ─────────────────────────────────────────────
# 8. MOVIMIENTOS Y FACTURAS DE PRUEBA
# ─────────────────────────────────────────────

def insertar_movimientos_y_facturas(productos_ids, pres_ids, clientes_ids, id_usuario_admin, id_pv, id_bodega):
    print("\n[8] Insertando movimientos y facturas de prueba...")

    # ── 8a. Entradas de mercancía (ENTRADA) ──
    print("  → Entradas de mercancía...")
    id_mov_entrada = uid()
    db.run_query(
        """INSERT INTO movimiento (idMovimiento, tipo, fecha, idUbicacionOrigen, idUbicacionDestino, idUsuario, observacion, sincronizado)
           VALUES (%s,'ENTRADA',%s,NULL,%s,%s,'Entrada inicial de mercancía al sistema',0)""",
        (id_mov_entrada, fecha(30), id_bodega, id_usuario_admin)
    )
    for nombre in ["Mancozeb 80%", "Ridomil Gold", "Roundup"]:
        id_prod = productos_ids[nombre]
        id_pres = pres_ids[(id_prod, "Litro" if nombre != "Mancozeb 80%" else "Kilogramo")]
        db.run_query(
            """INSERT INTO movimiento_detalle
               (idDetalle, idMovimiento, idProducto, idPresentacion, cantidad, cantidad_base, precio_unitario_aplicado)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (uid(), id_mov_entrada, id_prod, id_pres, 50, 50, 0)
        )
    print("    ✔ Entrada registrada")

    # ── 8b. Traslado bodega → punto de venta ──
    print("  → Traslado bodega a punto de venta...")
    id_mov_traslado = uid()
    db.run_query(
        """INSERT INTO movimiento (idMovimiento, tipo, fecha, idUbicacionOrigen, idUbicacionDestino, idUsuario, observacion, sincronizado)
           VALUES (%s,'TRASLADO',%s,%s,%s,%s,'Reabastecimiento punto de venta',0)""",
        (id_mov_traslado, fecha(15), id_bodega, id_pv, id_usuario_admin)
    )
    for nombre in ["Lorsban", "Cipermetrina 25%"]:
        id_prod = productos_ids[nombre]
        id_pres = pres_ids[(id_prod, "Litro")]
        db.run_query(
            """INSERT INTO movimiento_detalle
               (idDetalle, idMovimiento, idProducto, idPresentacion, cantidad, cantidad_base, precio_unitario_aplicado)
               VALUES (%s,%s,%s,%s,%s,%s,%s)""",
            (uid(), id_mov_traslado, id_prod, id_pres, 10, 10, 0)
        )
    print("    ✔ Traslado registrado")

    # ── 8c. Ventas con facturas ──
    print("  → Ventas y facturas...")

    ventas = [
        # (cliente, dias_atras, es_fianza, productos[(nombre, pres, cantidad, precio)])
        ("Carlos Andrés Muñoz",  20, False, [
            ("Roundup",          "Litro",     5,  38000),
            ("Lorsban",          "Litro",     2,  55000),
        ]),
        ("María Elena Vargas",   18, True, [
            ("Ridomil Gold",     "Litro",     3,  120000),
            ("Mancozeb 80%",     "Kilogramo", 5,  45000),
        ]),
        ("José Ignacio Herrera", 15, True, [
            ("Urea 46%",         "Kilogramo", 100, 2800),
            ("DAP 18-46-0",      "Kilogramo", 50,  3200),
        ]),
        ("Ana Lucía Ospina",     10, False, [
            ("Cipermetrina 25%", "Litro",     4,  32000),
            ("Abamectina 1.8%",  "Litro",     2,  98000),
        ]),
        ("Luis Fernando Castro",  5, False, [
            ("Gramoxone",        "Litro",     3,  42000),
            ("Folimax Calcio-Boro","Litro",   2,  68000),
        ]),
        ("Rosa Inés Castaño",     3, True, [
            ("Ridomil Gold",     "Litro",     5,  120000),
            ("Lorsban",          "Litro",     3,  55000),
            ("Mancozeb 80%",     "Kilogramo", 10, 45000),
        ]),
    ]

    consecutivo = 0
    for cliente_nombre, dias, es_fianza, items in ventas:
        consecutivo += 1
        id_cli = clientes_ids[cliente_nombre]
        id_mov = uid()
        id_fac = uid()

        # Calcular totales
        subtotal = sum(cant * precio for _, _, cant, precio in items)
        descuento = 0
        total_neto = subtotal - descuento

        # Movimiento
        db.run_query(
            """INSERT INTO movimiento
               (idMovimiento, tipo, fecha, idUbicacionOrigen, idUbicacionDestino, idUsuario, idCliente, observacion, sincronizado)
               VALUES (%s,'VENTA',%s,%s,NULL,%s,%s,'Venta de prueba',0)""",
            (id_mov, fecha(dias), id_pv, id_usuario_admin, id_cli)
        )

        # Detalle del movimiento
        for prod_nombre, pres_nombre, cantidad, precio in items:
            id_prod = productos_ids[prod_nombre]
            id_pres = pres_ids[(id_prod, pres_nombre)]
            db.run_query(
                """INSERT INTO movimiento_detalle
                   (idDetalle, idMovimiento, idProducto, idPresentacion, cantidad, cantidad_base, precio_unitario_aplicado)
                   VALUES (%s,%s,%s,%s,%s,%s,%s)""",
                (uid(), id_mov, id_prod, id_pres, cantidad, cantidad, precio)
            )

        # Factura
        estado_pago = 'PENDIENTE' if es_fianza else 'PAGADA'
        fecha_venc = fecha_solo(-180) if es_fianza else None  # 6 meses adelante
        db.run_query(
            """INSERT INTO factura
               (idFactura, idMovimiento, idCliente, consecutivo, subtotal, descuento_ajuste,
                total_neto, es_fianza, fecha_vencimiento_fianza, estado_pago, sincronizado)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,0)""",
            (id_fac, id_mov, id_cli, consecutivo, subtotal, descuento,
             total_neto, 1 if es_fianza else 0, fecha_venc, estado_pago)
        )
        print(f"    ✔ Factura #{consecutivo:03d} — {cliente_nombre} — ${total_neto:,.0f} — {'Fianza' if es_fianza else 'Contado'}")

    # Actualizar consecutivo
    db.run_query("UPDATE consecutivo_factura SET ultimo_valor = %s WHERE id = 1", (consecutivo,))


# ─────────────────────────────────────────────
# 9. PAGOS DE FIANZA
# ─────────────────────────────────────────────

def insertar_pagos_fianza(clientes_ids, id_usuario_admin):
    print("\n[9] Insertando abonos a fianzas...")

    # María Elena Vargas abona algo
    id_cli = clientes_ids["María Elena Vargas"]
    facturas = db.fetch_query(
        "SELECT idFactura, total_neto FROM factura WHERE idCliente = %s AND estado_pago = 'PENDIENTE'",
        (id_cli,)
    )
    if facturas:
        id_pago = uid()
        monto_abono = 200000
        db.run_query(
            """INSERT INTO pago_fianza (idPago, idCliente, idUsuario, monto, fecha, observacion, sincronizado)
               VALUES (%s,%s,%s,%s,%s,'Abono parcial en efectivo',0)""",
            (id_pago, id_cli, id_usuario_admin, monto_abono, fecha(10))
        )
        db.run_query(
            """INSERT INTO pago_fianza_detalle (idDetallePago, idPago, idFactura, monto_aplicado)
               VALUES (%s,%s,%s,%s)""",
            (uid(), id_pago, facturas[0]['idFactura'], monto_abono)
        )
        db.run_query(
            "UPDATE cliente SET saldo_pendiente = saldo_pendiente - %s WHERE idCliente = %s",
            (monto_abono, id_cli)
        )
        print(f"  ✔ Abono de ${monto_abono:,} registrado para María Elena Vargas")


# ─────────────────────────────────────────────
# 10. AJUSTE DE BAJA (producto dañado)
# ─────────────────────────────────────────────

def insertar_baja(productos_ids, pres_ids, id_usuario_admin, id_bodega):
    print("\n[10] Insertando ajuste de baja...")
    id_prod = productos_ids["Gramoxone"]
    id_pres = pres_ids[(id_prod, "Litro")]
    id_mov  = uid()

    db.run_query(
        """INSERT INTO movimiento
           (idMovimiento, tipo, fecha, idUbicacionOrigen, idUbicacionDestino, idUsuario, observacion, sincronizado)
           VALUES (%s,'AJUSTE_BAJA',%s,%s,NULL,%s,'2 litros dañados por filtración en bodega',0)""",
        (id_mov, fecha(7), id_bodega, id_usuario_admin)
    )
    db.run_query(
        """INSERT INTO movimiento_detalle
           (idDetalle, idMovimiento, idProducto, idPresentacion, cantidad, cantidad_base, precio_unitario_aplicado)
           VALUES (%s,%s,%s,%s,%s,%s,%s)""",
        (uid(), id_mov, id_prod, id_pres, 2, 2, 42000)
    )
    print("  ✔ Baja de 2 litros de Gramoxone registrada")


# ─────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 55)
    print("  POBLANDO BASE DE DATOS — Almacén La Playa")
    print("=" * 55)

    id_admin, id_operario, id_usuario_admin, id_pv, id_bodega = get_existing()

    id_operario_usuario = insertar_operario(id_operario)
    tipos               = insertar_tipos()
    productos_ids, pres_ids = insertar_productos(tipos)
    insertar_inventario(productos_ids, id_pv, id_bodega)
    init_consecutivo()

    clientes_ids, clientes_raw = insertar_clientes()
    # Diccionario nombre → id para las ventas
    clientes_map = {nombre: id_cli for id_cli, _, nombre, *_ in clientes_raw}

    insertar_movimientos_y_facturas(productos_ids, pres_ids, clientes_map, id_usuario_admin, id_pv, id_bodega)
    insertar_pagos_fianza(clientes_map, id_usuario_admin)
    insertar_baja(productos_ids, pres_ids, id_usuario_admin, id_bodega)

    print("\n" + "=" * 55)
    print("  ✔ Base de datos lista para desarrollo.")
    print("  Usuarios disponibles:")
    print("    admin     / 1234  (Administrador)")
    print("    operario1 / 1234  (Operario)")
    print("=" * 55)