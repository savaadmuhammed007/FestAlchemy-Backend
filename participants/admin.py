from django.contrib import admin
from .models import Team, Member, CallingList

admin.site.register(Team)
admin.site.register(Member)
admin.site.register(CallingList)
