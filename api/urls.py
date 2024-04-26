from django.urls import path
from api.views.orders import (
    BatchUserOrdersView,
    OrderView,
    MakerView,
    BotView,
    TakerView,
)
from api.views.watch_tower import WatchTowerVerificationView, WatchTowerView
from api.views.user import UserCreateView, UserLogInView
from api.views.stacking import (
    StackingView,
    StackingFeesView,
    StackingFeesWithdrawalView,
    GlobalStackingView,
)

app_name = "api"
urlpatterns = [
    path("account", UserCreateView.as_view(), name="account"),
    path("login", UserLogInView.as_view(), name="login"),
    path("orders", OrderView.as_view(), name="orders"),
    path("batch-orders", BatchUserOrdersView.as_view(), name="batch-orders"),
    path("order", MakerView.as_view(), name="order"),
    path("taker", TakerView.as_view(), name="taker"),
    path("stacking", StackingView.as_view(), name="stacking"),
    path("bot", BotView.as_view(), name="bot"),
    path("stacking-fees", StackingFeesView.as_view(), name="stacking-fees"),
    path(
        "fees-withdrawal", StackingFeesWithdrawalView.as_view(), name="fees-withdrawal"
    ),
    path("global-stacking", GlobalStackingView.as_view(), name="global-stacking"),
    path("wt", WatchTowerView.as_view(), name="wt"),
    path("wt-verification", WatchTowerVerificationView.as_view(), name="wt-verification"),
]
