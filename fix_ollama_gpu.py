
import os
import subprocess

def fix_ollama():
    config_path = "/etc/systemd/system/ollama.service.d/override.conf"
    new_content = """[Service]
Environment="LD_LIBRARY_PATH=/usr/lib/x86_64-linux-gnu:/lib/x86_64-linux-gnu:/usr/local/cuda/lib64"
Environment="PATH=/usr/local/cuda/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin"
Environment="OLLAMA_HOST=0.0.0.0:11434"
Environment="CUDA_VISIBLE_DEVICES=0"
Environment="OLLAMA_DEBUG=1"
Environment="OLLAMA_CUDA_PATH=/usr/local/cuda"
Environment="OLLAMA_LLM_LIBRARY=cuda"
Environment="NVIDIA_VISIBLE_DEVICES=all"
Environment="NVIDIA_DRIVER_CAPABILITIES=compute,utility"
"""
    
    print(f"Updating {config_path}...")
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(config_path), exist_ok=True)
        
        # Write the file
        with open(config_path, "w") as f:
            f.write(new_content)
        
        print("Reloading systemd daemon...")
        subprocess.run(["systemctl", "daemon-reload"], check=True)
        
        print("Restarting Ollama service...")
        subprocess.run(["systemctl", "restart", "ollama"], check=True)
        
        print("\nSUCCESS: Ollama has been updated with more aggressive paths and restarted.")
        print("Please run a query in the application now.")
        
    except PermissionError:
        print("\nERROR: Permission denied. Please run this script with sudo:")
        print("sudo python3 fix_ollama_gpu.py")
    except Exception as e:
        print(f"\nAn error occurred: {e}")

if __name__ == "__main__":
    fix_ollama()
