from django.contrib import admin
from django.urls import path
from django.conf import settings
from django.conf.urls.static import static
from django.contrib.auth import views as auth_views
from inventario import views

urlpatterns = [
    # ADMIN Y REPORTES
    path('admin/reporte-stock/', views.reporte_stock, name='admin_stock_view'),
    path('admin/', admin.site.urls),
    path('reporte-financiero/', views.reporte_financiero, name='reporte_financiero'),
    path('pos/', views.punto_venta, name='punto_venta'),

    # TIENDA
    path('', views.tienda_home, name='home'),
    path('nosotros/', views.nosotros, name='nosotros'),
    path('producto/<int:producto_id>/', views.detalle_producto, name='detalle_producto'),

    # USUARIOS
    path('registro/', views.registro, name='registro'),
    path('login/', auth_views.LoginView.as_view(template_name='registration/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),

    # CARRITO Y PEDIDOS (Rutas corregidas)
    path('carrito/', views.vista_carrito, name='carrito'), 
    
    # ACCIONES DEL CARRITO (+, -, eliminar, procesar)
    path('sumar/<int:producto_id>/', views.agregar_producto, name="sumar"),
    path('restar/<int:producto_id>/', views.restar_producto, name="restar"),
    path('eliminar/<int:producto_id>/', views.eliminar_producto, name="eliminar"),
    path('limpiar/', views.limpiar_carrito, name="limpiar"),
    
    path('procesar_pedido/', views.procesar_pedido, name='procesar_pedido'),
    path('agregar-carrito/<int:producto_id>/', views.agregar_producto, name='agregar_carrito'),
    
    # GESTIÓN DE PEDIDOS
    path('eliminar_pedido/<int:pedido_id>/', views.eliminar_pedido, name='eliminar_pedido'),
    path('archivar/<int:pedido_id>/', views.archivar_pedido, name='archivar_pedido'),
    path('descargar-comprobante/<int:pedido_id>/', views.descargar_comprobante, name='descargar_comprobante'),

    # FAVORITOS
    path('favoritos/toggle/<int:producto_id>/', views.toggle_favorito, name='toggle_favorito'),
    path('mis-favoritos/', views.lista_favoritos, name='favoritos'),

    # PASSWORD RESET
    path('reset_password/', auth_views.PasswordResetView.as_view(), name='password_reset'),
    path('reset_password_sent/', auth_views.PasswordResetDoneView.as_view(), name='password_reset_done'),
    path('reset/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(), name='password_reset_confirm'),
    path('reset_password_complete/', auth_views.PasswordResetCompleteView.as_view(), name='password_reset_complete'),
    
]


urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
    