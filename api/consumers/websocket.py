from channels.generic.websocket import AsyncJsonWebsocketConsumer


class WebsocketConsumer(AsyncJsonWebsocketConsumer):
    groups = ["websocket"]

    async def send_json(self, content, close=False):
        return await super().send_json(content["data"], close)
