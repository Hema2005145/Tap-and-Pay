import subprocess
import time
import sys
import os

def main():
    print("Starting Federated Learning Simulation...")
    
    python_exe = os.path.join(".venv", "Scripts", "python.exe")
    server_script = os.path.join("server", "server_fl.py")
    client_script = os.path.join("client", "client_fl.py")
    
    # Start Server
    print("Launching Aggregation Server...")
    server_process = subprocess.Popen([python_exe, server_script])
    time.sleep(4)  # Wait for server to bind to port
    
    # Start Client 1
    print("Launching Edge Device 1...")
    client1 = subprocess.Popen([python_exe, client_script])
    time.sleep(1)
    
    # Start Client 2
    print("Launching Edge Device 2...")
    client2 = subprocess.Popen([python_exe, client_script])
    
    # Wait for clients to finish (3 rounds)
    client1.wait()
    client2.wait()
    print("Edge devices have finished training and disconnected.")
    
    # Kill server
    server_process.terminate()
    print("Federated Learning Simulation Complete!")

if __name__ == "__main__":
    main()
