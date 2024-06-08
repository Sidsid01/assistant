import json
import openai
import os
from dotenv import load_dotenv
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')

# Initialize APIs
openai.api_key = OPENAI_API_KEY

context = "You are Gracie, Sid's caring and funny friend. Your answers should be limited to 1-2 short sentences."
allow_speaking = True

def request_gpt(prompt: str) -> str:
    response = openai.ChatCompletion.create(
        model="gpt-4",
        messages=[
            {"role": "system", "content": context},
            {"role": "user", "content": prompt}
        ],
        max_tokens=150
    )
    return response['choices'][0]['message']['content'].strip()

async def handle_connection(websocket: WebSocket):
    global allow_speaking
    await websocket.accept()
    try:
        while True:
            try:
                message = await websocket.receive_text()
                print(f"Received a message")

                try:
                    data = json.loads(message)
                    print(f"Parsed data received")
                except json.JSONDecodeError as json_error:
                    print(f"JSON decode error: {json_error}")
                    continue

                if isinstance(data, dict) and 'input' in data:
                    prompt = data['input']
                    print(f"User input: {prompt}")

                    if "stop talking" in prompt.lower():
                        allow_speaking = False
                        await websocket.send_text(json.dumps({"response": "AI will stop talking."}))
                        continue

                    if allow_speaking:
                        response = request_gpt(prompt)
                        print(f"GPT-4 response: {response}")

                        await websocket.send_text(json.dumps({"response": response}))

            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
    except Exception as e:
        print(f"A critical error occurred: {e}")

app = FastAPI()

# CORS settings to allow WebSocket connections from the expected origin
origins = [
    "http://localhost",
    "http://localhost:8000",
    "http://127.0.0.1",
    "http://127.0.0.1:8000"
]

app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('templates/index.html')

@app.get("/chatbot.html")
def get_chatbot():
    return FileResponse("templates/chatbot.html")

@app.get("/{filename}")
def read_file(filename: str):
    return FileResponse(f"static/{filename}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_connection(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8766)
