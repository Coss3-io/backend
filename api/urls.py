from django.urls import path
from api.views.orders import OrderView, MakerView

urlpatterns = [
    path("/orders", OrderView.as_view(), name="orders"),
    path("/order", MakerView.as_view(), name="order")
]
