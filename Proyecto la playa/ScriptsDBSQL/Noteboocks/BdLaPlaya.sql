CREATE DATABASE LaPlayaO;
USE LaPlayaO;

-- Tabla de ubicaciones
CREATE TABLE UBICACION (
  id_ubicacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(250) NOT NULL,
  descripcion VARCHAR(250)
);

-- Tabla de tipos de productos
CREATE TABLE TIPO_PRODUCTO (
  id_tipo_producto INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  categoria VARCHAR(100) NOT NULL,
  descripcion VARCHAR(250)
);

-- Tabla de productos
CREATE TABLE PRODUCTO (
  id_producto INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  descripcion VARCHAR(250),
  cantidad INT NOT NULL,
  id_tipo_producto INT NOT NULL,
  precio DECIMAL(10,2) NOT NULL,
  fecha_vencimiento DATE NOT NULL,
  CONSTRAINT fk_producto_tipo_producto FOREIGN KEY (id_tipo_producto) REFERENCES TIPO_PRODUCTO(id_tipo_producto)
);

-- Relación producto - ubicación
CREATE TABLE PRODUCTO_UBICACION (
  id_producto INT NOT NULL,
  id_ubicacion INT NOT NULL,
  PRIMARY KEY (id_producto, id_ubicacion),
  CONSTRAINT fk_producto_ubicacion_producto FOREIGN KEY (id_producto) REFERENCES PRODUCTO(id_producto),
  CONSTRAINT fk_producto_ubicacion_ubicacion FOREIGN KEY (id_ubicacion) REFERENCES UBICACION(id_ubicacion)
);

-- Tabla de clientes
CREATE TABLE CLIENTE (
  id_cliente INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(250) NOT NULL,
  apellido VARCHAR(250),
  apodo VARCHAR(250),
  celular VARCHAR(45)
);

-- Tabla de fianzas
CREATE TABLE FIANZA (
  id_fianza INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  fecha DATE NOT NULL,
  valor INT NOT NULL,
  CONSTRAINT fk_fianza_cliente FOREIGN KEY (id_cliente) REFERENCES CLIENTE(id_cliente)
);

-- Tabla de ventas
CREATE TABLE VENTA (
  id_venta INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  total_venta DECIMAL(10,2) NOT NULL,
  fecha DATE NOT NULL,
  descuento DECIMAL(10,2) DEFAULT 0,
  id_fianza INT,
  CONSTRAINT fk_venta_fianza FOREIGN KEY (id_fianza) REFERENCES FIANZA(id_fianza)
);

-- Relación venta - producto
CREATE TABLE VENTA_PRODUCTO (
  id_producto INT NOT NULL,
  id_venta INT NOT NULL,
  cantidad INT NOT NULL,
  precio_unitario DECIMAL(10,2) NOT NULL,
  PRIMARY KEY (id_producto, id_venta),
  CONSTRAINT fk_vp_producto FOREIGN KEY (id_producto) REFERENCES PRODUCTO(id_producto),
  CONSTRAINT fk_vp_venta FOREIGN KEY (id_venta) REFERENCES VENTA(id_venta)
);

-- Historial de ventas
CREATE TABLE HISTORIAL_VENTA (
  id_historial INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  fecha DATE NOT NULL,
  cantidad INT NOT NULL,
  precio_unitario DECIMAL(10,2) NOT NULL,
  subtotal DECIMAL(10,2) NOT NULL,
  id_venta INT NOT NULL,
  id_producto INT NOT NULL,
  CONSTRAINT fk_hist_venta FOREIGN KEY (id_venta) REFERENCES VENTA(id_venta),
  CONSTRAINT fk_hist_producto FOREIGN KEY (id_producto) REFERENCES PRODUCTO(id_producto)
);

-- Tabla de roles
CREATE TABLE ROL (
  id_rol INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(45) NOT NULL,
  descripcion VARCHAR(45)
);

-- Tabla de usuarios
CREATE TABLE USUARIO (
  id_usuario INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  correo VARCHAR(75) NOT NULL,
  contrasena VARCHAR(100) NOT NULL,
  id_rol INT NOT NULL,
  id_cliente INT,
  CONSTRAINT fk_usuario_rol FOREIGN KEY (id_rol) REFERENCES ROL(id_rol),
  CONSTRAINT fk_usuario_cliente FOREIGN KEY (id_cliente) REFERENCES CLIENTE(id_cliente)
);

-- Tabla de módulos
CREATE TABLE MODULO (
  id_modulo INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  descripcion VARCHAR(100)
);

-- Tabla de operaciones
CREATE TABLE OPERACION (
  id_operacion INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  nombre VARCHAR(100) NOT NULL,
  id_modulo INT NOT NULL,
  CONSTRAINT fk_operacion_modulo FOREIGN KEY (id_modulo) REFERENCES MODULO(id_modulo)
);

-- Relación rol - operación
CREATE TABLE ROL_OPERACION (
  id INT NOT NULL AUTO_INCREMENT PRIMARY KEY,
  id_rol INT NOT NULL,
  id_operacion INT NOT NULL,
  CONSTRAINT fk_rol_operacion_rol FOREIGN KEY (id_rol) REFERENCES ROL(id_rol),
  CONSTRAINT fk_rol_operacion_operacion FOREIGN KEY (id_operacion) REFERENCES OPERACION(id_operacion)
);

-- Tabla de pedidos
CREATE TABLE PEDIDO (
  id_pedido INT AUTO_INCREMENT PRIMARY KEY,
  id_cliente INT NOT NULL,
  fecha_pedido DATE NOT NULL,
  estado VARCHAR(50) NOT NULL,
  direccion_entrega VARCHAR(250),
  FOREIGN KEY (id_cliente) REFERENCES CLIENTE(id_cliente)
);

-- Relación pedido - producto
CREATE TABLE PEDIDO_PRODUCTO (
  id_pedido INT NOT NULL,
  id_producto INT NOT NULL,
  cantidad INT NOT NULL,
  PRIMARY KEY (id_pedido, id_producto),
  FOREIGN KEY (id_pedido) REFERENCES PEDIDO(id_pedido),
  FOREIGN KEY (id_producto) REFERENCES PRODUCTO(id_producto)
);

-- Tabla de pagos
CREATE TABLE PAGO (
  id_pago INT AUTO_INCREMENT PRIMARY KEY,
  id_venta INT NOT NULL,
  monto DECIMAL(10,2) NOT NULL,
  metodo_pago VARCHAR(100) NOT NULL,
  fecha_pago DATE NOT NULL,
  FOREIGN KEY (id_venta) REFERENCES VENTA(id_venta)
);

-- Tabla de facturas
CREATE TABLE FACTURA (
  id_factura INT AUTO_INCREMENT PRIMARY KEY,
  numero_factura VARCHAR(50) UNIQUE NOT NULL,
  fecha_emision DATE NOT NULL,
  id_venta INT NOT NULL,
  nombre_cliente_factura VARCHAR(250),
  nit_cliente VARCHAR(50),
  total_venta DECIMAL(10,2) NOT NULL,
  CONSTRAINT fk_factura_venta FOREIGN KEY (id_venta) REFERENCES VENTA(id_venta)
);
