from django.urls import path
from api.views.orders import OrderView, MakerView, BotView
from api.views.watch_tower import WatchTowerView
from api.views.user import UserView
from api.views.stacking import StackingView, StackingFeesView

app_name = "api"
urlpatterns = [
    path("acccount", UserView.as_view(), name="account"),
    path("orders", OrderView.as_view(), name="orders"),
    path("order", MakerView.as_view(), name="order"),
    path("stacking", StackingView.as_view(), name="stacking"),
    path("bot", BotView.as_view(), name="bot"),
    path("stacking-fees", StackingFeesView.as_view(), name="stacking-fees"),
    path("wt-orders", WatchTowerView.as_view(), name="wt"),
]
