import asyncio
from websockets.asyncio.client import connect
from websockets.exceptions import ConnectionClosed

# https://websockets.readthedocs.io/en/stable/howto/patterns.html
# https://websockets.readthedocs.io/en/stable/intro/examples.html#connect-a-client

URI = 'ws://localhost:8080'

async def producer_handler(websocket):
    while True:
        try:
            message = await produce()
            await websocket.send(message)
        except ConnectionClosed:
            print("Connection closed.")
            break


async def produce():
    # Server looks for the following commands:
    # 'n', 'b': next, back. For example, next instructions slide, next practice slide, next stimulus
    # 'f': fixation. Only valid during practice and actual study. We should show this before every practice and study trial.
    # 'i': go to instructions
    # 'p': go to practice
    # 's': go to beginning of stimuli
    
    # The block order and stimulus list is set in the web app client, so probably 
    message = await asyncio.to_thread(input, "Type command: ")
    return message

async def main():
    async with connect(URI) as websocket:
        print("Connected to server")
        await producer_handler(websocket)

asyncio.run(main())
