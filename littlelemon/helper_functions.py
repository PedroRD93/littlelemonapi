from .models import Order, OrderItem
from .serializers import OrderItemSerializer


def build_order_item_list(order: Order) -> list(dict()):
    out = []

    order_items = OrderItem.objects.filter(order=order)
    for item in order_items:
        item_info = {}
        s_item = OrderItemSerializer(item)

        item_info['id'] = s_item.data['menuitem']
        item_info['quantity'] = s_item.data['quantity']
        item_info['unit_price'] = s_item.data['unit_price']
        item_info['price'] = s_item.data['price']
        out.append(item_info)

    return out


def attempt_parse_as_boolean(data):
    out = False

    try:
        int_value = int(data)
        if int_value > 0:
            out = True
    except ValueError:
        if type(data) == str:
            if data.title() == 'True':
                out = True
            elif data.title() == 'False':
                out = False
            else:
                out = data
        else:
            out = data

    return out


def is_null_string(string: str, empty_string=True) -> bool:
    possible_null = string.lower()
    if possible_null == 'null':
        return True
    if possible_null == 'none':
        return True
    if possible_null == 'nullptr':
        return True
    if empty_string:
        if possible_null == '':
            return True
    return False
