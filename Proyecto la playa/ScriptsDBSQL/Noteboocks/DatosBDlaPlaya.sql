USE LaPlayaO;

-- 1. UBICACION
INSERT INTO UBICACION (nombre, descripcion) VALUES
('Bodega Principal', 'Ubicación central para almacenamiento'),
('Estantería 1', 'Estante superior izquierdo'),
('Estantería 2', 'Estante inferior derecho');

-- 2. TIPO_PRODUCTO
INSERT INTO TIPO_PRODUCTO (categoria, descripcion) VALUES
('Herbicida', 'Control de malezas'),
('Fungicida', 'Control de hongos'),
('Insecticida', 'Control de insectos'),
('Nematicida', 'Control de nematodos');

-- 3. PRODUCTO
INSERT INTO PRODUCTO (nombre, descripcion, cantidad, tipo_producto, precio, fecha_vencimiento) VALUES
('Glifosol', 'Líquido para control de malas hierbas.', 50, 1, 75000.00, '2024-12-31'),
('Manzate', 'Fungicida sistémico.', 40, 2, 89000.00, '2025-06-30'),
('Pholition', 'Control de plagas foliares.', 80, 3, 105000.00, '2024-09-30'),
('Curaxil', 'Herbicida preemergente.', 70, 1, 80000.00, '2025-03-31'),
('Nematron', 'Nematicida de acción rápida.', 100, 4, 65000.00, '2024-11-30');

-- 4. PRODUCTO_UBICACION
INSERT INTO PRODUCTO_UBICACION (id_producto, id_ubicacion) VALUES
(1, 1),
(2, 1),
(3, 2),
(4, 1),
(5, 2);

-- 5. CLIENTE
INSERT INTO CLIENTE (nombre, apellido, apodo, celular) VALUES
('Carlos', 'Pérez', 'Carlitos', '3001112233'),
('Ana', 'Rodríguez', NULL, '3123344556'),
('Luis', 'Martínez', 'El Profe', '3109988776'),
('Sara', 'Gómez', 'Sarita', '3017766554'),
('Mario', 'López', NULL, '3054433221');

-- 6. FIANZA
INSERT INTO FIANZA (cliente_id, fecha, valor) VALUES
(1, '2024-03-02', 30000),
(3, '2024-04-21', 50000),
(4, '2024-06-12', 45000);

-- 7. VENTA
INSERT INTO VENTA (venta_total, fecha, descuento, fianza_id) VALUES
(125000.00, '2024-03-02', 2000.00, 1),
(178000.00, '2024-04-21', 0.00, NULL),
(210000.00, '2024-06-12', 5000.00, 2),
(90000.00, '2024-08-16', 0.00, NULL),
(130000.00, '2024-03-15', 3000.00, 3);

-- 8. VENTA_PRODUCTO
INSERT INTO VENTA_PRODUCTO (id_producto, id_venta, cantidad, precio_unitario) VALUES
(1, 1, 1, 75000.00),
(2, 1, 1, 89000.00),
(3, 2, 2, 105000.00),
(5, 3, 3, 65000.00),
(4, 4, 1, 80000.00);

-- 9. HISTORIAL_VENTA
INSERT INTO HISTORIAL_VENTA (fecha, cantidad, precio_unitario, subtotal, venta_id, producto_id) VALUES
('2024-03-02', 1, 75000.00, 75000.00, 1, 1),
('2024-03-02', 1, 89000.00, 89000.00, 1, 2),
('2024-04-21', 2, 105000.00, 210000.00, 2, 3),
('2024-06-12', 3, 65000.00, 195000.00, 3, 5),
('2024-08-16', 1, 80000.00, 80000.00, 4, 4);

-- 10. PAGO
INSERT INTO PAGO (id_venta, monto, metodo_pago, fecha_pago) VALUES
(1, 125000.00, 'efectivo', '2024-03-02'),
(2, 178000.00, 'transferencia', '2024-04-21'),
(3, 210000.00, 'tarjeta', '2024-06-12'),
(4, 90000.00, 'efectivo', '2024-08-16'),
(5, 130000.00, 'efectivo', '2024-03-15');

-- 11. FACTURA
INSERT INTO FACTURA (numero_factura, fecha_emision, id_venta, nombre_cliente_factura, nit_cliente, total_facturado) VALUES
('FAC-0001', '2024-03-02', 1, 'Carlos Pérez', '123456789', 125000.00),
('FAC-0002', '2024-04-21', 2, 'Ana Rodríguez', '987654321', 178000.00),
('FAC-0003', '2024-06-12', 3, 'Luis Martínez', '456123789', 210000.00),
('FAC-0004', '2024-08-16', 4, 'Sara Gómez', '789456123', 90000.00),
('FAC-0005', '2024-03-15', 5, 'Mario López', '321654987', 130000.00);

-- 12. PEDIDO
INSERT INTO PEDIDO (id_cliente, fecha_pedido, estado, direccion_entrega) VALUES
(1, '2024-04-01', 'pendiente', 'Calle 123 #45-67'),
(3, '2024-04-10', 'entregado', 'Carrera 45 #12-34');

-- 13. PEDIDO_PRODUCTO
INSERT INTO PEDIDO_PRODUCTO (id_pedido, id_producto, cantidad) VALUES
(1, 1, 2),
(1, 2, 1),
(2, 5, 3);

-- 14. CAJA_DIARIA
INSERT INTO CAJA_DIARIA (fecha, apertura, cierre, diferencia, observacion) VALUES
('2024-03-02', 500000.00, 625000.00, 0.00, 'Día sin novedades'),
('2024-04-21', 400000.00, 578000.00, 0.00, 'Pagos por transferencia'),
('2024-06-12', 300000.00, 510000.00, 0.00, 'Pago mixto recibido');

-- 15. ROL
INSERT INTO ROL (nombre, descripcion) VALUES
('Administrador', 'Acceso completo al sistema'),
('Comprador', 'Cliente registrado que realiza compras');


INSERT INTO USUARIO (nombre, correo, contrasena, id_rol, id_cliente) VALUES
('admin', 'admin@laplaya.com', 'admin123', 1, NULL), -- Admin sin vínculo a cliente
('carlitos', 'carlos@laplaya.com', 'cliente123', 2, 1), -- Carlos Pérez
('luis', 'luis@laplaya.com', 'cliente123', 2, 3); -- Luis Martínez


INSERT INTO MODULO (nombre, descripcion) VALUES
('Usuarios', 'Gestión de usuarios del sistema'),
('Productos', 'Visualización y gestión de productos'),
('Ventas', 'Manejo de ventas y fianzas'),
('Reportes', 'Visualización de estadísticas'),
('Pedidos', 'Gestión de pedidos de clientes'),
('Perfil', 'Módulo para gestión del perfil del comprador');


INSERT INTO OPERACION (nombre, id_modulo) VALUES
('Crear Usuario', 1),
('Ver Usuarios', 1),
('Ver Productos', 2),
('Editar Producto', 2),
('Crear Venta', 3),
('Ver Ventas', 3),
('Ver Reportes', 4),
('Crear Pedido', 5),
('Ver Mis Pedidos', 5),
('Editar Perfil', 6);


-- Permisos del ADMINISTRADOR (ID Rol = 1)
INSERT INTO ROL_OPERACION (id_rol, id_operacion) VALUES
(1, 1), (1, 2),       -- Usuarios
(1, 3), (1, 4),       -- Productos
(1, 5), (1, 6),       -- Ventas
(1, 7),               -- Reportes
(1, 8), (1, 9),       -- Pedidos
(1, 10);              -- Perfil

-- Permisos del COMPRADOR (ID Rol = 2)
INSERT INTO ROL_OPERACION (id_rol, id_operacion) VALUES
(2, 3),   -- Ver Productos
(2, 8),   -- Crear Pedido
(2, 9),   -- Ver Mis Pedidos
(2, 10);  -- Editar Perfil








