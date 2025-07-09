import logging
import os

import pydicom
import streamlit as st
from pydicom.uid import generate_uid

# Setup basic logging to console
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(levelname)s - %(message)s"
)

# A list of tags to anonymize, based on DICOM PS3.15, Annex E.
TAGS_TO_ANONYMIZE_BY_GROUP = {
    "Patient Information": [
        (0x0010, 0x0010),  # Patient's Name
        (0x0010, 0x0020),  # Patient ID
        (0x0010, 0x0021),  # Issuer of Patient ID
        (0x0010, 0x0030),  # Patient's Birth Date
        (0x0010, 0x0032),  # Patient's Birth Time
        (0x0010, 0x0040),  # Patient's Sex
        (0x0010, 0x1000),  # Other Patient IDs
        (0x0010, 0x1001),  # Other Patient Names
        (0x0010, 0x1002),  # Other Patient IDs Sequence
        (0x0010, 0x1010),  # Patient's Age
        (0x0010, 0x1020),  # Patient's Size
        (0x0010, 0x1030),  # Patient's Weight
        (0x0010, 0x1040),  # Patient's Address
        (0x0010, 0x2160),  # Ethnic Group
        (0x0010, 0x2180),  # Occupation
        (0x0010, 0x21B0),  # Additional Patient History
        (0x0010, 0x4000),  # Patient Comments
    ],
    "Physician Information": [
        (0x0008, 0x0080),  # Institution Name
        (0x0008, 0x0081),  # Institution Address
        (0x0008, 0x0090),  # Referring Physician's Name
        (0x0008, 0x0092),  # Referring Physician's Address
        (0x0008, 0x0094),  # Referring Physician's Telephone Numbers
        (0x0008, 0x1050),  # Performing Physician's Name
        (0x0008, 0x1070),  # Operators' Name
    ],
    "Study Information": [
        (0x0008, 0x1030),  # Study Description
        (0x0008, 0x0050),  # Accession Number
        (0x0032, 0x1032),  # Requesting Physician
    ],
    "Equipment Information": [(0x0008, 0x1010)],  # Station Name
    "UIDs": [
        (0x0020, 0x000D),  # Study Instance UID
        (0x0020, 0x000E),  # Series Instance UID
        (0x0008, 0x0018),  # SOP Instance UID
        (0x0020, 0x0052),  # Frame of Reference UID
    ],
}

# A flattened list of all tags for easier processing
ALL_TAGS_TO_ANONYMIZE = [
    tag for group_tags in TAGS_TO_ANONYMIZE_BY_GROUP.values() for tag in group_tags
]


def anonymize_dicom_file(input_path, output_path, tags_to_anonymize):
    """
    Anonymizes a single DICOM file by removing or replacing specific tags.
    Returns True on success, False on failure.
    """
    try:
        ds = pydicom.dcmread(input_path)
    except pydicom.errors.InvalidDicomError:
        logging.warning(f"Skipping non-DICOM file: {input_path}")
        return False

    # Anonymize specific tags
    for group, element in tags_to_anonymize:
        tag = (group, element)
        if tag in ds:
            vr = ds[tag].VR
            if vr == "UI":
                ds[tag].value = generate_uid()
            elif vr in ["PN", "SH", "LO", "ST", "LT"]:
                ds[tag].value = "ANONYMIZED"
            elif vr == "DA":
                ds[tag].value = "18000101"
            elif vr == "TM":
                ds[tag].value = "000000"
            elif vr in ["DS", "IS"]:
                ds[tag].value = "0"
            else:
                try:
                    ds[tag].value = ""
                except TypeError:
                    logging.warning(f"Could not blank tag {tag}, removing it.")
                    del ds[tag]

    # Remove private tags
    ds.remove_private_tags()

    # Update file meta information with the new SOP Instance UID
    if (0x0002, 0x0003) in ds.file_meta:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    # Ensure the output directory exists
    output_dir = os.path.dirname(output_path)
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # Save the anonymized file
    ds.save_as(output_path)
    logging.info(f"Anonymized '{input_path}' -> '{output_path}'")
    return True


# --- Streamlit App ---

st.set_page_config(page_title="DICOM Anonymizer", layout="centered")

st.title("DICOM Anonymizer Tool")

st.info(
    "**Disclaimer:** This tool is for educational and research purposes. "
    "It does not remove burned-in annotations from pixel data. "
    "Always verify anonymization meets your legal and ethical requirements."
)

st.header("Anonymization Options")
st.write("Select the DICOM tags you want to anonymize:")

# Create a mapping from tag tuple to a descriptive string for display
TAG_DESCRIPTIONS = {
    tag: f"({tag[0]:04X}, {tag[1]:04X}) - {pydicom.datadict.dictionary_description(tag) or 'Unknown Tag'}"
    for tag in ALL_TAGS_TO_ANONYMIZE
}

# Initialize session state for each tag's checkbox if not already present.
# This ensures that selections are preserved across reruns.
for tag in ALL_TAGS_TO_ANONYMIZE:
    if f"tag_{tag}" not in st.session_state:
        st.session_state[f"tag_{tag}"] = True  # Default to selected


# Callback to update all tags when "Select All" is clicked
def select_all_callback():
    select_all_state = st.session_state.select_all_checkbox
    for tag in ALL_TAGS_TO_ANONYMIZE:
        st.session_state[f"tag_{tag}"] = select_all_state


# Determine the current state of the "Select All" checkbox
all_selected = all(st.session_state[f"tag_{tag}"] for tag in ALL_TAGS_TO_ANONYMIZE)

st.checkbox(
    "Select/Deselect All",
    value=all_selected,
    key="select_all_checkbox",
    on_change=select_all_callback,
)

st.markdown("---")

# Display checkboxes for each tag, grouped by category
selected_tags = []
for group_name, group_tags in TAGS_TO_ANONYMIZE_BY_GROUP.items():
    with st.expander(group_name, expanded=False):
        cols = st.columns(2)
        for i, tag in enumerate(group_tags):
            with cols[i % 2]:
                is_checked = st.checkbox(TAG_DESCRIPTIONS[tag], key=f"tag_{tag}")
                if is_checked:
                    selected_tags.append(tag)


input_dir = st.text_input(
    "Enter the full path to the directory containing DICOM files:",
    placeholder="e.g., C:/Users/YourUser/Desktop/DICOM_data",
)

if st.button("Anonymize Directory"):
    if not selected_tags:
        st.warning("Please select at least one tag to anonymize.")
    elif input_dir and os.path.isdir(input_dir):
        output_dir = os.path.join(input_dir, "anonymized")

        with st.spinner(f"Scanning directory: {input_dir}..."):
            files_to_process = []
            for root, _, files in os.walk(input_dir):
                # Important: Skip the output directory to prevent re-processing
                if root.startswith(output_dir):
                    continue
                for filename in files:
                    files_to_process.append(os.path.join(root, filename))

        if not files_to_process:
            st.warning("No files found in the specified directory.")
        else:
            st.success(f"Found {len(files_to_process)} files. Starting anonymization...")

            progress_bar = st.progress(0)
            status_text = st.empty()
            anonymized_count = 0

            for i, file_path in enumerate(files_to_process):
                relative_path = os.path.relpath(file_path, input_dir)
                output_file_path = os.path.join(output_dir, relative_path)

                if anonymize_dicom_file(file_path, output_file_path, selected_tags):
                    anonymized_count += 1

                # Update progress bar
                progress = (i + 1) / len(files_to_process)
                progress_bar.progress(progress)
                status_text.text(
                    f"Processing file {i + 1}/{len(files_to_process)}: {os.path.basename(file_path)}"
                )

            status_text.empty()
            progress_bar.empty()
            st.success(
                f"Anonymization complete! {anonymized_count} DICOM files were processed and saved to:"
            )
            st.code(output_dir, language=None)
    else:
        st.error("The provided path is not a valid directory. Please check the path and try again.")