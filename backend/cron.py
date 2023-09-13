from api.models.orders import Maker
from datetime import datetime

def deleting_expired_orders():
    """Cron job function to delete the expired orders from the database"""
    queryset = Maker.objects.filter(expiry__lte=datetime.now())
    queryset._raw_delete(queryset.db) #type: ignore

