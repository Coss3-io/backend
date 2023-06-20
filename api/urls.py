from django.urls import path
from api.views.orders import OrderView, MakerView
from api.views.watch_tower import WatchTowerView
from api.views.user import UserView

app_name = "api"
urlpatterns = [
    path("acccount", UserView.as_view(), name="account"),
    path("orders", OrderView.as_view(), name="orders"),
    path("order", MakerView.as_view(), name="order"),
    path("wt/orders", WatchTowerView.as_view(), name="wt"),
]
