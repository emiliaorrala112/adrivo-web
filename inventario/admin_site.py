from django import template
from inventario.models import Producto, Pedido, LineaPedido
from django.db.models import Sum, Count
import datetime
from django.utils import timezone

register = template.Library()

@register.simple_tag
def get_dashboard_stats():
    total_productos = Producto.objects.filter(activo=True).count()
    total_pedidos = Pedido.objects.count()
    alertas = 0
    for p in Producto.objects.filter(activo=True):
        if p.stock <= p.stock_minimo:
            alertas += 1
    return { 'total_productos': total_productos, 'total_pedidos': total_pedidos, 'alertas_stock': alertas }

@register.simple_tag
def get_sales_chart_data():
    today = timezone.now().date()
    labels, data = [], []
    for i in range(5, -1, -1):
        d = today - datetime.timedelta(days=i*30)
        month_name = d.strftime("%B")
        sales = Pedido.objects.filter(fecha__year=d.year, fecha__month=d.month).aggregate(total=Sum('total'))['total'] or 0
        labels.append(month_name.capitalize())
        data.append(float(sales))
    return {'labels': labels, 'data': data}

@register.simple_tag
def get_top_products_data():
    top = LineaPedido.objects.values('producto__nombre').annotate(qty=Sum('cantidad')).order_by('-qty')[:5]
    labels = [x['producto__nombre'] for x in top]
    data = [x['qty'] for x in top]
    if not data:
        labels = ["Sin Datos"]
        data = [1]
    return {'labels': labels, 'data': data}