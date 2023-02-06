from django.urls import path
from littlelemon import views

urlpatterns = [

    path('menu-items', views.MenuItemsListView.as_view()),
    path('menu-items/', views.MenuItemsViewset.as_view({
            'get': 'list',
            'post': 'create',
            'list': 'list',
        })),
    path('menu-items/<int:pk>', views.MenuItemView.as_view()),
    path('categories', views.CategoryViewset.as_view({
            'get': 'list',
            'post': 'create',
        })),
    path('groups/manager/users', views.managers_list_assign),
    path('groups/manager/users/<int:pk>', views.managers_remove),
    path('groups/delivery-crew/users', views.delivery_list_assign),
    path('groups/delivery-crew/users/<int:pk>', views.delivery_remove),
    path('cart/menu-items', views.cart_view),
    path('cart/orders', views.OrdersView.as_view()),
    path('orders', views.OrdersView.as_view()),
    path('orders/<int:pk>', views.OrderView.as_view()),
]