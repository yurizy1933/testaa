"""
模型序列化器基类
提供通用的序列化功能，减少重复代码
"""
from .constants import DATETIME_FORMAT


class ModelSerializer:
    """模型序列化器基类"""

    @staticmethod
    def format_datetime(dt):
        """格式化日期时间"""
        if dt is None:
            return None
        return dt.strftime(DATETIME_FORMAT)

    @staticmethod
    def serialize_common_fields(obj, fields):
        """序列化通用字段"""
        data = {}
        for field in fields:
            value = getattr(obj, field, None)
            if value is not None:
                data[field] = value
        return data


class ProjectSerializer(ModelSerializer):
    """项目序列化器"""

    @staticmethod
    def serialize(project):
        """序列化项目对象"""
        return {
            'id': project.id,
            'project_name': project.project_name,
            'description': project.description,
            'owner': project.owner,
            'create_time': ProjectSerializer.format_datetime(project.create_time),
            'update_time': ProjectSerializer.format_datetime(project.update_time),
            'doc_count': getattr(project, 'doc_count', 0)
        }


class CommonDocSerializer(ModelSerializer):
    """统一文档序列化器"""

    @staticmethod
    def serialize(doc, include_content=False):
        """序列化文档对象"""
        data = {
            'id': doc.id,
            'doc_type': doc.doc_type,
            'doc_type_display': doc.get_doc_type_display(),
            'file_type': doc.file_type,
            'file_type_display': doc.get_file_type_display(),
            'filename': doc.filename,
            'version': doc.version,
            'is_processed': doc.is_processed,
            'create_time': CommonDocSerializer.format_datetime(doc.create_time),
            'update_time': CommonDocSerializer.format_datetime(doc.update_time),
            'project_id': doc.project.id,
            'project_name': doc.project.project_name
        }
        if include_content and doc.file_content:
            data['file_content'] = doc.file_content
        return data
