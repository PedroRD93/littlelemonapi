from rest_framework import serializers
from django.contrib.auth.models import User, Group
from djoser.serializers import UserCreateSerializer
from .models import MenuItem, Category, Cart, Order, OrderItem
from decimal import Decimal
import bleach


class LLAPIUserCreateSerializer(UserCreateSerializer):
    def create(self, validated_data):
        user = super().create(validated_data)
        Group.objects.get(name="Customer").user_set.add(user)
        return user


class CategorySerializer(serializers.ModelSerializer):
    class Meta:
        model = Category
        fields = ['id', 'slug', 'title']

    def validate(self, data):
        return super().validate(data)

    def get_id_from_field(self):
        if type(self) is str:
            try:
                c_ref = Category.objects.filter(id=int(self))
                if c_ref:
                    return c_ref[0].id
            except ValueError:
                pass

            c_ref = Category.objects.filter(title=self)
            if c_ref:
                return c_ref[0].id

            c_ref = Category.objects.filter(slug=self)
            if c_ref:
                return c_ref[0].id

            raise serializers.ValidationError('Invalid category field: \'{}\''.format(self))
        elif type(self) is dict:
            if 'id' in self:
                c_ref = Category.objects.filter(id=self['id'])
                if c_ref:
                    return c_ref[0].id
                else:
                    raise serializers.ValidationError('Invalid category id \'{}\''.format(self['id']))
            elif 'title' in self:
                c_ref = Category.objects.filter(title=self['title'])
                if c_ref:
                    return c_ref[0].id
                else:
                    raise serializers.ValidationError('Invalid category title: \'{}\''.format(self['title']))
            elif 'slug' in self:
                c_ref = Category.objects.filter(slug=self['slug'])
                if c_ref:
                    return c_ref[0].id
                else:
                    raise serializers.ValidationError('Invalid category slug: \'{}\''.format(self['slug']))
            else:
                raise serializers.ValidationError('Invalid category field(s): \'{}\''.format(self))

        raise serializers.ValidationError('Invalid category data: \'{}\''.format(self))


class MenuItemSerializer(serializers.ModelSerializer):
    category = CategorySerializer()

    class Meta:
        model = MenuItem
        fields = ['id', 'title', 'price', 'featured', 'category']
        depth = 1

    def create(self, validated_data):
        c_ref = Category.objects.get(id=validated_data['category'])
        return MenuItem.objects.create(title=validated_data['title'], price=validated_data['price'], category=c_ref)

    def validate(self, data):
        out_data = {}

        errors = []

        if 'title' not in data:
            errors.append('Missing data: \'title\'.')
        if 'price' not in data:
            errors.append('Missing data: \'price\'.')

        if 'category' not in data:
            errors.append('Missing data: \'category\'.')

        if len(errors) > 0:
            raise serializers.ValidationError(errors)

        price = Decimal(bleach.clean(data['price']))
        if price > 75 or price < 0:
            raise serializers.ValidationError('Invalid price: expected range [0.0, 75.0].')

        out_data['price'] = price

        title = bleach.clean(data['title'])
        if len(title) > 100:
            raise serializers.ValidationError('Invalid title: exceeds character limit of 100.')

        out_data['title'] = title

        # validate the category data
        out_data['category'] = CategorySerializer.get_id_from_field(data['category'])

        return out_data

    def validate_partial_data(self):
        out_data = {}

        if 'price' in self:
            price = Decimal(bleach.clean(self['price']))
            if price > 75 or price < 0:
                raise serializers.ValidationError('Invalid price: expected range [0.0, 75.0].')

            out_data['price'] = price

        if 'title' in self:
            title = bleach.clean(self['title'])
            if len(title) > 100:
                raise serializers.ValidationError('Invalid title: exceeds character limit of 100.')

            out_data['title'] = title

        if 'category' in self:
            out_data['category'] = CategorySerializer.get_id_from_field(self['category'])

        return out_data


class UserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ['id', 'first_name', 'last_name', 'username', 'email']


class CartSerializer(serializers.ModelSerializer):
    class Meta:
        model = Cart
        fields = ['menuitem', 'quantity', 'unit_price', 'price']


class OrderSerializer(serializers.ModelSerializer):
    class Meta:
        model = Order
        depth = 1
        fields = ['id', 'delivery_crew', 'status', 'total', 'date']


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = ['id', 'menuitem', 'quantity', 'unit_price', 'price']
