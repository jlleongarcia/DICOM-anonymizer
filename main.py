import subprocess
import sys


def run_anonymizer(port):
    """Run the Streamlit app."""
    print("Starting the Streamlit app...")
    try:
        command = [
            sys.executable, "-m", "streamlit", "run", "anonymize_dicom.py",
            "--server.port", str(port)
        ]
        subprocess.check_call(command)
    except subprocess.CalledProcessError as e:
        print(f"Error running Streamlit app: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("Starting setup script...")

    # Define a default port and check for a command-line argument
    port_number = 8504
    if len(sys.argv) > 1:
        try:
            port_number = int(sys.argv[1])
        except ValueError:
            print(f"Invalid port number '{sys.argv[1]}'. Using default port {port_number}.")

    # Run the anonymizer script
    run_anonymizer(port=port_number)
