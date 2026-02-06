from django import template
from inventario.models import Producto, Pedido, LineaPedido
from django.db.models import Sum
import datetime
from django.utils import timezone

register = template.Library()

# 1. ESTADÍSTICAS BÁSICAS (Tarjetas de arriba)
@register.simple_tag
def get_dashboard_stats():
    total_productos = Producto.objects.filter(activo=True).count()
    total_pedidos = Pedido.objects.count()
    
    # Contar alertas de stock manualmente para asegurar precisión
    alertas = 0
    for p in Producto.objects.filter(activo=True):
        if p.stock <= p.stock_minimo:
            alertas += 1
            
    return {
        'total_productos': total_productos,
        'total_pedidos': total_pedidos,
        'alertas_stock': alertas,
    }

# 2. DATOS PARA EL GRÁFICO DE VENTAS (Últimos 6 meses)
@register.simple_tag
def get_sales_chart_data():
    today = timezone.now().date()
    labels = []
    data = []
    
    # Vamos 6 meses hacia atrás
    for i in range(5, -1, -1):
        # Calcular fecha aproximada
        d = today - datetime.timedelta(days=i*30)
        month_name = d.strftime("%B") # Nombre del mes
        
        # Sumar el total de ventas de ese mes y año
        sales = Pedido.objects.filter(
            fecha__year=d.year, 
            fecha__month=d.month
        ).aggregate(total=Sum('total'))['total'] or 0
        
        labels.append(month_name.capitalize()) # Ej: "Enero"
        data.append(float(sales)) # Ej: 150.50
        
    return {
        'labels': labels, 
        'data': data
    }

# 3. DATOS PARA EL GRÁFICO DE DONA (Top 5 Productos)
@register.simple_tag
def get_top_products_data():
    # Busca en LineaPedido cuáles productos se han vendido más
    top = LineaPedido.objects.values('producto__nombre').annotate(
        qty=Sum('cantidad')
    ).order_by('-qty')[:5]
    
    labels = [x['producto__nombre'] for x in top]
    data = [x['qty'] for x in top]
    
    # Si no hay ventas aún, mostramos datos de ejemplo para que no se vea vacío
    if not data:
        labels = ["Sin Datos", "Ejemplo 1", "Ejemplo 2"]
        data = [1, 1, 1]
        
    return {'labels': labels, 'data': data}