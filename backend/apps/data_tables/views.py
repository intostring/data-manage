from rest_framework import viewsets
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response

from .registry import table_registry


class DynamicModelViewSet(viewsets.ModelViewSet):
    """通用 ViewSet，通过类属性 model / serializer_class 绑定具体表。

    子类（由 urls.py 动态生成）设置这两个属性即可获得完整 CRUD。
    """
    model = None
    serializer_class = None

    def get_queryset(self):
        return self.model.objects.all()


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def list_tables(request):
    """返回所有已注册的已有表清单"""
    return Response([
        {'key': e.key, 'label': e.label, 'type': 'existing'}
        for e in table_registry.all()
    ])
