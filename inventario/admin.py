from django.contrib import admin
from django.utils.html import format_html
from django.contrib.admin import SimpleListFilter
from django.db.models import F
from .models import (
    Categoria, SubCategoria, TipoProducto, Producto, 
    MovimientoStock, Variacion, Marca, Pedido, LineaPedido, 
    Gasto, Configuracion, Favorito
)
from django.shortcuts import redirect
from django.urls import reverse
from .models import Configuracion 

# --- FILTROS ---
class EstadoPedidoFilter(SimpleListFilter):
    title = 'Estado'
    parameter_name = 'estado'
    def lookups(self, request, model_admin): return (('activos', 'Activos'), ('entregados', 'Historial'))
    def queryset(self, request, queryset):
        if self.value() == 'activos': return queryset.exclude(estado='ENTREGADO')
        if self.value() == 'entregados': return queryset.filter(estado='ENTREGADO')
        return queryset

class BajoStockFilter(SimpleListFilter):
    title = 'Stock'
    parameter_name = 'stock'
    def lookups(self, request, model_admin): return (('bajo', 'Bajo'), ('ok', 'Bien'))
    def queryset(self, request, queryset):
        if self.value() == 'bajo': return queryset.filter(stock__lte=F('stock_minimo'))
        return queryset

# --- 1. CONFIGURACIÓN DE PEDIDOS (LIMPIA) ---
class LineaPedidoInline(admin.TabularInline):
    model = LineaPedido
    extra = 0
    autocomplete_fields = ['producto'] 
    fields = ('producto', 'cantidad', 'precio_unitario', 'subtotal_visual')
    readonly_fields = ('subtotal_visual',)

    def subtotal_visual(self, obj):
        return f"${obj.subtotal}" if obj.id else "-"
    subtotal_visual.short_description = "Subtotal"

@admin.register(Pedido)
class PedidoAdmin(admin.ModelAdmin):
    inlines = [LineaPedidoInline]
    
    # LISTA SIMPLE Y LIMPIA (Sin editar afuera)
    list_display = ('id', 'usuario', 'fecha_bonita', 'total_display', 'estado_badge') 
    
    list_display_links = ('id', 'usuario') 
    list_filter = (EstadoPedidoFilter, 'fecha', 'estado')
    search_fields = ('usuario__username', 'id')
    actions = ['marcar_entregado']

    # Aquí es donde se edita el estado (ADENTRO)
    fieldsets = (
        ('Información del Cliente', {
            'fields': ('usuario', 'nombre_destinatario', 'cedula', 'telefono')
        }),
        ('Detalles de Entrega', {
            'fields': ('provincia', 'canton', 'direccion', 'referencia')
        }),
        ('Gestión del Pedido', {
            'fields': ('estado', 'costo_envio', 'total_display') 
        }),
    )
    
    readonly_fields = ('total_display', 'fecha')

    def total_display(self, obj): return f"${obj.total}"
    total_display.short_description = "Total"
    
    def fecha_bonita(self, obj): return obj.fecha.strftime("%d/%m %H:%M")
    fecha_bonita.short_description = "Fecha"

    # Etiqueta de color simple para la lista
    def estado_badge(self, obj):
        colores = {
            'PENDIENTE': '#d97706', # Naranja
            'EN_CAMINO': '#2563eb', # Azul
            'ENTREGADO': '#059669', # Verde
            'CANCELADO': '#dc2626'  # Rojo
        }
        color = colores.get(obj.estado, 'black')
        return format_html('<b style="color:{};">{}</b>', color, obj.get_estado_display())
    estado_badge.short_description = "Estado"

    def get_form(self, request, obj=None, **kwargs):
        form = super().get_form(request, obj, **kwargs)
        if obj is None:
            config = Configuracion.objects.first()
            if config:
                form.base_fields['costo_envio'].initial = config.costo_envio
        return form

    def save_related(self, request, form, formsets, change):
        super().save_related(request, form, formsets, change)
        pedido = form.instance
        total_productos = sum(linea.cantidad * linea.precio_unitario for linea in pedido.lineas.all())
        pedido.total = total_productos + pedido.costo_envio
        pedido.save()

    def marcar_entregado(self, request, queryset): queryset.update(estado='ENTREGADO')

    class Media:
        css = { 'all': ('css/admin_sections/orders.css',) }


# --- 2. CONFIGURACIÓN DE PRODUCTOS (INTACTA) ---
class VariacionInline(admin.TabularInline):
    model = Variacion
    extra = 0

@admin.register(Producto)
class ProductoAdmin(admin.ModelAdmin):
    list_display = ('imagen_thumbnail', 'nombre', 'precio', 'mostrar_stock', 'activo')
    list_display_links = ('imagen_thumbnail', 'nombre') 
    search_fields = ('nombre',)
    list_filter = ('marca', 'activo', BajoStockFilter)
    inlines = [VariacionInline]

    def imagen_thumbnail(self, obj):
        if hasattr(obj, 'imagen') and obj.imagen:
            return format_html('<img src="{}" style="width: 45px; height: 45px; object-fit: cover; border-radius: 8px; border: 1px solid #ddd;" class="img-zoom" />', obj.imagen.url)
        return "-"
    imagen_thumbnail.short_description = "FOTO"

    def mostrar_stock(self, obj):
        color = "red" if obj.stock <= 0 else "orange" if obj.stock <= obj.stock_minimo else "green"
        return format_html('<b style="color:{};">{}</b>', color, obj.stock)
    mostrar_stock.short_description = "Stock Global"

    class Media:
        css = { 'all': ('css/admin_sections/products.css',) }

# El decorador (@) hace el registro, NO necesitas admin.site.register abajo
@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    fieldsets = (
        ("Parámetros de Ventas", {
            'fields': ('costo_envio',) 
        }),
    )

    def changelist_view(self, request, extra_context=None):
        config = Configuracion.objects.first()
        if not config:
            config = Configuracion.objects.create(costo_envio=5.00)
        return redirect(reverse('admin:inventario_configuracion_change', args=[config.id]))

    def has_add_permission(self, request):
        return False

    def has_delete_permission(self, request, obj=None):
        return False

# --- 3. REGISTROS SIMPLES ---
admin.site.register(Marca)
admin.site.register(Categoria)
admin.site.register(SubCategoria)
admin.site.register(TipoProducto)
admin.site.register(MovimientoStock)
admin.site.register(Gasto)
admin.site.register(Favorito)