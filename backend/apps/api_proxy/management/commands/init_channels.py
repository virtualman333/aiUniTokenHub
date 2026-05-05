from django.core.management.base import BaseCommand
from apps.ai_models.models import AIModel
from apps.api_proxy.models_channel import APIChannel, ModelChannelBinding


class Command(BaseCommand):
    help = '初始化API渠道和模型绑定配置'

    def handle(self, *args, **options):
        # 创建默认渠道（如果不存在）
        channel, created = APIChannel.objects.get_or_create(
            name='默认OpenAI兼容渠道',
            defaults={
                'provider_id': 1,  # 需要确保供应商存在
                'base_url': 'https://api.openai.com/v1',
                'api_key': '',  # 实际使用时填入真实API Key
                'status': 'active',
                'priority': 100,
                'is_default': True,
                'max_qps': 100,
                'timeout': 120,
            }
        )
        if created:
            self.stdout.write(f'Created channel: {channel.name}')

        # 获取所有活跃模型
        active_models = AIModel.objects.filter(status='active')
        
        for model in active_models:
            # 检查是否已有绑定
            existing_binding = ModelChannelBinding.objects.filter(model=model).exists()
            if not existing_binding:
                # 创建默认绑定
                binding = ModelChannelBinding.objects.create(
                    model=model,
                    channel=channel,
                    is_active=True,
                    priority=100
                )
                self.stdout.write(f'Created binding: {model.code} -> {channel.name}')
            else:
                self.stdout.write(f'Binding exists: {model.code}')

        self.stdout.write(self.style.SUCCESS('API渠道和模型绑定初始化完成！'))
        self.stdout.write(self.style.WARNING('注意：请确保在后台配置正确的渠道API Key和Base URL'))
