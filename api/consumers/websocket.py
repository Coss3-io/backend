from channels.generic.websocket import AsyncJsonWebsocketConsumer


class WebsocketConsumer(AsyncJsonWebsocketConsumer):
    groups = ["websocket"]

    async def websocket_connect(self, message):
        base = str(self.scope["url_route"]["kwargs"].get("base", "")).lower()
        quote = str(self.scope["url_route"]["kwargs"].get("quote", "")).lower()
        chain_id = str(self.scope["url_route"]["kwargs"].get("chain_id", "")).lower()
        await self.channel_layer.group_add(f"{chain_id}{base}{quote}", self.channel_name)  # type: ignore
        return await super().websocket_connect(message)

    async def websocket_disconnect(self, message):
        await self.channel_layer.group_discard(group, self.channel_name)  # type: ignore
        return await super().websocket_disconnect(message)

    async def send_json(self, content, close=False):
        return await super().send_json(content["data"], close)
