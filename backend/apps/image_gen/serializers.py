from rest_framework import serializers
from .models import ImageGeneration, GeneratedImage


class GeneratedImageSerializer(serializers.ModelSerializer):
    image_url = serializers.SerializerMethodField()

    class Meta:
        model = GeneratedImage
        fields = ['id', 'image_url', 'revised_prompt', 'created_at']

    def get_image_url(self, obj):
        request = self.context.get('request')
        if obj.image and request:
            return request.build_absolute_uri(obj.image.url)
        return ''


class ImageGenerationSerializer(serializers.ModelSerializer):
    images = GeneratedImageSerializer(many=True, read_only=True)
    username = serializers.CharField(source='user.username', read_only=True)

    class Meta:
        model = ImageGeneration
        fields = [
            'id', 'username', 'model_code', 'mode', 'prompt',
            'size', 'quality', 'n', 'status', 'error_message',
            'cost', 'created_at', 'images',
        ]


class ImageGenerationCreateSerializer(serializers.Serializer):
    model_code = serializers.CharField(max_length=100, default='gpt-image-2')
    mode = serializers.ChoiceField(choices=['generate', 'edit'], default='generate')
    prompt = serializers.CharField()
    size = serializers.CharField(default='auto')
    quality = serializers.CharField(default='auto')
    n = serializers.IntegerField(min_value=1, max_value=5, default=1)
    image = serializers.ImageField(required=False, help_text='编辑模式下的参考图片')
