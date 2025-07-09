import subprocess
import sys


def install_packages():
    """Install packages from requirements.txt."""
    print("Checking and installing required packages...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", "-r", "requirements.txt"])
        print("Packages installed successfully.")
    except subprocess.CalledProcessError as e:
        print(f"Error installing packages: {e}")
        sys.exit(1)

def run_anonymizer():
    """Run the Streamlit app."""
    print("Starting the Streamlit app...")
    try:
        subprocess.check_call([sys.executable, "-m", "streamlit", "run", "anonymize_dicom.py"])
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting setup script...")

    # Install dependencies
    install_packages()

    # Run the anonymizer script
    run_anonymizer()