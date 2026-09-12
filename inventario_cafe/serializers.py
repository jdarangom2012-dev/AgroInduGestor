from rest_framework import serializers
from .models import InventarioCafe


class InventarioCafeSerializer(serializers.ModelSerializer):
    empaquecafe_nombre = serializers.CharField(source='empaquecafe.empaque_cafe', read_only=True)
    cantidad_existente = serializers.FloatField(read_only=True)
    class Meta:
        model = InventarioCafe
        fields = '__all__'
