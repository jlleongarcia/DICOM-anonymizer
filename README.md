# DICOM Anonymizer Tool

A simple, web-based tool to anonymize DICOM files. Built with Python, Streamlit, and Pydicom, this application provides an easy-to-use interface for removing or replacing sensitive patient information from DICOM file metadata.

## Features

*   **User-Friendly Web Interface:** A simple UI built with Streamlit for easy operation.
*   **Batch Processing:** Anonymize all DICOM files within a specified directory.
*   **Selective Anonymization:** Choose which DICOM tags to anonymize from a predefined list based on DICOM standards.
*   **Safe Output:** Anonymized files are saved to a new `anonymized` subdirectory, leaving original files untouched.
*   **UID Regeneration:** Automatically generates new, unique UIDs for `Study Instance UID`, `Series Instance UID`, `SOP Instance UID`, etc.
*   **Private Tag Removal:** Strips private tags from the files.
*   **Progress Tracking:** A progress bar shows the status of the anonymization process.

## Disclaimer

> **Important:** This tool is intended for educational and research purposes. It anonymizes DICOM metadata tags but **does not remove burned-in annotations** from the pixel data. Always verify that the anonymization meets your specific legal, ethical, and institutional requirements before sharing data.

## Installation

1.  **Clone the repository:**
    ```bash
    git clone https://github.com/jlleongarcia/DICOM-anonymizer.git
    cd DICOM-anonymizer
    ```

2.  **Create a virtual environment (recommended):**
    ```bash
    # For macOS/Linux
    python3 -m venv myvenv
    source myvenv/bin/activate

    # For Windows
    python -m venv myvenv
    myvenv\Scripts\activate
    ```

3.  **Install dependencies:**
    The project comes with a setup script that handles this automatically when you run it. Alternatively, you can install the dependencies manually:
    ```bash
    pip install -r requirements.txt
    ```

## Usage

The easiest way to run the application is by using the provided `exe_anonymizer.py` script. This will first install the required packages and then launch the web application.

```bash
python exe_anonymizer.py
```

By default, the application will run on port `8503`. You can specify a different port as a command-line argument:

```bash
python exe_anonymizer.py 8000
```

Once the application is running, open your web browser and navigate to the URL provided in your terminal (e.g., `http://localhost:8503`).

### How to Use the Interface

1.  **Select Tags:** The application lists DICOM tags recommended for anonymization, grouped by category. By default, all are selected. You can expand the categories and deselect any tags you wish to keep.
2.  **Enter Directory Path:** Provide the full path to the folder containing the DICOM files you want to process (e.g., `C:/Users/YourUser/Desktop/DICOM_data`).
3.  **Anonymize:** Click the "Anonymize Directory" button.
4.  **Done:** The tool will process the files and save the anonymized versions in a new subfolder named `anonymized` inside your source directory.

## How It Works

The script reads each file in the source directory and performs the following actions on the selected tags:

*   **Removes/Blanks Personal Information:** Tags containing names (`PN`), short text (`SH`, `LO`), long text (`LT`, `ST`), and other descriptive fields are replaced with `"ANONYMIZED"` or blanked.
*   **Replaces Dates and Times:** Date (`DA`) and Time (`TM`) tags are replaced with dummy values (`18000101` and `000000`).
*   **Generates New UIDs:** Unique Identifier (`UI`) tags are replaced with newly generated UIDs to break links between studies, series, and instances.
*   **Removes Private Tags:** All private tags are removed to prevent potential data leakage.

The anonymization logic is based on the recommendations in **DICOM Standard PS3.15, Annex E**.

## Dependencies

*   Streamlit: For the web application interface.
*   Pydicom: For reading, modifying, and writing DICOM files.
