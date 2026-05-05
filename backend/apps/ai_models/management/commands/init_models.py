from django.core.management.base import BaseCommand
from apps.ai_models.models import ModelProvider, ModelCategory, AIModel


class Command(BaseCommand):
    help = '初始化AI模型示例数据'

    def handle(self, *args, **options):
        # 创建供应商
        providers_data = [
            {'name': 'OpenAI', 'code': 'openai', 'logo': 'https://upload.wikimedia.org/wikipedia/commons/4/4d/OpenAI_Logo.svg', 'description': 'OpenAI开发的AI模型'},
            {'name': 'Anthropic', 'code': 'anthropic', 'logo': 'https://upload.wikimedia.org/wikipedia/commons/e/e5/Anthropic_logo.svg', 'description': 'Anthropic开发的Claude模型'},
            {'name': 'Google', 'code': 'google', 'logo': 'https://upload.wikimedia.org/wikipedia/commons/2/2f/Google_2015_logo.svg', 'description': 'Google AI开发的Gemini模型'},
            {'name': 'DeepSeek', 'code': 'deepseek', 'logo': '', 'description': '国产开源大模型'},
            {'name': '智谱AI', 'code': 'zhipu', 'logo': '', 'description': '智谱华章开发的GLM模型'},
        ]
        
        providers = {}
        for p in providers_data:
            obj, created = ModelProvider.objects.get_or_create(code=p['code'], defaults=p)
            providers[p['code']] = obj
            if created:
                self.stdout.write(f'Created provider: {p["name"]}')
        
        # 创建分类
        categories_data = [
            {'name': '大语言模型', 'code': 'llm', 'icon': 'chat'},
            {'name': '视觉模型', 'code': 'vision', 'icon': 'eye'},
            {'name': 'Embedding', 'code': 'embedding', 'icon': 'vector'},
            {'name': '语音合成', 'code': 'tts', 'icon': 'audio'},
        ]
        
        categories = {}
        for c in categories_data:
            obj, created = ModelCategory.objects.get_or_create(code=c['code'], defaults=c)
            categories[c['code']] = obj
            if created:
                self.stdout.write(f'Created category: {c["name"]}')
        
        # 创建模型
        models_data = [
            {
                'provider': providers['openai'],
                'category': categories['llm'],
                'name': 'GPT-4o',
                'code': 'gpt-4o',
                'input_price': 0.0000025,
                'output_price': 0.00001,
                'context_window': 128000,
                'max_tokens': 16384,
                'supports_vision': True,
                'supports_streaming': True,
                'supports_tools': True,
                'supports_json': True,
                'is_featured': True,
                'description': 'OpenAI最新多模态旗舰模型，支持文本、图像、音频理解',
                'tags': ['GPT-4', '多模态', '旗舰', '最新'],
            },
            {
                'provider': providers['openai'],
                'category': categories['llm'],
                'name': 'GPT-4 Turbo',
                'code': 'gpt-4-turbo',
                'input_price': 0.000007,
                'output_price': 0.000021,
                'context_window': 128000,
                'max_tokens': 4096,
                'supports_streaming': True,
                'supports_tools': True,
                'supports_json': True,
                'description': '高速版GPT-4，更低价格更快响应',
                'tags': ['GPT-4', '高速', '性价比'],
            },
            {
                'provider': providers['anthropic'],
                'category': categories['llm'],
                'name': 'Claude 3.5 Sonnet',
                'code': 'claude-3.5-sonnet',
                'input_price': 0.0000015,
                'output_price': 0.0000075,
                'context_window': 200000,
                'max_tokens': 8192,
                'supports_vision': True,
                'supports_streaming': True,
                'supports_tools': True,
                'is_featured': True,
                'is_new': True,
                'description': 'Anthropic最新旗舰模型，在编程和推理方面表现出色',
                'tags': ['Claude', '编程', '推理', '最新'],
            },
            {
                'provider': providers['anthropic'],
                'category': categories['llm'],
                'name': 'Claude 3 Opus',
                'code': 'claude-3-opus',
                'input_price': 0.00001,
                'output_price': 0.00003,
                'context_window': 200000,
                'max_tokens': 4096,
                'supports_vision': True,
                'supports_streaming': True,
                'description': 'Anthropic最强大模型，适合复杂推理和创意任务',
                'tags': ['Claude', '旗舰', '复杂推理'],
            },
            {
                'provider': providers['google'],
                'category': categories['llm'],
                'name': 'Gemini 1.5 Pro',
                'code': 'gemini-1.5-pro',
                'input_price': 0.00000125,
                'output_price': 0.000005,
                'context_window': 2000000,
                'max_tokens': 8192,
                'supports_vision': True,
                'supports_streaming': True,
                'is_featured': True,
                'description': 'Google最新模型，拥有200万token超长上下文',
                'tags': ['Gemini', '长上下文', '多模态', '最新'],
            },
            {
                'provider': providers['deepseek'],
                'category': categories['llm'],
                'name': 'DeepSeek V2',
                'code': 'deepseek-v2',
                'input_price': 0.00000014,
                'output_price': 0.00000028,
                'context_window': 128000,
                'max_tokens': 4096,
                'supports_streaming': True,
                'supports_json': True,
                'is_featured': True,
                'description': '国产开源强力模型，性价比极高',
                'tags': ['国产', '开源', '低价', '性价比'],
            },
            {
                'provider': providers['deepseek'],
                'category': categories['llm'],
                'name': 'DeepSeek Coder',
                'code': 'deepseek-coder',
                'input_price': 0,
                'output_price': 0,
                'context_window': 163840,
                'max_tokens': 4096,
                'supports_streaming': True,
                'description': '免费开源编程模型，专注代码生成',
                'tags': ['免费', '开源', '编程', '免费模型'],
            },
            {
                'provider': providers['zhipu'],
                'category': categories['llm'],
                'name': 'GLM-4',
                'code': 'glm-4',
                'input_price': 0.000001,
                'output_price': 0.000002,
                'context_window': 128000,
                'max_tokens': 4096,
                'supports_vision': True,
                'supports_streaming': True,
                'supports_tools': True,
                'description': '智谱AI最新旗舰模型，国产大模型代表',
                'tags': ['国产', 'GLM', '旗舰'],
            },
            {
                'provider': providers['openai'],  # 根据实际情况选择供应商
                'category': categories['llm'],
                'name': 'MIMO v2.5',
                'code': 'mimo-v2.5',
                'input_price': 0.000001,
                'output_price': 0.000002,
                'context_window': 128000,
                'max_tokens': 4096,
                'supports_streaming': True,
                'supports_json': True,
                'is_featured': True,
                'description': 'MIMO v2.5 智能助手模型',
                'tags': ['MIMO', '对话', '智能助手'],
            },
        ]
        
        for m in models_data:
            obj, created = AIModel.objects.get_or_create(
                provider=m['provider'],
                code=m['code'],
                defaults=m
            )
            if created:
                self.stdout.write(f'Created model: {m["name"]}')
        
        self.stdout.write(self.style.SUCCESS('AI模型示例数据初始化完成！'))
