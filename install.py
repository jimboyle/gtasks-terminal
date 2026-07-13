import sys
import subprocess
import shutil

def is_tool_installed(name):
    """Check whether `name` is on PATH."""
    return shutil.which(name) is not None

def install():
    print("📦 Installing gtasks-cli using pipx...")
    
    if not is_tool_installed("pipx"):
        print("❌ Error: 'pipx' is not installed.")
        print("Please install pipx first, it is required for safe isolated installations:")
        print("  - On Fedora: sudo dnf install pipx")
        print("  - On Ubuntu/Debian: sudo apt install pipx")
        print("  - On macOS: brew install pipx")
        print("  - On Windows: python -m pip install --user pipx")
        print("\nAfter installing pipx, you may need to run 'pipx ensurepath' and restart your terminal.")
        sys.exit(1)

    try:
        # pipx install handles python environments and adds the executable to PATH automatically.
        # We can just install the package name.
        subprocess.check_call(["pipx", "install", "gtasks-cli"])
        print("\n✅ SUCCESS: gtasks-cli installed successfully!")
        print("If the 'gtasks' command is not found, run 'pipx ensurepath' and restart your terminal.")
    except subprocess.CalledProcessError as e:
        print(f"❌ Installation failed. Please check the pipx errors above.")
        sys.exit(1)

if __name__ == "__main__":
    install()
