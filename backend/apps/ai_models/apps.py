from django.apps import AppConfig
import django.core.management


class AIModelsConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.ai_models'
    verbose_name = 'AI模型'

    def ready(self):
        """应用启动时自动执行数据库迁移"""
        try:
            from django.db import connection
            from django.core.management import call_command
            
            # 检查数据库是否需要迁移
            with connection.cursor() as cursor:
                # 获取已应用的迁移
                cursor.execute("SELECT name FROM django_migrations WHERE app = %s ORDER BY id", [self.name])
                applied_migrations = set(row[0] for row in cursor.fetchall())
            
            # 获取所有迁移文件
            from pathlib import Path
            migrations_dir = Path(__file__).parent / 'migrations'
            if migrations_dir.exists():
                migration_files = set(
                    f.stem for f in migrations_dir.glob('*.py')
                    if f.stem not in ('__init__', '__pycache__')
                )
                
                # 检查是否有未应用的迁移
                pending_migrations = migration_files - applied_migrations
                if pending_migrations:
                    print(f"\n📦 检测到 {self.verbose_name} 有待执行迁移: {pending_migrations}")
                    print("🔄 正在执行数据库迁移...")
                    try:
                        call_command('migrate', '--run-syncdb', verbosity=1, interactive=False)
                        print("✅ 数据库迁移完成\n")
                    except Exception as e:
                        print(f"⚠️ 迁移过程中出现警告: {e}\n")
        except Exception as e:
            # 忽略迁移检查错误，避免影响应用启动
            pass
