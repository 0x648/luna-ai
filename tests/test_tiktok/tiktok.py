from TikTokLive import TikTokLiveClient
from TikTokLive.types.events import CommentEvent, ConnectEvent, DisconnectEvent, JoinEvent

proxies = {
    "http://": "http://127.0.0.1:10809",
    "https://": "http://127.0.0.1:10809"
}

# Instantiate the client with the user's username
client: TikTokLiveClient = TikTokLiveClient(unique_id="@markus864", proxies=proxies)


# Define how you want to handle specific events via decorator
@client.on("connect")
async def on_connect(_: ConnectEvent):
    print("Connected to Room ID:", client.room_id)

@client.on("disconnect")
async def on_disconnect(event: DisconnectEvent):
    print("Disconnected")

@client.on("join")
async def on_join(event: JoinEvent):
    print(f"@{event.user.unique_id} joined the stream!")

# Notice no decorator?
async def on_comment(event: CommentEvent):
    print(f"{event.user.nickname} -> {event.comment}")


# Define handling an event via a "callback"
client.add_listener("comment", on_comment)

if __name__ == '__main__':
    # Run the client and block the main thread
    # await client.start() to run non-blocking
    client.run()