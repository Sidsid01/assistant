from fastapi import FastAPI, WebSocket, WebSocketDisconnect
import json
import base64
from gtts import gTTS
import numpy as np
import openai
import os
import pyaudio
import requests
from dotenv import load_dotenv
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
import time
import asyncio

# Load environment variables
load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

# Initialize APIs
openai.api_key = OPENAI_API_KEY

# Define constants
RECORDING_PATH = "audio/recording.wav"
RESPONSE_AUDIO_PATH = "audio/response.mp3"
os.makedirs(os.path.dirname(RECORDING_PATH), exist_ok=True)

context = "Your name is  Gracie, You are caring and funny friend. Your answers should be limited to 1-2 short sentences."
conversation = []

# Audio recording settings
CHUNK = 1024
FORMAT = pyaudio.paInt16
CHANNELS = 1
RATE = 16000
SILENCE_THRESHOLD = 500  # Silence threshold in RMS
SILENCE_DURATION = 3  # Duration of silence in seconds to stop recording

p = pyaudio.PyAudio()

is_speaking = False
allow_speaking = True

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/")
def read_root():
    return FileResponse('index.html')

@app.get("/voice_input.html")
def get_voice_input():
    return FileResponse("voice_input.html")

@app.get("/{filename}")
def read_file(filename: str):
    return FileResponse(filename)

# Function to handle OpenAI GPT request
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

# Function to transcribe audio
async def transcribe(file_name):
    url = "https://api.deepgram.com/v1/listen"
    headers = {
        "Authorization": f"Token {DEEPGRAM_API_KEY}",
        "Content-Type": "audio/wav"
    }
    try:
        with open(file_name, "rb") as audio:
            response = requests.post(url, headers=headers, data=audio)
            response.raise_for_status()
            transcript = response.json()["results"]["channels"][0]["alternatives"][0]["transcript"]
            return transcript
    except Exception as e:
        print(f"Transcription error: {e}")
        return ""

# Function to calculate RMS of audio frame
def rms(frame):
    count = len(frame) // 2
    shorts = np.frombuffer(frame, np.int16)
    sum_squares = np.sum(shorts ** 2)
    return np.sqrt(sum_squares / count)

# Function to record audio with extended silence detection
def record_audio():
    global is_speaking
    if is_speaking:
        return  # Do not start recording if the bot is speaking

    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    print("Listening...")
    frames = []
    silent_chunks = 0
    silence_started = None

    while True:
        data = stream.read(CHUNK)
        frames.append(data)

        rms_value = rms(data)
        if rms_value < SILENCE_THRESHOLD:
            if silence_started is None:
                silence_started = time.time()
            elif time.time() - silence_started > SILENCE_DURATION:
                silent_chunks += 1
                if silent_chunks > 2:  # Allow for brief pauses
                    break
        else:
            silent_chunks = 0
            silence_started = None

    print("Finished Thinking.")
    stream.stop_stream()
    stream.close()

    with open(RECORDING_PATH, 'wb') as wf:
        wf.write(b''.join(frames))

# Function to handle WebSocket connection
async def handle_connection(websocket: WebSocket):
    global context, is_speaking, allow_speaking
    await websocket.accept()
    try:
        while True:
            try:
                message = await websocket.receive_text()
                print(f"Received a message")

                # Try to parse the JSON data
                try:
                    data = json.loads(message)
                    print(f"Parsed data received")
                except json.JSONDecodeError as json_error:
                    print(f"JSON decode error: {json_error}")
                    continue

                # Explicitly check the type and content of the message
                if isinstance(data, dict) and 'input' in data:
                    prompt = data['input']
                    print(f"User input: {prompt}")

                    # Check if the input is a command to stop talking
                    if "stop talking" in prompt.lower():
                        allow_speaking = False
                        await websocket.send_text(json.dumps({"response": "AI will stop talking."}))
                        continue

                    # Generate response only if allowed to speak
                    if allow_speaking:
                        response = request_gpt(prompt)
                        print(f"GPT-4 response: {response}")

                        is_speaking = True
                        await websocket.send_text(json.dumps({"response": response}))
                        await asyncio.sleep(2)  # Ensure AI has finished speaking before allowing recording to start
                        is_speaking = False
                elif isinstance(data, dict) and data.get('action') == "start":
                    allow_speaking = True  # Allow speaking when the start button is clicked
                    while is_speaking:
                        await asyncio.sleep(1)  # Wait if AI is still speaking

                    await websocket.send_text(json.dumps({"status": "Recording started..."}))
                    await asyncio.sleep(1)  # Ensure AI has fully stopped
                    record_audio()
                    await websocket.send_text(json.dumps({"status": "Recording stopped, processing..."}))

                    print("Transcribing audio...")
                    transcript = await transcribe(RECORDING_PATH)
                    print(f"Transcription: {transcript}")

                    # Check if transcription contains the stop command
                    if "stop talking" in transcript.lower():
                        allow_speaking = False
                        await websocket.send_text(json.dumps({"response": "AI will stop talking."}))
                        continue

                    if not transcript:
                        if allow_speaking:
                            response = "Sorry, I couldn't understand what you said."
                            await websocket.send_text(json.dumps({"response": response}))
                    else:
                        # Generate response only if allowed to speak
                        if allow_speaking:
                            print("Generating GPT-4 response...")
                            response = request_gpt(transcript)
                            print(f"GPT-4 generated response: {response}")

                            is_speaking = True
                            await websocket.send_text(json.dumps({"status": "Speaking..."}))  # Notify client that AI is speaking

                            print("Generating TTS audio...")
                            tts = gTTS(text=response, lang='en')
                            tts.save(RESPONSE_AUDIO_PATH)
                            print("TTS audio generated.")

                            with open(RESPONSE_AUDIO_PATH, "rb") as audio_file:
                                audio_data = audio_file.read()
                            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

                            response_data = {
                                "transcription": transcript,
                                "response": response,
                                "audio_base64": audio_base64
                            }
                            await websocket.send_text(json.dumps(response_data))
                            print("Sent audio data to client.")

                            is_speaking = False
                            await websocket.send_text(json.dumps({"status": "Finished speaking"}))  # Notify client that AI finished speaking

                            print(f"\n--- USER: {transcript}\n--- Gracie: {response}\n")
                            await asyncio.sleep(2)  # Ensure AI has finished speaking before next recording
                elif isinstance(data, dict) and data.get('action') == 'upload' and 'audio' in data:
                    while is_speaking:
                        await asyncio.sleep(2)  # Wait if AI is still speaking

                    audio_bytes = bytes(data['audio'])
                    with open(RECORDING_PATH, 'wb') as audio_file:
                        audio_file.write(audio_bytes)
                    print("Received and saved audio file")

                    # Process the saved audio file
                    print("Transcribing saved audio file...")
                    transcript = await transcribe(RECORDING_PATH)
                    print(f"Transcription: {transcript}")

                    # Check if transcription contains the stop command
                    if "stop talking" in transcript.lower():
                        allow_speaking = False
                        await websocket.send_text(json.dumps({"response": "AI will stop talking."}))
                        continue

                    if not transcript:
                        if allow_speaking:
                            response = "Sorry, I couldn't understand what you said. Could please repeat that or click on start recording again?"
                            await websocket.send_text(json.dumps({"response": response}))
                    else:
                        # Generate response only if allowed to speak
                        if allow_speaking:
                            print("Generating GPT-4 response...")
                            response = request_gpt(transcript)
                            print(f"GPT-4 generated response: {response}")

                            is_speaking = True
                            await websocket.send_text(json.dumps({"status": "Speaking..."}))  # Notify client that AI is speaking

                            print("Generating TTS audio...")
                            tts = gTTS(text=response, lang='en')
                            tts.save(RESPONSE_AUDIO_PATH)
                            print("TTS audio generated.")

                            with open(RESPONSE_AUDIO_PATH, "rb") as audio_file:
                                audio_data = audio_file.read()
                            audio_base64 = base64.b64encode(audio_data).decode("utf-8")

                            response_data = {
                                "transcription": transcript,
                                "response": response,
                                "audio_base64": audio_base64
                            }
                            await websocket.send_text(json.dumps(response_data))
                            print("Sent audio data to client.")

                            is_speaking = False
                            await websocket.send_text(json.dumps({"status": "Finished speaking"}))  # Notify client that AI finished speaking

                            print(f"\n--- USER: {transcript}\n--- Gracie: {response}\n")
                            await asyncio.sleep(5)  # Ensure AI has finished speaking before next recording
                else:
                    print("Unknown message format or content")
            except WebSocketDisconnect:
                print("Client disconnected")
                break
            except Exception as e:
                print(f"Unexpected error: {e}")
    except Exception as e:
        print(f"A critical error occurred: {e}")

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await handle_connection(websocket)

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8765)
