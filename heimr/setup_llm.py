#!/usr/bin/env python3
"""
Heimr LLM Setup Script
Ensures Ollama and Llama 3.1 are installed and ready.
"""

import sys
import subprocess
import platform
import requests


def check_ollama_installed():
    """Check if Ollama is installed."""
    try:
        result = subprocess.run(
            ["ollama", "--version"],
            capture_output=True,
            text=True,
            timeout=5
        )
        return result.returncode == 0
    except (FileNotFoundError, subprocess.TimeoutExpired):
        return False


def check_ollama_running():
    """Check if Ollama service is running."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=2)
        return response.status_code == 200
    except requests.exceptions.RequestException:
        return False


def check_model_available(model_name="llama3.1:8b"):
    """Check if the specified model is available."""
    try:
        response = requests.get("http://localhost:11434/api/tags", timeout=5)
        if response.status_code == 200:
            models = response.json().get("models", [])
            return any(model_name in m.get("name", "") for m in models)
    except requests.exceptions.RequestException:
        pass
    return False


def install_ollama():
    """Install Ollama based on the operating system."""
    system = platform.system()

    print("📦 Installing Ollama...")

    if system == "Linux":
        # Linux installation
        try:
            subprocess.run(
                ["curl", "-fsSL", "https://ollama.com/install.sh"],
                stdout=subprocess.PIPE,
                check=True
            )
            subprocess.run(
                ["sh"],
                input=subprocess.run(
                    ["curl", "-fsSL", "https://ollama.com/install.sh"],
                    capture_output=True,
                    check=True
                ).stdout,
                check=True
            )
            print("✅ Ollama installed successfully!")
            return True
        except subprocess.CalledProcessError as e:
            print(f"❌ Failed to install Ollama: {e}")
            return False

    elif system == "Darwin":  # macOS
        print("Please install Ollama manually:")
        print("  brew install ollama")
        print("  OR download from: https://ollama.com/download/mac")
        return False

    elif system == "Windows":
        print("Please install Ollama manually:")
        print("  Download from: https://ollama.com/download/windows")
        return False

    else:
        print(f"❌ Unsupported operating system: {system}")
        return False


def start_ollama_service():
    """Start Ollama service."""
    system = platform.system()

    print("🚀 Starting Ollama service...")

    try:
        if system == "Linux":
            # Try systemd first
            subprocess.run(["systemctl", "start", "ollama"], check=False)

        # Start in background for all systems
        subprocess.Popen(
            ["ollama", "serve"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            start_new_session=True
        )

        # Wait a bit for service to start
        import time
        time.sleep(3)

        if check_ollama_running():
            print("✅ Ollama service started!")
            return True
        else:
            print("⚠️  Ollama service may not have started. Try running: ollama serve")
            return False

    except Exception as e:
        print(f"⚠️  Could not start Ollama automatically: {e}")
        print("Please start Ollama manually: ollama serve")
        return False


def pull_model(model_name="llama3.1:8b"):
    """Pull the specified Llama model."""
    print(f"📥 Pulling {model_name} model (this may take a few minutes)...")

    try:
        process = subprocess.Popen(
            ["ollama", "pull", model_name],
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1
        )

        # Stream output
        for line in process.stdout:
            print(f"  {line.strip()}")

        process.wait()

        if process.returncode == 0:
            print(f"✅ {model_name} model ready!")
            return True
        else:
            print(f"❌ Failed to pull {model_name}")
            return False

    except Exception as e:
        print(f"❌ Error pulling model: {e}")
        return False


def setup_llm(interactive=True):
    """
    Main setup function.
    Returns True if LLM is ready, False otherwise.
    """
    print("\n" + "=" * 60)
    print("🏠 Heimr.ai - LLM Setup")
    print("=" * 60 + "\n")

    # Step 1: Check if Ollama is installed
    if check_ollama_installed():
        print("✅ Ollama is installed")
    else:
        print("❌ Ollama is not installed")

        if interactive:
            response = input("\nWould you like to install Ollama now? (y/n): ")
            if response.lower() != 'y':
                print("\n⚠️  Heimr requires Ollama for AI analysis.")
                print("Install manually: https://ollama.com/download")
                return False

        if not install_ollama():
            print("\n⚠️  Please install Ollama manually and run: heimr setup-llm")
            return False

    # Step 2: Check if Ollama is running
    if check_ollama_running():
        print("✅ Ollama service is running")
    else:
        print("❌ Ollama service is not running")

        if not start_ollama_service():
            print("\n⚠️  Please start Ollama manually: ollama serve")
            print("Then run: heimr setup-llm")
            return False

    # Step 3: Check if model is available
    model_name = "llama3.1:8b"
    if check_model_available(model_name):
        print(f"✅ {model_name} model is available")
    else:
        print(f"❌ {model_name} model is not available")

        if interactive:
            response = input(f"\nWould you like to download {model_name}? (~4.7GB) (y/n): ")
            if response.lower() != 'y':
                print("\n⚠️  Heimr requires Llama 3.1 for AI analysis.")
                print(f"Download manually: ollama pull {model_name}")
                return False

        if not pull_model(model_name):
            print(f"\n⚠️  Please pull the model manually: ollama pull {model_name}")
            return False

    print("\n" + "=" * 60)
    print("🎉 LLM setup complete! Heimr is ready to use.")
    print("=" * 60 + "\n")

    return True


def main():
    """CLI entry point."""
    import argparse

    parser = argparse.ArgumentParser(
        description="Setup LLM for Heimr.ai"
    )
    parser.add_argument(
        "--non-interactive",
        action="store_true",
        help="Run in non-interactive mode (auto-install everything)"
    )

    args = parser.parse_args()

    success = setup_llm(interactive=not args.non_interactive)
    sys.exit(0 if success else 1)


if __name__ == "__main__":
    main()
