from django.contrib import admin
from .models.orders import Maker, Taker

# Register your models here.
admin.site.register(Maker)
admin.site.register(Taker)
