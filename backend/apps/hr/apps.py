from django.apps import AppConfig


class HrConfig(AppConfig):
    default_auto_field = 'django.db.models.BigAutoField'
    name = 'apps.hr'
    verbose_name = '人事考勤'

    def ready(self):
        # 钉钉缺失功能补全：自动同步信号（建档/转正/调岗/离职/假期余额）
        from . import signals  # noqa: F401
