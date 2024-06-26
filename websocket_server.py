import asyncio
import json
import os
import websockets
import numpy as np
import pyaudio
from gtts import gTTS
import openai
import requests
import base64
from dotenv import load_dotenv

load_dotenv()
OPENAI_API_KEY = os.getenv('OPENAI_API_KEY')
DEEPGRAM_API_KEY = os.getenv('DEEPGRAM_API_KEY')

# Initialize APIs
openai.api_key = OPENAI_API_KEY

# Define constants
RECORDING_PATH = "audio/recording.wav"
RESPONSE_AUDIO_PATH = "audio/response.mp3"
os.makedirs(os.path.dirname(RECORDING_PATH), exist_ok=True)

context = "You are Gracie, Sid's personal caring and funny friend. Your answers should be limited to 1-2 short sentences."
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

async def handle_connection(websocket, path):
    global context, is_speaking
    try:
        async for message in websocket:
            if isinstance(message, str):
                data = json.loads(message)
                if 'input' in data:
                    prompt = data['input']
                    print(f"User: {prompt}")

                    response = request_gpt(prompt)
                    print(f"Dave: {response}")

                    await websocket.send(json.dumps({"response": response}))
                elif message == "start":
                    await websocket.send(json.dumps({"status": "Recording started..."}))
                    record_audio()
                    await websocket.send(json.dumps({"status": "Recording stopped, processing..."}))

                    print("Transcribing...")
                    transcript = await transcribe(RECORDING_PATH)
                    print(f"Finished transcribing: {transcript}")

                    if not transcript:
                        response = "Sorry, I couldn't understand what you said."
                    else:
                        print("Generating response...")
                        response = request_gpt(transcript)
                        print(f"Finished generating response: {response}")

                    is_speaking = True
                    await websocket.send(json.dumps({"status": "Speaking..."}))  # Notify client that AI is speaking

                    print("Generating audio...")
                    tts = gTTS(text=response, lang='en')
                    tts.save(RESPONSE_AUDIO_PATH)
                    print("Finished generating audio.")

                    with open(RESPONSE_AUDIO_PATH, "rb") as audio_file:
                        audio_data = audio_file.read()
                    audio_base64 = base64.b64encode(audio_data).decode("utf-8")

                    response_data = {
                        "transcription": transcript,
                        "response": response,
                        "audio_base64": audio_base64
                    }
                    await websocket.send(json.dumps(response_data))
                    print("Sent audio data to client.")

                    is_speaking = False
                    await websocket.send(json.dumps({"status": "Finished speaking"}))  # Notify client that AI finished speaking

                    print(f"\n --- USER: {transcript}\n --- Gracie: {response}\n")
            elif isinstance(message, bytes):
                with open(RECORDING_PATH, "wb") as f:
                    f.write(message)
                print("Received and saved binary data")

                # Process the saved audio data
                print("Transcribing...")
                transcript = await transcribe(RECORDING_PATH)
                print(f"Finished transcribing: {transcript}")

                if not transcript:
                    response = "Sorry, I couldn't understand what you said."
                else:
                    print("Generating response...")
                    response = request_gpt(transcript)
                    print(f"Finished generating response: {response}")

                is_speaking = True
                await websocket.send(json.dumps({"status": "Speaking..."}))  # Notify client that AI is speaking

                print("Generating audio...")
                tts = gTTS(text=response, lang='en')
                tts.save(RESPONSE_AUDIO_PATH)
                print("Finished generating audio.")

                with open(RESPONSE_AUDIO_PATH, "rb") as audio_file:
                    audio_data = audio_file.read()
                audio_base64 = base64.b64encode(audio_data).decode("utf-8")

                response_data = {
                    "transcription": transcript,
                    "response": response,
                    "audio_base64": audio_base64
                }
                await websocket.send(json.dumps(response_data))
                print("Sent audio data to client.")

                is_speaking = False
                await websocket.send(json.dumps({"status": "Finished speaking"}))  # Notify client that AI finished speaking

                print(f"\n --- USER: {transcript}\n --- Gracie: {response}\n")
            else:
                print("Received non-binary data")
    except websockets.ConnectionClosed as e:
        print(f"Connection closed: {e}")
    except Exception as e:
        print(f"An error occurred: {e}")

def rms(frame):
    count = len(frame) / 2
    if count == 0:
        return 0
    shorts = np.frombuffer(frame, np.int16)
    sum_squares = np.sum(np.square(shorts))
    if count == 0:
        return 0
    return np.sqrt(sum_squares / count)

def record_audio():
    global is_speaking
    if is_speaking:
        return  # Do not start recording if the bot is speaking

    stream = p.open(format=FORMAT, channels=CHANNELS,
                    rate=RATE, input=True,
                    frames_per_buffer=CHUNK)

    print("Recording...")
    frames = []
    silent_chunks = 0
    while True:
        data = stream.read(CHUNK)
        frames.append(data)
        if rms(data) < SILENCE_THRESHOLD:
            silent_chunks += 1
        else:
            silent_chunks = 0
        if silent_chunks > (SILENCE_DURATION * RATE / CHUNK):
            break

    print("Finished recording.")
    stream.stop_stream()
    stream.close()

    with open(RECORDING_PATH, 'wb') as wf:
        wf.write(b''.join(frames))

async def start_websocket_server():
    async with websockets.serve(handle_connection, "0.0.0.0", 8765):
        await asyncio.Future()  # Run forever

if __name__ == "__main__":
    asyncio.run(start_websocket_server())
