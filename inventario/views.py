import os
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages, admin
from django.contrib.auth.decorators import login_required
from django.http import JsonResponse, HttpResponse
from django.contrib.staticfiles import finders
from django.db import transaction # Vital para la base de datos
from django.db.models import Q, Min, Max, Sum
from django.template.loader import get_template
from django.conf import settings
from xhtml2pdf import pisa
from io import BytesIO
from django.contrib.auth import views as auth_views
from django.db.models import Sum      # <--- 1. IMPORTANTE: Para sumar
from django.utils import timezone     # <--- 2. IMPORTANTE: Para la fecha de hoy
from .models import Producto, Variacion, Pedido, LineaPedido, Categoria, Favorito, Gasto, Marca, Configuracion
from .forms import RegistroForm
from .carrito import Carrito 
from decimal import Decimal
from django.contrib.admin.views.decorators import staff_member_required
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.utils.html import strip_tags
from django.conf import settings
import base64

# --- VISTA DEL CARRITO ---
def vista_carrito(request):
    carrito = Carrito(request)
    
    # --- VALIDACIÓN DE STOCK REAL ---
    alerta_stock = False
    
    for key, item in carrito.carrito.items():
        producto = Producto.objects.get(id=item['producto_id'])
        
        # 1. Definimos cuánto stock hay realmente y cómo se llama lo que compran
        if item.get('variacion_id'):
            # CASO A: Es un producto con variaciones (Ej: Base Tono 1)
            try:
                variacion = Variacion.objects.get(id=item['variacion_id'])
                stock_real = variacion.stock
                nombre_producto = f"{producto.nombre} ({variacion.nombre})" # Ej: Base (Tono 1)
            except Variacion.DoesNotExist:
                stock_real = 0
                nombre_producto = f"{producto.nombre} (Variación no disponible)"
        else:
            # CASO B: Es un producto simple sin variaciones (Ej: Labial único)
            stock_real = producto.stock
            nombre_producto = producto.nombre

        # 2. Comparamos lo que pide el cliente vs lo que hay
        cantidad_pedida = int(item['cantidad'])
        
        if cantidad_pedida > stock_real:
            messages.error(
                request, 
                f"⚠️ Stock insuficiente para '{nombre_producto}'. Solo quedan {stock_real}."
            )
            alerta_stock = True
    # ------------------------------------------------

    pedidos_usuario = []
    if request.user.is_authenticated:
        pedidos_usuario = Pedido.objects.filter(usuario=request.user).order_by('-fecha')

    config = Configuracion.objects.first()
    costo_envio = config.costo_envio if config else Decimal("0.25")
    total_con_envio = float(carrito.get_total_price()) + float(costo_envio)

    return render(request, "carrito.html", {
        'carrito': carrito, 
        "pedidos_usuario": pedidos_usuario,
        "costo_envio": costo_envio,
        "total_con_envio": total_con_envio,
        "alerta_stock": alerta_stock # Pasamos esta bandera al HTML
    })

# --- PROCESAR PEDIDO (ARREGLADO: CONECTA CON STOCK) ---
@login_required
def procesar_pedido(request):
    if request.method == 'POST':
        carrito = Carrito(request)
        if not carrito.carrito:
            return JsonResponse({'status': 'false', 'message': 'El carrito está vacío'})

        try:
            with transaction.atomic():
                # 1. Preparar el Total (usando la configuración de envío)
                config = Configuracion.objects.first()
                costo_envio = float(config.costo_envio) if config else 0.25
                total_float = carrito.get_total_price() + costo_envio

                # 2. Crear Dirección
                dir_completa = (
                    f"{request.POST.get('calle_p', '')} y {request.POST.get('calle_s', '')}, "
                    f"Barrio: {request.POST.get('barrio', '')}. "
                    f"Ref: {request.POST.get('referencia', '')}."
                )

                # 3. Crear Pedido en BD
                pedido = Pedido.objects.create(
                    usuario=request.user,
                    estado='PENDIENTE',
                    nombre_destinatario=request.POST.get('nombre_destinatario'),
                    cedula=request.POST.get('cedula'),
                    telefono=request.POST.get('telefono'),
                    provincia=request.POST.get('provincia'),
                    canton=request.POST.get('canton'),
                    direccion=dir_completa,

                    referencia=request.POST.get('referencia', ''),

                    costo_envio=costo_envio, 
                    total=total_float
                    
                    
                )

                
                # 4. Guardar Líneas y Restar Stock (CORREGIDO)
                lineas = []
                for key, item in carrito.carrito.items():
                    prod = Producto.objects.select_for_update().get(id=item['producto_id'])
                    cant = int(item['cantidad'])
                    
                    # Recuperamos el nombre del tono del carrito
                    nombre_tono_guardar = item.get('variacion') # Ej: "Tono 1"

                    # Lógica de Restar Stock
                    if item.get('variacion_id'):
                        var = Variacion.objects.select_for_update().get(id=item['variacion_id'])
                        if var.stock >= cant:
                            var.stock -= cant
                            var.save()
                        else:
                            raise Exception(f"Sin stock para {prod.nombre} ({var.nombre})")
                    else:
                        if prod.stock >= cant:
                            prod.stock -= cant
                            prod.save()
                        else:
                            raise Exception(f"Sin stock para {prod.nombre}")

                    # CREAMOS LA LÍNEA CON EL TONO
                    lineas.append(LineaPedido(
                        pedido=pedido, 
                        producto=prod, 
                        variacion=nombre_tono_guardar, # <--- AQUÍ GUARDAMOS EL TONO
                        cantidad=cant, 
                        precio_unitario=Decimal(str(item['precio']))
                    ))

                LineaPedido.objects.bulk_create(lineas)

                # --- 5. EL CÓDIGO RECUPERADO: ENVIAR CORREO ---
                try:
                    subject = f'Confirmación de Pedido #{pedido.id} - Adrivo'
                    
                    # Usamos tu plantilla bonita 'emails/recibo.html'
                    html_content = render_to_string('emails/correo_recibo.html', {'pedido': pedido})
                    text_content = strip_tags(html_content) # Versión texto plano por si acaso

                    msg = EmailMultiAlternatives(
                        subject, 
                        text_content, 
                        settings.EMAIL_HOST_USER, 
                        [request.user.email] # Al correo del usuario logueado
                    )
                    msg.attach_alternative(html_content, "text/html")
                    msg.send()
                except Exception as e:
                    print("⚠️ El usuario no tiene email registrado, no se envió el correo.")
                    # No detenemos la venta si falla el correo, solo lo imprimimos en consola
                # ---------------------------------------------

                carrito.limpiar()
                return JsonResponse({'status': 'true', 'pedido_id': pedido.id})

        except Exception as e:
            return JsonResponse({'status': 'false', 'message': str(e)})
            
    return redirect('home')

# --- FUNCIONES CARRITO (CORREGIDAS) --

def agregar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    variacion_id = request.POST.get('variacion_id') 
    cantidad = int(request.POST.get('cantidad', 1))

    # VALIDACIÓN INSTANTÁNEA
    if variacion_id:
        from .models import Variacion
        var = get_object_or_404(Variacion, id=variacion_id)
        stock_disponible = var.stock
        nombre_error = f"{producto.nombre} ({var.nombre})"
    else:
        stock_disponible = producto.stock
        nombre_error = producto.nombre

    if cantidad > stock_disponible:
        return JsonResponse({
            'status': 'false', 
            'message': f"⚠️ Stock insuficiente. Solo quedan {stock_disponible} de '{nombre_error}'"
        })

    carrito.agregar(producto=producto, cantidad=cantidad, variacion_id=variacion_id)
    return JsonResponse({'status': 'true', 'cantidad_total': len(carrito.carrito)})

def sumar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    # 1. Recuperamos el ID de la variación desde la URL
    variacion_id = request.GET.get('variacion')
    if variacion_id == 'None' or variacion_id == '':
        variacion_id = None
        
    # 2. Se lo pasamos al carrito para que no lo olvide
    carrito.agregar(producto=producto, variacion_id=variacion_id)
    
    return redirect("carrito")

def restar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    
    # 1. Recuperamos el ID de la variación
    variacion_id = request.GET.get('variacion')
    if variacion_id == 'None' or variacion_id == '':
        variacion_id = None
        
    # 2. Restamos respetando el tono
    carrito.restar(producto=producto, variacion_id=variacion_id)
    
    return redirect("carrito")

def eliminar_producto(request, producto_id):
    carrito = Carrito(request)
    producto = get_object_or_404(Producto, id=producto_id)
    carrito.eliminar(producto)
    return redirect("carrito")

def limpiar_carrito(request):
    carrito = Carrito(request)
    carrito.limpiar()
    return redirect("carrito")

# --- RESTO DE TUS VISTAS (NO LAS TOQUÉ, ESTÁN IGUALES) ---

def tienda_home(request):
    productos = Producto.objects.filter(activo=True)
    categorias = Categoria.objects.prefetch_related('subcategorias__tipos').all()
    marcas = Producto.objects.values('marca__nombre', 'marca__id').distinct()

    cats_id = request.GET.getlist('categoria') 
    if cats_id: productos = productos.filter(tipo__subcategoria__categoria__id__in=cats_id)
    
    tipos_id = request.GET.getlist('tipo')
    if tipos_id: productos = productos.filter(tipo__id__in=tipos_id)

    marcas_id = request.GET.getlist('marca')
    if marcas_id: productos = productos.filter(marca__id__in=marcas_id)

    min_precio = request.GET.get('min_precio')
    max_precio = request.GET.get('max_precio')
    if min_precio and max_precio:
        productos = productos.filter(precio__gte=min_precio, precio__lte=max_precio)

    query = request.GET.get('q')
    if query:
        productos = productos.filter(Q(nombre__icontains=query) | Q(descripcion__icontains=query)).distinct()

    orden = request.GET.get('orden')
    if orden == 'precio_bajo': productos = productos.order_by('precio')
    elif orden == 'precio_alto': productos = productos.order_by('-precio')
    elif orden == 'relevancia': productos = productos.order_by('-id')

    rango_precios = Producto.objects.aggregate(Min('precio'), Max('precio'))
    precio_min_global = rango_precios['precio__min'] or 0
    precio_max_global = rango_precios['precio__max'] or 100
    
    cantidad_favoritos = 0
    productos_favoritos_ids = []
    if request.user.is_authenticated:
        qs_favs = Favorito.objects.filter(usuario=request.user)
        productos_favoritos_ids = qs_favs.values_list('producto_id', flat=True)
        cantidad_favoritos = qs_favs.count()

    context = {
        'productos': productos, 'categorias': categorias, 'marcas': marcas, 'query': query,
        'cats_selected': [int(x) for x in cats_id], 'tipos_selected': [int(x) for x in tipos_id],
        'marcas_selected': [int(x) for x in marcas_id], 'orden_actual': orden,
        'precio_min_global': precio_min_global, 'precio_max_global': precio_max_global,
        'filtro_min': min_precio or precio_min_global, 'filtro_max': max_precio or precio_max_global,
        'productos_favoritos_ids': list(productos_favoritos_ids), 'cantidad_favoritos': cantidad_favoritos,
    }
    return render(request, 'home.html', context)

def detalle_producto(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    return render(request, 'detalle.html', {'producto': producto})

def registro(request):
    if request.method == 'POST':
        form = RegistroForm(request.POST) 
        if form.is_valid():
            form.save()
            messages.success(request, "¡Cuenta creada!")
            return redirect('login')
    else:
        form = RegistroForm() 
    return render(request, 'registro.html', {'form': form})

def nosotros(request):
    return render(request, 'nosotros.html')

@login_required
def toggle_favorito(request, producto_id):
    producto = get_object_or_404(Producto, id=producto_id)
    fav, created = Favorito.objects.get_or_create(usuario=request.user, producto=producto)
    if not created: fav.delete()
    return JsonResponse({'es_favorito': created})

@login_required
def lista_favoritos(request):
    favoritos = Favorito.objects.filter(usuario=request.user).select_related('producto')
    return render(request, 'favoritos.html', {'favoritos': favoritos})

# En inventario/views.py

def descargar_comprobante(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    
    # --- BUSCADOR MAESTRO (FINDERS) ---
    # Lista de posibles nombres y ubicaciones (Django buscará por nosotros)
    nombres_posibles = [
        'css/logo_adrivo.jpg',   # La más probable
        'css/logo_adrivo.png',   # Por si es PNG
        'css/Logo_adrivo.jpg',   # Por si tiene mayúsculas
        'img/logo_adrivo.jpg',   # Por si está en img
        'logo_adrivo.jpg',       # Por si está en la raíz de static
        'inventario/static/css/logo_adrivo.jpg' # Ruta completa relativa
    ]
    
    logo_data = None
    ruta_encontrada = None

    print("--- INICIANDO BÚSQUEDA DE LOGO ---")
    
    for nombre in nombres_posibles:
        # Preguntamos a Django dónde está este archivo
        path = finders.find(nombre)
        
        if path:
            print(f"✅ ¡ENCONTRADO! Django dice que está en: {path}")
            try:
                with open(path, "rb") as image_file:
                    logo_data = base64.b64encode(image_file.read()).decode('utf-8')
                    ruta_encontrada = path
                break  # ¡Lo tenemos! Salimos del bucle.
            except Exception as e:
                print(f"❌ Encontré el archivo pero fallé al leerlo: {e}")
        else:
            print(f"   No encontrado: {nombre}")

    if not logo_data:
        print("⚠️ ALERTA FINAL: No se pudo cargar el logo de ninguna forma.")

    # Renderizamos
    context = {
        'pedido': pedido,
        'logo_base64': logo_data,
    }
    
    template = get_template('emails/recibo.html')
    html = template.render(context)
    
    result = BytesIO()
    pdf = pisa.pisaDocument(BytesIO(html.encode("UTF-8")), result)
    
    if not pdf.err:
        response = HttpResponse(result.getvalue(), content_type='application/pdf')
        response['Content-Disposition'] = f'attachment; filename="Orden_{pedido.id}.pdf"'
        return response
    
    return HttpResponse("Error generando PDF", status=400)

def eliminar_pedido(request, pedido_id):
    if request.method == "POST":
        pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
        if pedido.estado in ['ENTREGADO', 'CANCELADO']:
            pedido.delete()
            messages.success(request, "Eliminado.")
    return redirect('carrito')

def archivar_pedido(request, pedido_id):
    pedido = get_object_or_404(Pedido, id=pedido_id, usuario=request.user)
    if pedido.estado == 'ENTREGADO':
        pedido.estado = 'ARCHIVADO' 
        pedido.save()
    return redirect('carrito')

@staff_member_required
def punto_venta(request):
    productos = Producto.objects.filter(activo=True)
    carrito_pos = request.session.get('carrito_pos', {})
    
    # Manejo del "Cierre de Caja" (Filtramos por fecha o mostramos 0 si se cerró)
    caja_cerrada = request.session.get('caja_cerrada_flag', False)
    
    # Calcular Total del Carrito
    total_pos = sum(Decimal(str(item['subtotal'])) for item in carrito_pos.values())

    if request.method == 'POST':
        accion = request.POST.get('accion')
        
        # --- AGREGAR CON VALIDACIÓN DE STOCK ---
        if accion == 'agregar':
            p_id = request.POST.get('producto_id')
            v_id = request.POST.get('variacion_id')
            cantidad_solicitada = int(request.POST.get('cantidad', 1))
            producto = get_object_or_404(Producto, id=p_id)
            
            # 1. Identificar Producto o Variación y su Stock Real
            if v_id:
                variacion = get_object_or_404(Variacion, id=v_id)
                item_key = f"var_{v_id}"
                nombre = f"{producto.nombre} ({variacion.nombre})"
                precio = float(producto.precio)
                stock_disponible = variacion.stock
            else:
                item_key = f"prod_{p_id}"
                nombre = producto.nombre
                precio = float(producto.precio)
                stock_disponible = producto.stock

            # 2. Verificar cuánto ya tenemos en el carrito
            cantidad_en_carrito = 0
            if item_key in carrito_pos:
                cantidad_en_carrito = carrito_pos[item_key]['cantidad']

            # 3. VALIDACIÓN FINAL: ¿Hay suficiente para lo que pides + lo que ya tienes?
            if (cantidad_en_carrito + cantidad_solicitada) > stock_disponible:
                messages.error(request, f"🚫 Stock insuficiente. Solo quedan {stock_disponible} de {nombre}.")
            else:
                # Si hay stock, procedemos
                if item_key in carrito_pos:
                    carrito_pos[item_key]['cantidad'] += cantidad_solicitada
                    carrito_pos[item_key]['subtotal'] = precio * carrito_pos[item_key]['cantidad']
                else:
                    carrito_pos[item_key] = {
                        'tipo': 'variacion' if v_id else 'producto', 
                        'id_db': v_id if v_id else p_id, 
                        'nombre': nombre, 
                        'precio': precio, 
                        'cantidad': cantidad_solicitada, 
                        'subtotal': precio * cantidad_solicitada
                    }
                request.session['caja_cerrada_flag'] = False # Si vendemos, abrimos caja lógica
                request.session['carrito_pos'] = carrito_pos
            
            return redirect('punto_venta')

        elif accion == 'eliminar':
            item_key = request.POST.get('item_key')
            if item_key in carrito_pos:
                del carrito_pos[item_key]
                request.session['carrito_pos'] = carrito_pos
            return redirect('punto_venta')

        elif accion == 'cobrar':
            if carrito_pos:
                total_decimal = Decimal(str(total_pos))
                pedido = Pedido.objects.create(
                    usuario=request.user, total=total_decimal, 
                    direccion="🏪 Venta Local", metodo_pago="Efectivo"
                )
                
                for key, item in carrito_pos.items():
                    if item['tipo'] == 'variacion':
                        var = Variacion.objects.get(id=item['id_db'])
                        var.stock -= item['cantidad'] # Restamos Stock DB
                        var.save()
                        prod_real = var.producto
                    else:
                        prod = Producto.objects.get(id=item['id_db'])
                        prod.stock -= item['cantidad'] # Restamos Stock DB
                        prod.save()
                        prod_real = prod
                    
                    LineaPedido.objects.create(
                        pedido=pedido, producto=prod_real, 
                        cantidad=item['cantidad'], precio_unitario=Decimal(str(item['precio']))
                    )
                
                request.session['carrito_pos'] = {}
                messages.success(request, f"¡Venta registrada! Total: ${total_pos}")
            return redirect('punto_venta')

        # --- NUEVA ACCIÓN: CERRAR CAJA ---
        elif accion == 'cerrar_caja':
            # Calculamos ventas hasta el momento para el mensaje
            hoy = timezone.now().date()
            ventas_finales = Pedido.objects.filter(fecha__date=hoy, direccion="🏪 Venta Local").aggregate(Sum('total'))['total__sum'] or 0
            
            # Ponemos una bandera en la sesión para "ocultar" las ventas visualmente
            request.session['caja_cerrada_flag'] = True
            
            messages.info(request, f"🔒 CAJA CERRADA. Ganancias del turno: ${ventas_finales}")
            return redirect('punto_venta')

    # Lógica Visual de Caja
    hoy = timezone.now().date()
    ventas_reales = Pedido.objects.filter(fecha__date=hoy, direccion="🏪 Venta Local").aggregate(Sum('total'))['total__sum'] or 0
    
    # Si se cerró la caja, mostramos 0 visualmente, si no, mostramos las ventas reales
    ventas_hoy = 0.00 if caja_cerrada else float(ventas_reales)

    context = admin.site.each_context(request)
    context.update({
        'productos': productos, 
        'carrito_pos': carrito_pos, 
        'total_pos': total_pos,
        'ventas_hoy': ventas_hoy,
        'caja_cerrada': caja_cerrada, # Para saber si mostrar alerta en HTML
        'title': 'Punto de Venta'
    })
    return render(request, 'admin/punto_venta.html', context)

@staff_member_required
def reporte_stock(request):
    productos_qs = Producto.objects.all().order_by('stock')
    context = admin.site.each_context(request)
    context.update({'productos': productos_qs, 'title': 'Reporte de Stock'})
    return render(request, 'admin/stock_list.html', context)

@staff_member_required
def reporte_financiero(request):
    total_ingresos = Pedido.objects.all().aggregate(Sum('total'))['total__sum'] or 0
    total_gastos = Gasto.objects.all().aggregate(Sum('monto'))['monto__sum'] or 0
    ganancia_neta = total_ingresos - total_gastos
    ultimos_gastos = Gasto.objects.order_by('-fecha')[:5]
    ultimos_pedidos = Pedido.objects.order_by('-id')[:5]
    context = admin.site.each_context(request)
    context.update({'total_ingresos': total_ingresos, 'total_gastos': total_gastos, 'ganancia_neta': ganancia_neta, 'ultimos_gastos': ultimos_gastos, 'ultimos_pedidos': ultimos_pedidos, 'title': 'Reporte Financiero'})
    return render(request, 'admin/dashboard_contable.html', context)