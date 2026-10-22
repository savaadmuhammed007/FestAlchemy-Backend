from django.apps import AppConfig


class JudgingConfig(AppConfig):
    name = 'judging'

    def ready(self):
        import judging.signals  # noqa
