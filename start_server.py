import subprocess

def start_server():
    # Start the WebSocket server
    server_process = subprocess.Popen(['python', 'AI.py'])
    return server_process

if __name__ == "__main__":
    server_process = start_server()
    print(f"Server started with PID {server_process.pid}")
