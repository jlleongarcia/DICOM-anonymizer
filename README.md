# DICOM Anonymizer Tool

A simple, web-based tool to anonymize DICOM files. Built with Python, Streamlit, and Pydicom, this application provides an easy-to-use interface for removing or replacing sensitive patient information from DICOM file metadata.

## Features

*   **User-Friendly Web Interface:** A simple UI built with Streamlit for easy operation.
*   **Batch Processing:** Anonymize all DICOM files within a specified directory.
*   **Selective Anonymization:** Choose which DICOM tags to anonymize from a predefined list based on DICOM standards.
*   **Tag Editing (Upload):** A second tab lets you upload `.dcm` files, set new values for common tags (or any tag by keyword/number), and download the modified files individually or as a ZIP. Nothing is written to disk.
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

2.  **Create a virtual environment and install dependencies:****
    
    Having uv installed in your PC:

    ```bash
    uv run main.py
    ```

Once the application is running, open your web browser and navigate to the URL provided in your terminal (e.g., `http://localhost:8504`).

### How to Use the Interface

The app has two tabs.

#### Anonymize Directory

1.  **Select Tags:** The application lists DICOM tags recommended for anonymization, grouped by category. By default, all are selected. You can expand the categories and deselect any tags you wish to keep.
2.  **Enter Directory Path:** Provide the full path to the folder containing the DICOM files you want to process (e.g., `C:/Users/YourUser/Desktop/DICOM_data`).
3.  **Anonymize:** Click the "Anonymize Directory" button.
4.  **Done:** The tool will process the files and save the anonymized versions in a new subfolder named `anonymized` inside your source directory.

#### Modify Tags (Upload)

1.  **Upload Files:** Drag and drop one or more `.dcm` files into the uploader.
2.  **Set Values:** Fill in new values for the common tags shown, and/or add rows in the "Other tags" table for any tag by keyword (e.g. `PatientName`) or number (e.g. `0010,0010`). Blank common-tag fields are left unchanged; use `\` to separate multiple values.
3.  **Apply:** Click "Apply modifications". A per-file report shows which tags were updated or added.
4.  **Download:** Download each modified file (named `<name>_modified.dcm`) individually, or grab them all as a single ZIP. Uploaded originals are never modified and nothing is written to disk.

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
