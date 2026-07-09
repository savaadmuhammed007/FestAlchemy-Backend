from django.contrib import admin
from .models import FestSettings, Category, Program, PosterTemplate

admin.site.register(FestSettings)
admin.site.register(Category)
admin.site.register(Program)
admin.site.register(PosterTemplate)
