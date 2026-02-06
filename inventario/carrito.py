from decimal import Decimal
from django.conf import settings

class Carrito:
    def __init__(self, request):
        self.request = request
        self.session = request.session
        carrito = self.session.get("carrito")
        if not carrito:
            carrito = self.session["carrito"] = {}
        self.carrito = carrito

    def agregar(self, producto, cantidad=1, variacion_id=None):
        # Asegurar que el ID sea string
        product_id = str(producto.id)
        
        # Limpieza de datos (Evita el error 'None')
        if variacion_id == 'None' or variacion_id == '':
            variacion_id = None
        
        # 1. Definir CLAVE ÚNICA
        if variacion_id:
            key = f"{product_id}-{variacion_id}"
        else:
            key = product_id

        # 2. Obtener Datos Visuales (Nombre y Tono)
        nombre_display = producto.nombre
        imagen_display = producto.imagen.url if producto.imagen else ""
        nombre_tono = None

        if variacion_id:
            from .models import Variacion
            try:
                # Buscamos el objeto real en la BD
                var = Variacion.objects.get(id=int(variacion_id))
                nombre_tono = var.nombre  # Ej: "Rojo"
                if var.imagen:
                    imagen_display = var.imagen.url
            except:
                pass

        # 3. CREAR EL ITEM (Aquí estaba el error antes, aseguramos guardar producto_id)
        if key not in self.carrito:
            self.carrito[key] = {
                "producto_id": producto.id,    # <--- ESTO ES LO QUE FALTABA O ESTABA MAL
                "nombre": nombre_display,
                "variacion": nombre_tono,      # Nombre del tono
                "variacion_id": variacion_id,  # ID del tono
                "precio": str(producto.precio),
                "cantidad": 0,
                "imagen": imagen_display,
                "subtotal": "0.00"
            }

        # 4. SUMAR Y CALCULAR
        self.carrito[key]["cantidad"] += int(cantidad)
        
        precio_float = float(self.carrito[key]["precio"])
        cantidad_int = int(self.carrito[key]["cantidad"])
        self.carrito[key]["subtotal"] = f"{precio_float * cantidad_int:.2f}"
        
        self.guardar_carrito()

    def restar(self, producto, variacion_id=None):
        product_id = str(producto.id)
        if variacion_id == 'None' or variacion_id == '':
            variacion_id = None
            
        if variacion_id:
            key = f"{product_id}-{variacion_id}"
        else:
            key = product_id

        if key in self.carrito:
            self.carrito[key]["cantidad"] -= 1
            
            # Si llega a 0, se elimina
            if self.carrito[key]["cantidad"] < 1:
                self.eliminar(producto, variacion_id)
            else:
                # Si no, RECALCULAMOS el subtotal
                precio_float = float(self.carrito[key]["precio"])
                cantidad_int = int(self.carrito[key]["cantidad"])
                self.carrito[key]["subtotal"] = f"{precio_float * cantidad_int:.2f}"
                self.guardar_carrito()

    def eliminar(self, producto, variacion_id=None):
        product_id = str(producto.id)
        if variacion_id == 'None' or variacion_id == '':
            variacion_id = None
            
        if variacion_id:
            key = f"{product_id}-{variacion_id}"
        else:
            key = product_id
        
        if key in self.carrito:
            del self.carrito[key]
            self.guardar_carrito()

    def guardar_carrito(self):
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def save(self):
        self.session["carrito"] = self.carrito
        self.session.modified = True

    def limpiar(self):
        self.session["carrito"] = {}
        self.session.modified = True

    def get_total_price(self):
        return sum(float(item["precio"]) * item["cantidad"] for item in self.carrito.values())

    def __iter__(self):
        for key, item in self.carrito.items():
            item['subtotal'] = float(item['precio']) * int(item['cantidad'])
            yield item

    def __len__(self):
        return sum(item["cantidad"] for item in self.carrito.values())