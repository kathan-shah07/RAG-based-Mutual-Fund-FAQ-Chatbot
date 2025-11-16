"""
Script to start the FastAPI server and open the browser to the frontend.
Logs all API calls and errors to the terminal in real-time.
"""
import subprocess
import time
import webbrowser
import sys
import os
import threading
import queue
import uvicorn
import config

def check_server_ready(url="http://localhost:8000/health", max_attempts=30):
    """Check if the server is ready by making a health check request."""
    import urllib.request
    import urllib.error
    
    for attempt in range(max_attempts):
        try:
            response = urllib.request.urlopen(url, timeout=2)
            if response.getcode() == 200:
                return True
        except (urllib.error.URLError, OSError):
            pass
        time.sleep(0.5)
    return False


def read_output(pipe, output_queue, stream_name):
    """Read output from a pipe and put it in a queue."""
    try:
        for line in iter(pipe.readline, ''):
            if line:
                output_queue.put((stream_name, line))
        pipe.close()
    except Exception as e:
        output_queue.put((stream_name, f"Error reading {stream_name}: {e}\n"))


def print_output(output_queue, stop_event):
    """Print output from the queue to the terminal."""
    while not stop_event.is_set() or not output_queue.empty():
        try:
            stream_name, line = output_queue.get(timeout=0.1)
            # Print with appropriate stream prefix
            if stream_name == 'stderr':
                print(f"[ERROR] {line.rstrip()}", file=sys.stderr)
            else:
                print(f"[LOG] {line.rstrip()}")
            output_queue.task_done()
        except queue.Empty:
            continue
        except Exception as e:
            print(f"Error printing output: {e}", file=sys.stderr)


def main():
    """Start the server and open the browser."""
    print("=" * 70)
    print("Starting FastAPI server with logging...")
    print("=" * 70)
    print(f"Server will be available at http://localhost:{config.API_PORT}")
    print("Press Ctrl+C to stop the server\n")
    
    # Start the server in a subprocess with logging enabled
    server_process = None
    output_queue = queue.Queue()
    stop_event = threading.Event()
    
    try:
        # Start uvicorn server with logging to terminal
        # Use --log-level info to see API calls and requests
        server_process = subprocess.Popen(
            [sys.executable, "-m", "uvicorn", "api.main:app", 
             "--host", config.API_HOST, 
             "--port", str(config.API_PORT),
             "--log-level", "info"],  # Show info level logs (includes API calls)
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,  # Merge stderr into stdout for unified logging
            text=True,
            bufsize=1,  # Line buffered
            universal_newlines=True
        )
        
        # Start thread to read and display output
        output_thread = threading.Thread(
            target=print_output,
            args=(output_queue, stop_event),
            daemon=True
        )
        output_thread.start()
        
        # Start thread to read stdout
        stdout_thread = threading.Thread(
            target=read_output,
            args=(server_process.stdout, output_queue, 'stdout'),
            daemon=True
        )
        stdout_thread.start()
        
        # Wait for server to be ready
        print("\n[INFO] Waiting for server to start...")
        if check_server_ready():
            print("\n" + "=" * 70)
            print("✓ Server is ready!")
            print("=" * 70)
            print(f"\n[INFO] Opening browser to http://localhost:{config.API_PORT}")
            webbrowser.open(f"http://localhost:{config.API_PORT}")
            print("\n[INFO] Server is running. All API calls and errors will be logged below.")
            print("[INFO] Press Ctrl+C to stop the server.\n")
            print("-" * 70)
            
            # Wait for the server process while logs are being displayed
            try:
                server_process.wait()
            except KeyboardInterrupt:
                print("\n\n[INFO] Stopping server...")
                stop_event.set()
                server_process.terminate()
                server_process.wait()
                print("[INFO] Server stopped.")
        else:
            print("\n[ERROR] Server failed to start within expected time.")
            stop_event.set()
            if server_process:
                server_process.terminate()
                server_process.wait()
            sys.exit(1)
            
    except KeyboardInterrupt:
        print("\n\n[INFO] Stopping server...")
        stop_event.set()
        if server_process:
            server_process.terminate()
            server_process.wait()
        print("[INFO] Server stopped.")
    except Exception as e:
        print(f"\n[ERROR] Error: {e}", file=sys.stderr)
        stop_event.set()
        if server_process:
            server_process.terminate()
            server_process.wait()
        sys.exit(1)
    finally:
        stop_event.set()

if __name__ == "__main__":
    main()

