from django.contrib import admin
from .models.orders import Maker, ReplaceMaker, Taker, ReplaceTaker

# Register your models here.
admin.site.register(Maker)
admin.site.register(ReplaceMaker)
admin.site.register(Taker)
admin.site.register(ReplaceTaker)
