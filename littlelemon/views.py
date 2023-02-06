import datetime

from django.contrib.auth.models import User, Group
from django.core import exceptions
from django.db.utils import IntegrityError
from django.utils.datastructures import MultiValueDictKeyError
from rest_framework import generics, viewsets
from rest_framework.decorators import api_view, permission_classes, throttle_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.serializers import ValidationError

from .helper_functions import build_order_item_list, attempt_parse_as_boolean, is_null_string
from .models import MenuItem, Category, Cart, Order, OrderItem
from .permissions import IsCustomer, IsManager
from .serializers import MenuItemSerializer, CategorySerializer, UserSerializer, CartSerializer, OrderSerializer
from .throttles import TenCallsPerMinute


class MenuItemsListView(generics.ListCreateAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    ordering_fields = ['category', 'title', 'price']
    search_fields = ['category__title']
    throttle_classes = [TenCallsPerMinute]

    def post(self, request, **kwargs):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'Unauthorized Access'}, status=403)

        try:
            serial_item = MenuItemSerializer()
            valid_data = serial_item.validate(request.data)
            if MenuItem.objects.filter(title=valid_data['title']).exists():
                return Response({'message': 'Menu item \'{}\' already exists'}, status=400)
            new_item = serial_item.create(valid_data)
            new_item.save()
            return Response({'message': 'menu item successfully created'}, status=201)
        except ValidationError as e:
            return Response({'error': str(e)}, status=400)


class MenuItemsViewset(viewsets.ModelViewSet):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    ordering_fields = ['category', 'title', 'price']
    search_fields = ['category__title']
    throttle_classes = [TenCallsPerMinute]


class MenuItemView(generics.RetrieveUpdateDestroyAPIView):
    queryset = MenuItem.objects.all()
    serializer_class = MenuItemSerializer
    permission_classes = [IsAuthenticated]
    throttle_classes = [TenCallsPerMinute]
    lookup_field = 'id'

    def get(self, request, pk):
        try:
            item = MenuItem.objects.get(pk=pk)
            return Response(self.serializer_class(item).data, status=200)
        except MenuItem.DoesNotExist:
            return Response({'error': 'no MenuItem with id {}'.format(pk)}, status=404)

    def post(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'Unauthorized Access'}, status=403)
        return Response({'message': '\'POST\' not supported for this endpoint'}, status=400)

    def put(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'Unauthorized Access'}, status=403)

        try:
            item = MenuItem.objects.get(pk=pk)
            serial_item = MenuItemSerializer()
            valid_data = serial_item.validate(request.data)

            item.title = valid_data['title']
            item.price = valid_data['price']
            item.category = Category.objects.get(id=valid_data['category'])

            item.save()
            return Response({'message': 'Menu item \'{}\' successfully updated'.format(item.title)}, status=200)
        except ValidationError as e:
            return Response({'message': str(e)}, status=400)
        except MenuItem.DoesNotExist:
            return Response({'message': 'Menu item \'{}\' does not exist'.format(pk)}, status=400)

    def patch(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'Unauthorized Access'}, status=403)

        try:
            item = MenuItem.objects.get(pk=pk)
            data = MenuItemSerializer.validate_partial_data(request.data)

            if 'title' in data:  item.title = data['title']
            if 'price' in data:  item.price = data['price']
            if 'category' in data: item.category = Category.objects.get(id=data['category'])

            item.save()
            return Response({'message': 'Menu item \'{}\' updated'.format(item.title)}, status=200)
        except MenuItem.DoesNotExist:
            return Response({'message': 'Invalid menu item id: \'{}\''.format(pk)}, status=404)
        except ValidationError as e:
            return Response({'message': str(e)}, status=404)

    def delete(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'Unauthorized Access'}, status=403)

        try:
            item = MenuItem.objects.get(pk=pk)
            item.delete()
        except MenuItem.DoesNotExist:
            return Response({'message': 'Menu item does not exist.'}, status=400)

        return Response({'message': 'Menu item deleted'}, status=200)


class CategoryViewset(viewsets.ModelViewSet):
    queryset = Category.objects.all()
    serializer_class = CategorySerializer
    throttle_classes = [TenCallsPerMinute]
    search_fields = ['title']


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated, IsManager])
@throttle_classes([TenCallsPerMinute])
def managers_list_assign(request):
    if request.method == 'GET':
        managers = Group.objects.get(name='Manager')
        serial = UserSerializer(managers.user_set, many=True)
        return Response(serial.data, status=200)

    if request.method == 'POST':
        einfo = None
        try:
            managers = Group.objects.get(name='Manager')
            if 'id' in request.data:
                einfo = 'id: \'{}\''.format(request.data['id'])
                user = User.objects.get(id=request.data['id'])
                managers.user_set.add(user)
                return Response({'message': 'User \'{}\' added to Manager Group'.format(user.username)}, status=201)
            if 'username' in request.data:
                einfo = 'username: \'{}\''.format(request.data['username'])
                user = User.objects.get(username=request.data['username'])
                managers.user_set.add(user)
                return Response({'message': 'User \'{}\' added to Manager Group'.format(user.username)}, status=201)
            return Response({'error': 'Missing valid User id or username'}, status=400)
        except User.DoesNotExist:
            return Response({'error': 'No user found with {}'.format(einfo)}, status=404)


@api_view(['DELETE'])
@permission_classes({IsAuthenticated, IsManager})
@throttle_classes([TenCallsPerMinute])
def managers_remove(request, pk):
    try:
        user = User.objects.get(pk=pk)
        managers = Group.objects.get(name='Manager')
        managers.user_set.remove(user)
        return Response({'message': 'Successfully removed \'{}\' from Manager group.'.format(user.username)},
                        status=200)
    except User.DoesNotExist:
        return Response({'message': 'No user found with id: \'{}\''.format(pk)}, status=404)


@api_view(['GET', 'POST'])
@permission_classes({IsAuthenticated, IsManager})
@throttle_classes([TenCallsPerMinute])
def delivery_list_assign(request):
    if request.method == 'GET':
        managers = Group.objects.get(name='Delivery Crew')
        serial = UserSerializer(managers.user_set, many=True)
        return Response(serial.data, status=200)

    if request.method == 'POST':
        einfo = None
        try:
            managers = Group.objects.get(name='Delivery Crew')
            if 'id' in request.data:
                einfo = 'id: \'{}\''.format(request.data['id'])
                user = User.objects.get(id=request.data['id'])
                managers.user_set.add(user)
                return Response({'message': 'User \'{}\' added to Delivery Crew Group'.format(user.username)},
                                status=201)
            if 'username' in request.data:
                einfo = 'username: \'{}\''.format(request.data['username'])
                user = User.objects.get(username=request.data['username'])
                managers.user_set.add(user)
                return Response({'message': 'User \'{}\' added to Delivery Crew group'.format(user.username)},
                                status=201)
            return Response({'message': 'Missing valid User id or username'}, status=400)
        except User.DoesNotExist:
            return Response({'message': 'No user found with {}'.format(einfo)}, status=404)


@api_view(['DELETE'])
@permission_classes({IsAuthenticated, IsManager})
@throttle_classes([TenCallsPerMinute])
def delivery_remove(request, pk):
    try:
        user = User.objects.get(pk=pk)
        delivery_crew = Group.objects.get(name='Delivery Crew')
        delivery_crew.user_set.remove(user)
        return Response({'message': 'Successfully removed \'{}\' from Delivery Crew group.'.format(user.username)},
                        status=200)
    except User.DoesNotExist:
        return Response({'message': 'No user found with id: \'{}\''.format(pk)}, status=404)


@api_view(['GET', 'POST', 'DELETE'])
@permission_classes([IsAuthenticated, IsCustomer])
@throttle_classes([TenCallsPerMinute])
def cart_view(request):
    if request.method == 'GET':
        items = Cart.objects.filter(user=request.user)
        serial = CartSerializer(items, many=True)
        return Response(serial.data, status=200)

    if request.method == 'POST':
        menuitem = None
        try:
            try:
                menuitem = MenuItem.objects.filter(id=int(request.data['menuitem']))
                if not menuitem.exists():
                    return Response({'message': 'menu item \'{}\' not found'.format(request.data['menuitem'])},
                                    status=404)
                menuitem = menuitem[0]
            except ValueError:
                menuitem = MenuItem.objects.filter(title=request.data['menuitem'])
                if not menuitem.exists():
                    return Response({'message': 'menu item \'{}\' not found'.format(request.data['menuitem'])},
                                    status=404)
                menuitem = menuitem[0]
            user = request.user
            quantity = int(request.data['quantity'])
            unit_price = menuitem.price
            price = quantity * unit_price

            cart = Cart.objects.create(user=user, menuitem=menuitem, quantity=quantity, unit_price=unit_price,
                                       price=price)
            cart.save()
            return Response({'message': 'cart updated'}, status=200)
        except MultiValueDictKeyError as e:
            return Response({'message': 'Missing named variable {}'.format(str(e))}, status=404)
        except ValueError as e:
            return Response({'message': 'quantity value \'{}\' invalid.'.format(str(e))}, status=404)
        except IntegrityError:
            return Response({'message': 'MenuItem is already present in cart.'}, status=400)
        except Exception as e:
            return Response({'message': str(type(e)) + str(e)}, status=404)

    if request.method == 'DELETE':
        cart = Cart.objects.filter(user=request.user).delete()
        return Response({'message': 'cart has been emptyed for user \'{}\''.format(request.user.username)}, status=200)


class OrdersView(generics.ListCreateAPIView):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [TenCallsPerMinute]

    def get(self, request):
        if request.user.groups.filter(name="Customer").exists():
            try:
                orders = Order.objects.filter(user=request.user)
                output = []
                index = 0
                for order in orders:
                    serial = OrderSerializer(order)
                    output.append(serial.data)
                    if output[index]['delivery_crew']:
                        output[index]['delivery_crew'] = output[index]['delivery_crew']['username']
                    output[index]['orderitems'] = build_order_item_list(order)
                    index += 1
                return Response(output, status=200)
            except Order.DoesNotExist:
                return Response('requested order does not exist', status=404)

        if request.user.groups.filter(name="Delivery Crew").exists():
            try:
                orders = Order.objects.filter(delivery_crew=request.user)
                output = []
                index = 0
                for order in orders:
                    serial = OrderSerializer(order)
                    output.append(serial.data)
                    if output[index]['delivery_crew']:
                        output[index]['delivery_crew'] = output[index]['delivery_crew']['username']
                    output[index]['orderitems'] = build_order_item_list(order)
                    index += 1
                return Response(output, status=200)
            except Order.DoesNotExist:
                return Response('requested order does not exist', status=404)

        if request.user.groups.filter(name="Manager").exists():
            try:
                output = []
                users = User.objects.all()
                iu = 0
                for user in users:
                    orders = Order.objects.filter(user=user)
                    if not orders:
                        continue

                    output.append(UserSerializer(user).data)
                    output[iu]['orders'] = []
                    io = 0
                    for order in orders:
                        serial = OrderSerializer(order)
                        output[iu]['orders'].append(serial.data)
                        if output[iu]['orders'][io]['delivery_crew']:
                            output[iu]['orders'][io]['delivery_crew'] = output[iu]['orders'][io]['delivery_crew'][
                                'username']
                        output[iu]['orders'][io]['orderitems'] = build_order_item_list(order)
                        io += 1
                    iu += 1
                return Response(output, status=200)
            except Order.DoesNotExist as e:
                return Response('requested order does not exist', status=404)

        return Response({'message': 'unauthorized access'}, status=403)

    def post(self, request):
        if not request.user.groups.filter(name="Customer").exists():
            return Response({'message': 'Unauthorized access.'}, status=403)
        try:
            cart = Cart.objects.filter(user=request.user)
            if not cart.exists():
                return Response({'message': 'no items are currently in cart'}, status=400)
            if 'date' in request.data:
                order_date = request.data
            else:
                order_date = datetime.datetime.now()
            new_order = Order.objects.create(user=request.user, total=0, date=datetime.datetime.now())
            new_order.save()
            total = 0
            for item in cart:
                new_order.total += item.price
                orderitem = OrderItem.objects.create(order=new_order, menuitem=item.menuitem, quantity=item.quantity,
                                                     unit_price=item.unit_price, price=item.price)
                orderitem.save()
            new_order.save()
            cart.delete()
            return Response({'message': 'order number {:06d} placed.'.format(new_order.id)}, status=201)
        except Exception as e:
            new_order.delete()
            return Response(str(e), status=400)


class OrderView(generics.RetrieveUpdateDestroyAPIView):
    queryset = Order.objects.all()
    permission_classes = [IsAuthenticated]
    throttle_classes = [TenCallsPerMinute]

    def get(self, request, pk):
        if request.user.groups.filter(name="Customer").exists():
            try:
                order = Order.objects.get(id=pk)
                if request.user != order.user:
                    return Response({'message': 'order {} does not belong to customer'.format(pk)}, status=403)
                output = OrderSerializer(order).data
                if output['delivery_crew']:
                    output['delivery_crew'] = order.delivery_crew.id
                output['orderitems'] = build_order_item_list(order)
                return Response(output, status=200)

            except Order.DoesNotExist:
                return Response({'message': 'order number {} not found.'.format(pk)}, status=404)
        return Response({'message': 'unathorized access. Customer endpoint'}, status=403)

    def put(self, request, pk):
        if request.user.groups.filter(name="Delivery Crew").exists():
            try:
                order = Order.objects.get(id=pk)
                order.status = attempt_parse_as_boolean(request.data['status'])
                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        if request.user.groups.filter(name="Manager").exists():
            try:
                order = Order.objects.get(id=pk)
                order.status = attempt_parse_as_boolean(request.data['status'])
                if is_null_string(request.data['delivery_crew']):
                    order.delivery_crew = None
                else:
                    order.delivery_crew = User.objects.get(id=request.data['delivery_crew'])

                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except User.DoesNotExist:
                return Response({'error': 'delivery_crew {} not found'.format(pk)}, status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        if request.user.groups.filter(name="Customer").exists():
            try:
                order = Order.objects.get(id=pk)
                if order.user != request.user:
                    return Response({'error': 'order does not belong to user'}, status=400)
                if order.delivery_crew != None:
                    if order.status:
                        return Response({'error': 'orders can not be modified after delivery'}, status=400)
                    else:
                        return Response({'error': 'orders can not be modified while being delivered'}, status=400)
                orderitems = OrderItem.objects.filter(order=order)
                item = orderitems.get(id=request.data['id'])

                delta_price = 0
                item.qantity = request.data['quantity']
                item.menuitem = MenuItem.objects.get(id=request.data['menuitem'])
                item.unit_price = item.menuitem.price
                delta_price = item.price
                item.price = item.unit_price * item.quantity
                delta_price = item.price - delta_price
                order.total += delta_price
                item.save()
                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except OrderItem.DoesNotExist:
                return Response({'error': 'orderitem {} not found in order {}'.format(request.data['id'], pk)},
                                status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        return Response({'message': 'unauthorizd access'}, status=403)

    def patch(self, request, pk):
        if request.user.groups.filter(name="Manager").exists():
            try:
                order = Order.objects.get(id=pk)
                if 'status' in request.data:
                    order.status = attempt_parse_as_boolean(request.data['status'])
                if 'username' in request.data:
                    if is_null_string(request.data['username']):
                        order.delivery_crew = None
                    else:
                        order.delivery_crew = User.objects.get(username=request.data['username'])

                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except User.DoesNotExist:
                return Response({'error': 'delivery_crew {} not found'.format(pk)}, status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        if request.user.groups.filter(name="Delivery Crew").exists():
            try:
                order = Order.objects.get(id=pk)
                order.status = attempt_parse_as_boolean(request.data['status'])
                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        if request.user.groups.filter(name="Customer").exists():
            try:
                order = Order.objects.get(id=pk)
                if order.user != request.user:
                    return Response({'error': 'order does not belong to user'}, status=400)
                if order.delivery_crew != None:
                    if order.status:
                        return Response({'error': 'orders can not be modified after delivery'}, status=400)
                    else:
                        return Response({'error': 'orders can not be modified while being delivered'}, status=400)
                orderitems = OrderItem.objects.filter(order=order)
                item = orderitems.get(id=request.data['id'])

                delta_price = 0
                if 'quantity' in request.data:
                    item.qantity = request.data['quantity']
                if 'menuitem' in request.data:
                    item.menuitem = MenuItem.objects.get(id=request.data['menuitem'])
                    item.unit_price = item.menuitem.price
                    delta_price = item.price
                    item.price = item.unit_price * item.quantity
                    delta_price = item.price - delta_price
                order.total += delta_price
                item.save()
                order.save()
                return Response({'message': 'order status successfully updated'}, status=200)
            except Order.DoesNotExist:
                return Response({'error': 'order {} not found'.format(pk)}, status=404)
            except OrderItem.DoesNotExist:
                return Response({'error': 'orderitem {} not found in order {}'.format(request.data['id'], pk)},
                                status=404)
            except MultiValueDictKeyError as e:
                return Response({'error': 'missing expected key {}'.format(str(e))}, status=400)
            except exceptions.ValidationError as e:
                return Response({'error': 'status: expected boolean value of true, false, 0, or 1'}, status=400)
            except Exception as e:
                return Response({'error': str(type(e)) + str(e)}, status=400)

        return Response({'message': 'unauthorizd access'}, status=403)

    def delete(self, request, pk):
        if not request.user.groups.filter(name="Manager").exists():
            return Response({'message': 'unauthorizd access'}, status=403)
        try:
            order = Order.objects.get(id=pk)
            order.delete()
            return Response({'message': 'order {} deleted'.format(pk)}, status=200)
        except Order.DoesNotExist:
            return Response({'error': 'order {} not found'.format(pk)}, status=404)
