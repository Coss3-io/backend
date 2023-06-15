from django.contrib import admin
from api.models.orders import Maker, Taker

# Register your models here.
admin.site.register(Maker)
admin.site.register(Taker)
