from django.urls import path
from api.views.orders import OrderView, MakerView
from api.views.watch_tower import WatchTowerView

app_name = "api"
urlpatterns = [
    path("orders", OrderView.as_view(), name="orders"),
    path("order", MakerView.as_view(), name="order"),
    path("wt/orders", WatchTowerView.as_view(), name="wt"),
]
