import io
import logging
import os
import zipfile

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

# Common tags exposed as ready-to-edit fields in the "Modify Tags" tab.
CURATED_EDITABLE_TAGS = [
    "PatientName",
    "PatientID",
    "PatientBirthDate",
    "PatientSex",
    "PatientAge",
    "AccessionNumber",
    "StudyID",
    "StudyDate",
    "StudyDescription",
    "SeriesDescription",
    "InstitutionName",
    "ReferringPhysicianName",
]

# VRs whose values should be coerced to numbers before assignment.
_INT_VRS = {"US", "SS", "UL", "SL"}
_FLOAT_VRS = {"FL", "FD"}


def anonymize_dicom_bytes(data, name, tags_to_anonymize):
    """
    Anonymizes a single DICOM file by removing or replacing specific tags.
    Returns the anonymized file as bytes, or None if it is not a DICOM file.
    """
    try:
        ds = pydicom.dcmread(io.BytesIO(data))
    except pydicom.errors.InvalidDicomError:
        logging.warning(f"Skipping non-DICOM file: {name}")
        return None

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
    if (0x0002, 0x0003) in ds.file_meta and "SOPInstanceUID" in ds:
        ds.file_meta.MediaStorageSOPInstanceUID = ds.SOPInstanceUID

    # Save the anonymized file to memory; nothing is written to disk
    buffer = io.BytesIO()
    ds.save_as(buffer)
    logging.info(f"Anonymized '{name}'")
    return buffer.getvalue()


def collect_uploaded_files(uploaded_files):
    """
    Expand the uploaded files into ``(relative_path, bytes)`` pairs.

    ZIP archives are unpacked so that their folder structure is preserved in
    the output; any other upload is taken as a single file.
    """
    collected = []
    for uploaded in uploaded_files:
        if uploaded.name.lower().endswith(".zip"):
            try:
                with zipfile.ZipFile(io.BytesIO(uploaded.getvalue())) as archive:
                    for info in archive.infolist():
                        if not info.is_dir():
                            collected.append((info.filename, archive.read(info)))
            except zipfile.BadZipFile:
                st.error(f"{uploaded.name}: not a valid ZIP archive - skipped.")
        else:
            collected.append((uploaded.name, uploaded.getvalue()))
    return collected


# --- Tag-modification helpers ---


def parse_tag_input(text):
    """
    Parse a user-supplied tag reference into a pydicom Tag.

    Accepts a DICOM keyword (e.g. ``PatientName``) or a numeric form such as
    ``0010,0010``, ``(0010,0010)``, ``0010 0010`` or ``00100010``.
    Returns None for empty input and raises ValueError for anything unparseable.
    """
    text = (text or "").strip()
    if not text:
        return None

    tag_int = pydicom.datadict.tag_for_keyword(text)
    if tag_int is not None:
        return pydicom.tag.Tag(tag_int)

    cleaned = text.lstrip("(").rstrip(")").strip().replace(" ", "")
    for sep in (",", "|", ";"):
        if sep in cleaned:
            group, element = cleaned.split(sep, 1)
            try:
                return pydicom.tag.Tag(int(group, 16), int(element, 16))
            except ValueError:
                break
    if len(cleaned) == 8:
        try:
            return pydicom.tag.Tag(int(cleaned[:4], 16), int(cleaned[4:], 16))
        except ValueError:
            pass

    raise ValueError(f"Could not parse tag: {text!r}")


def _coerce_value(vr, raw):
    """Convert a string value to the type expected for the given VR."""
    raw = "" if raw is None else str(raw)
    is_multivalue = "\\" in raw and vr not in {"LT", "ST", "UT"}
    parts = raw.split("\\") if is_multivalue else [raw]

    def convert(part):
        part = part.strip()
        if vr in _INT_VRS:
            try:
                return int(part)
            except ValueError:
                return part
        if vr in _FLOAT_VRS:
            try:
                return float(part)
            except ValueError:
                return part
        return part

    converted = [convert(p) for p in parts]
    return converted if is_multivalue else converted[0]


def apply_modifications(ds, modifications):
    """
    Apply ``(Tag, new_value)`` pairs to a dataset in place.

    Returns a list of ``(tag, vr, status, error)`` where status is one of
    ``"updated"``, ``"added"`` or ``"error"``.
    """
    results = []
    for tag, value in modifications:
        try:
            if tag in ds:
                elem = ds[tag]
                elem.value = _coerce_value(elem.VR, value)
                results.append((tag, elem.VR, "updated", None))
            else:
                try:
                    vr = pydicom.datadict.dictionary_VR(tag)
                except KeyError:
                    results.append(
                        (tag, None, "error", "Unknown tag - cannot infer VR")
                    )
                    continue
                ds.add_new(tag, vr, _coerce_value(vr, value))
                results.append((tag, vr, "added", None))
        except Exception as exc:  # noqa: BLE001 - surface any pydicom error to the UI
            results.append((tag, None, "error", str(exc)))
    return results


def _modified_filename(name, suffix="modified"):
    root, ext = os.path.splitext(name)
    return f"{root}_{suffix}{ext or '.dcm'}"


def _tag_label(tag):
    desc = pydicom.datadict.dictionary_description(tag) or "Unknown Tag"
    return f"({tag.group:04X},{tag.element:04X}) {desc}"


# --- Streamlit App ---

st.set_page_config(page_title="DICOM Anonymizer", layout="centered")

st.title("DICOM Anonymizer Tool")

st.info(
    "**Disclaimer:** This tool is for educational and research purposes. "
    "It does not remove burned-in annotations from pixel data. "
    "Always verify anonymization meets your legal and ethical requirements."
)


def render_anonymize_tab():
    st.header("Anonymization Options")
    st.write("Select the DICOM tags you want to anonymize:")

    # Create a mapping from tag tuple to a descriptive string for display
    tag_descriptions = {
        tag: f"({tag[0]:04X}, {tag[1]:04X}) - "
        f"{pydicom.datadict.dictionary_description(tag) or 'Unknown Tag'}"
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
    all_selected = all(
        st.session_state[f"tag_{tag}"] for tag in ALL_TAGS_TO_ANONYMIZE
    )

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
                    is_checked = st.checkbox(
                        tag_descriptions[tag], key=f"tag_{tag}"
                    )
                    if is_checked:
                        selected_tags.append(tag)

    st.markdown("---")

    upload_mode = st.radio(
        "What do you want to upload?",
        ["Folder", "Files or ZIP archive"],
        horizontal=True,
        key="anonymize_upload_mode",
    )

    # No type filter: DICOM files often have no extension. Non-DICOM files are
    # skipped during processing. Folder uploads name each file by its path
    # relative to the folder, so folders and ZIPs both keep their structure.
    if upload_mode == "Folder":
        uploaded_files = st.file_uploader(
            "Upload a folder containing DICOM files (subfolders included)",
            accept_multiple_files="directory",
            key="anonymize_folder_uploader",
        )
    else:
        uploaded_files = st.file_uploader(
            "Upload DICOM files, or a ZIP archive containing them",
            accept_multiple_files=True,
            key="anonymize_uploader",
        )

    if st.button("Anonymize files", key="anonymize_btn"):
        if not selected_tags:
            st.warning("Please select at least one tag to anonymize.")
            return
        if not uploaded_files:
            st.warning("Please upload a folder, DICOM files or a ZIP archive.")
            return

        files_to_process = collect_uploaded_files(uploaded_files)
        if not files_to_process:
            st.warning("No files found in the upload.")
            return

        progress_bar = st.progress(0)
        status_text = st.empty()
        anonymized_files = []
        skipped = []

        for i, (path, data) in enumerate(files_to_process):
            anonymized = anonymize_dicom_bytes(data, path, selected_tags)
            if anonymized is None:
                skipped.append(path)
            else:
                anonymized_files.append((path, anonymized))

            # Update progress bar
            progress_bar.progress((i + 1) / len(files_to_process))
            status_text.text(
                f"Processing file {i + 1}/{len(files_to_process)}: "
                f"{os.path.basename(path)}"
            )

        status_text.empty()
        progress_bar.empty()

        st.session_state["anonymize_output"] = {
            "files": anonymized_files,
            "skipped": skipped,
        }

    output = st.session_state.get("anonymize_output")
    if not output:
        return

    st.markdown("---")
    if output["skipped"]:
        with st.expander(
            f"{len(output['skipped'])} non-DICOM file(s) skipped", expanded=False
        ):
            for path in output["skipped"]:
                st.write(path)

    if not output["files"]:
        st.warning("None of the uploaded files were valid DICOM files.")
        return

    st.success(f"Anonymization complete! {len(output['files'])} DICOM file(s) processed.")

    if len(output["files"]) == 1:
        path, data = output["files"][0]
        st.download_button(
            "Download anonymized file",
            data=data,
            file_name=_modified_filename(os.path.basename(path), "anonymized"),
            mime="application/dicom",
            key="anonymize_dl_single",
        )
    else:
        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for path, data in output["files"]:
                archive.writestr(path, data)
        st.download_button(
            "Download all as ZIP",
            data=zip_buffer.getvalue(),
            file_name="anonymized_dicom.zip",
            mime="application/zip",
            key="anonymize_dl_zip",
        )


def render_modify_tab():
    st.header("Modify DICOM Tags")
    st.write(
        "Upload one or more `.dcm` files, set new values for the tags you want "
        "to change, then download the modified files. Original files are never "
        "touched and nothing is written to disk."
    )

    uploaded_files = st.file_uploader(
        "Upload DICOM files",
        type=["dcm"],
        accept_multiple_files=True,
        key="modify_uploader",
    )

    st.subheader("Common tags")
    st.caption("Leave a field blank to keep its current value unchanged.")
    curated_values = {}
    cols = st.columns(2)
    for i, keyword in enumerate(CURATED_EDITABLE_TAGS):
        with cols[i % 2]:
            curated_values[keyword] = st.text_input(keyword, key=f"mod_{keyword}")

    st.subheader("Other tags")
    st.caption(
        "Add any tag by keyword (e.g. `PatientName`) or number "
        "(e.g. `0010,0010`). Use `\\` to separate multiple values."
    )
    extra_rows = st.data_editor(
        [{"Tag": "", "New value": ""}],
        num_rows="dynamic",
        width="stretch",
        key="modify_extra_editor",
        column_config={
            "Tag": st.column_config.TextColumn("Tag", help="Keyword or group,element"),
            "New value": st.column_config.TextColumn("New value"),
        },
    )

    if st.button("Apply modifications", key="apply_modifications_btn"):
        if not uploaded_files:
            st.warning("Please upload at least one DICOM file.")
            return

        modifications = []
        parse_errors = []

        for keyword, raw_value in curated_values.items():
            if raw_value.strip():
                tag = pydicom.tag.Tag(pydicom.datadict.tag_for_keyword(keyword))
                modifications.append((tag, raw_value))

        for row in extra_rows:
            raw_tag = (row.get("Tag") or "").strip()
            if not raw_tag:
                continue
            try:
                tag = parse_tag_input(raw_tag)
            except ValueError as exc:
                parse_errors.append(str(exc))
                continue
            modifications.append((tag, row.get("New value")))

        for message in parse_errors:
            st.error(message)

        if not modifications:
            st.warning("No modifications specified.")
            return

        modified_files = []
        reports = []
        for uploaded in uploaded_files:
            try:
                ds = pydicom.dcmread(io.BytesIO(uploaded.getvalue()))
            except pydicom.errors.InvalidDicomError:
                st.error(f"{uploaded.name}: not a valid DICOM file - skipped.")
                continue

            results = apply_modifications(ds, modifications)

            buffer = io.BytesIO()
            ds.save_as(buffer, enforce_file_format=True)
            modified_files.append((uploaded.name, buffer.getvalue()))
            reports.append((uploaded.name, results))

        st.session_state["modify_output"] = {
            "files": modified_files,
            "reports": reports,
        }

    output = st.session_state.get("modify_output")
    if not output or not output["files"]:
        return

    st.markdown("---")
    st.success(f"Modified {len(output['files'])} file(s).")

    for name, results in output["reports"]:
        with st.expander(f"{name} - {len(results)} change(s)", expanded=False):
            for tag, vr, status, error in results:
                if status == "error":
                    st.write(f"❌ {_tag_label(tag)}: {error}")
                else:
                    st.write(f"✅ {_tag_label(tag)} [{vr}]: {status}")

    if len(output["files"]) == 1:
        name, data = output["files"][0]
        st.download_button(
            "Download modified file",
            data=data,
            file_name=_modified_filename(name),
            mime="application/dicom",
            key="modify_dl_single",
        )
    else:
        for index, (name, data) in enumerate(output["files"]):
            st.download_button(
                f"Download {name}",
                data=data,
                file_name=_modified_filename(name),
                mime="application/dicom",
                key=f"modify_dl_{index}",
            )

        zip_buffer = io.BytesIO()
        with zipfile.ZipFile(zip_buffer, "w", zipfile.ZIP_DEFLATED) as archive:
            for name, data in output["files"]:
                archive.writestr(_modified_filename(name), data)
        st.download_button(
            "Download all as ZIP",
            data=zip_buffer.getvalue(),
            file_name="modified_dicom.zip",
            mime="application/zip",
            key="modify_dl_zip",
        )


anonymize_tab, modify_tab = st.tabs(["Anonymize Files", "Modify Tags"])

with anonymize_tab:
    render_anonymize_tab()

with modify_tab:
    render_modify_tab()
