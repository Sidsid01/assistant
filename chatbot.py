import asyncio
import os

import websockets
import openai
import json

# Load your OpenAI API key
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
openai.api_key = OPENAI_API_KEY

# Define the context for the chatbot
context = "You are a friendly and helpful chatbot. You are very intelligent. "

# Function to get a response from OpenAI's GPT-3.5 Turbo
async def get_openai_response(prompt):
    try:
        response = openai.ChatCompletion.create(
            model="gpt-3.5-turbo",
            messages=[
                {"role": "system", "content": context},
                {"role": "user", "content": prompt}
            ],
            max_tokens=150,
            temperature=0.7,
        )
        return response.choices[0].message['content'].strip()
    except Exception as e:
        print(f"Error getting response from OpenAI: {e}")
        return "Sorry, I am unable to respond at the moment."

# WebSocket handler function
async def handle_connection(websocket, path):
    try:
        async for message in websocket:
            # Parse the incoming message
            data = json.loads(message)
            user_input = data.get("input", "")

            # Get the response from OpenAI
            response = await get_openai_response(user_input)

            # Send the response back to the client
            response_data = {"response": response}
            await websocket.send(json.dumps(response_data))
    except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

# Start the WebSocket server
start_server = websockets.serve(handle_connection, "localhost", 8765)

# Run the WebSocket server
asyncio.get_event_loop().run_until_complete(start_server)
asyncio.get_event_loop().run_forever()
