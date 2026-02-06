from .models import Producto
from django.db.models import F
from .carrito import Carrito

def importe_total_carrito(request):
    carrito = Carrito(request)
    total = carrito.get_total_price()
    return {"importe_total_carrito": total}

def cantidad_carrito(request):
    carrito = Carrito(request)
    return {"cantidad_carrito": len(carrito)}

def alertas_stock(request):
    """
    Muestra alertas al administrador si hay productos con poco stock.
    """
    if request.user.is_authenticated and request.user.is_staff:
        bajos = Producto.objects.filter(stock__lte=F('stock_minimo'))
    else:
        bajos = []
    return {'productos_bajo_stock': bajos}

def info_carrito(request):
    """
    Calcula la cantidad total de productos en el carrito para mostrar en el menú.
    """
    carrito = request.session.get('carrito', {})
    cantidad_total = 0
    
    if carrito:
        for item in carrito.values():
            if isinstance(item, dict):
                cantidad_total += item.get('cantidad', 0)
            elif isinstance(item, int):
                cantidad_total += item

    return {'cantidad_carrito': cantidad_total}