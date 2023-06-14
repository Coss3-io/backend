from adrf.views import APIView

class WatchTowerview(APIView):
    """The view for the watch tower to commit order changes"""

    authentication_classes = [] #custom authentication here

    async def post(self, request):
        """Function used to update several orders at once""" 

        # /!\ the bot orders have to be updated properly 
        pass

    async def delete(self, request):
        """Function used for order cancellation"""