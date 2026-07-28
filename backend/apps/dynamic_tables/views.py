from rest_framework import serializers
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .models import TableMeta
from . import services


class TableMetaSerializer(serializers.ModelSerializer):
    class Meta:
        model = TableMeta
        fields = ['id', 'key', 'label', 'table_name', 'columns', 'row_count', 'created_at']
        read_only_fields = ['table_name', 'row_count', 'created_at']


class DynamicTableView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        """动态表列表"""
        metas = TableMeta.objects.all()
        return Response(TableMetaSerializer(metas, many=True).data)

    def post(self, request):
        """上传 CSV 建表。

        multipart/form-data:
            file: CSV 文件
            key: URL 标识
            label: 显示名
        """
        file = request.FILES.get('file')
        key = request.data.get('key', '').strip().lower()
        label = request.data.get('label', '').strip()

        if not file or not key:
            return Response({'detail': '缺少 file 或 key 参数'}, status=400)
        if not key.replace('_', '').isalnum():
            return Response({'detail': 'key 仅允许字母数字下划线'}, status=400)
        if TableMeta.objects.filter(key=key).exists():
            return Response({'detail': f'表 key={key} 已存在'}, status=400)

        columns, rows = services.parse_csv(file)
        if not columns:
            return Response({'detail': 'CSV 无有效列'}, status=400)

        meta = services.create_dynamic_table(key, label or key, columns)
        written = services.insert_rows(meta, rows)
        return Response({
            **TableMetaSerializer(meta).data,
            'imported_rows': written,
            'columns': columns,
        }, status=201)


class DynamicTableDetailView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, key):
        """读取动态表数据，支持分页与搜索"""
        try:
            meta = TableMeta.objects.get(key=key)
        except TableMeta.DoesNotExist:
            return Response({'detail': '表不存在'}, status=404)

        page = int(request.query_params.get('page', 1))
        page_size = int(request.query_params.get('page_size', 20))
        search = request.query_params.get('search', '').strip()
        offset = (page - 1) * page_size

        rows, total = services.fetch_rows(meta, limit=page_size, offset=offset, search=search)
        return Response({
            'columns': meta.get_columns(),
            'results': rows,
            'count': total,
            'page': page,
            'page_size': page_size,
        })

    def delete(self, request, key):
        try:
            meta = TableMeta.objects.get(key=key)
        except TableMeta.DoesNotExist:
            return Response({'detail': '表不存在'}, status=404)
        services.drop_dynamic_table(meta)
        return Response({'detail': '已删除'}, status=204)
