from decimal import Decimal  
from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.utils.html import mark_safe
from django.db.models.signals import post_save, post_delete
from django.dispatch import receiver
from django.db.models import Sum

# 1. CONFIGURACIÓN
class Configuracion(models.Model):
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0.00, verbose_name="Costo de Envío ($)")
    def __str__(self):
        return "Configuración General del Sistema"

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuración" # Para que no diga "Configuraciones" en plural si es solo una

# 2. CATEGORÍAS
class Marca(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    imagen = models.ImageField(upload_to='marcas/', blank=True, null=True)
    def __str__(self): return self.nombre

class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)
    def __str__(self): return self.nombre

class SubCategoria(models.Model):
    # ¡ESTO ARREGLA EL ERROR DE QUE NO CARGABA LA PÁGINA!
    categoria = models.ForeignKey(Categoria, on_delete=models.CASCADE, related_name='subcategorias')
    nombre = models.CharField(max_length=100)
    def __str__(self): return f"{self.categoria} > {self.nombre}"

class TipoProducto(models.Model):
    # ¡ESTO TAMBIÉN ERA NECESARIO!
    subcategoria = models.ForeignKey(SubCategoria, on_delete=models.CASCADE, related_name='tipos')
    nombre = models.CharField(max_length=100)
    def __str__(self): return f"{self.subcategoria} > {self.nombre}"

# 3. PRODUCTOS
class Producto(models.Model):
    nombre = models.CharField(max_length=200)
    marca = models.ForeignKey(Marca, on_delete=models.SET_NULL, null=True, blank=True)
    tipo = models.ForeignKey(TipoProducto, on_delete=models.SET_NULL, null=True, blank=True)
    precio = models.DecimalField(max_digits=10, decimal_places=2)
    stock = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=5)
    imagen = models.ImageField(upload_to='productos/', blank=True, null=True)
    descripcion = models.TextField(blank=True, null=True)
    activo = models.BooleanField(default=True)
    def ver_imagen(self):
        if self.imagen: return mark_safe(f'<img src="{self.imagen.url}" width="50" style="border-radius:5px;"/>')
        return "-"
    def __str__(self): return self.nombre

class Variacion(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    stock = models.IntegerField(default=0)
    imagen = models.ImageField(upload_to='variacione/', null=True, blank=True)
    def __str__(self): return f"{self.producto} - {self.nombre}"

class MovimientoStock(models.Model):
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    tipo = models.CharField(max_length=10, choices=[('entrada', 'Entrada'), ('salida', 'Salida')])
    fecha = models.DateTimeField(auto_now_add=True)
    def save(self, *args, **kwargs):
        if self.pk is None:
            if self.tipo == 'entrada': self.producto.stock += self.cantidad
            else: self.producto.stock -= self.cantidad
            self.producto.save()
        super().save(*args, **kwargs)

# 4. PEDIDOS
class Pedido(models.Model):
    ESTADOS = (('PENDIENTE', 'Pendiente'), ('EN_CAMINO', 'En Camino'), ('ENTREGADO', 'Entregado'), ('CANCELADO', 'Cancelado'))
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    estado = models.CharField(max_length=20, choices=ESTADOS, default='PENDIENTE')
    
    nombre_destinatario = models.CharField(max_length=200, blank=True, null=True)
    cedula = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    provincia = models.CharField(max_length=100, blank=True, null=True)
    canton = models.CharField(max_length=100, blank=True, null=True)
    direccion = models.TextField(blank=True, null=True)
    referencia = models.TextField(blank=True, null=True)
    map_link = models.TextField(blank=True, null=True)

    metodo_pago = models.CharField(max_length=50, default="Transferencia")
    costo_envio = models.DecimalField(max_digits=10, decimal_places=2, default=0.25)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def __str__(self): return f"Pedido #{self.id}"

class LineaPedido(models.Model):
    pedido = models.ForeignKey(Pedido, related_name='lineas', on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    variacion = models.CharField(max_length=100, blank=True, null=True)
    cantidad = models.IntegerField(default=1)
    precio_unitario = models.DecimalField(max_digits=10, decimal_places=2)

    @property
    def subtotal(self): return self.cantidad * self.precio_unitario
    def __str__(self): return f"{self.cantidad}x {self.producto.nombre}"

# === SEÑALES: CÁLCULO AUTOMÁTICO ===
@receiver(post_delete, sender=LineaPedido)
def actualizar_total_pedido(sender, instance, **kwargs):
    pedido = instance.pedido
    total_productos = sum(linea.subtotal for linea in pedido.lineas.all())
    pedido.total = total_productos + pedido.costo_envio
    Pedido.objects.filter(id=pedido.id).update(total=pedido.total)

# --- CÓDIGO NUEVO: AUTOMATIZACIÓN DE STOCK ---

@receiver(post_save, sender=Variacion)
@receiver(post_delete, sender=Variacion)
def actualizar_stock_producto_padre(sender, instance, **kwargs):
    """
    Cada vez que se crea, edita o borra una variación, 
    se recalcula el stock del producto padre.
    """
    producto = instance.producto

    # Sumamos el stock de todas las variaciones de este producto
    total_variaciones = producto.variacion_set.aggregate(total=Sum('stock'))['total']

    # Si hay variaciones, el stock del padre es la suma
    if total_variaciones is not None:
        producto.stock = total_variaciones
    else:
        # Si borraron todas las variaciones, dejamos el stock como estaba o en 0
        # (Aquí depende de tu lógica, pero por seguridad actualizamos solo si hay hijos)
        pass 

    producto.save()

# 5. OTROS
class Favorito(models.Model):
    usuario = models.ForeignKey(User, on_delete=models.CASCADE)
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    fecha = models.DateTimeField(auto_now_add=True)
    class Meta: unique_together = ('usuario', 'producto')

class Gasto(models.Model):
    descripcion = models.CharField(max_length=200)
    monto = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField(auto_now_add=True)