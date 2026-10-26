# DICOM Anonymizer Tool

A simple, web-based tool to anonymize and edit DICOM files. Built with Python, Streamlit, and Pydicom, this application provides an easy-to-use interface for removing or replacing sensitive patient information from DICOM file metadata.

## Features

- **User-friendly web interface** built with Streamlit.
- **Upload-based workflow:** upload DICOM files (or a ZIP archive of folders) from the browser, up to 500 MB per file, and download the results. Nothing is written to disk on the server.
- **Selective anonymization:** choose which DICOM tags to anonymize from a predefined list based on DICOM standards.
- **Folder structure preserved:** when you upload a ZIP archive, the anonymized ZIP keeps the same folders and file names.
- **Tag editing:** a second tab lets you set new values for common tags (or any tag by keyword/number) and download the modified files individually or as a ZIP.
- **UID regeneration:** automatically generates new, unique UIDs for `Study Instance UID`, `Series Instance UID`, `SOP Instance UID`, etc.
- **Private tag removal:** strips private tags from the files.
- **Progress tracking:** a progress bar shows the status of the anonymization process.

## Disclaimer

> **Important:** This tool is intended for educational and research purposes. It anonymizes DICOM metadata tags but **does not remove burned-in annotations** from the pixel data. Always verify that the anonymization meets your specific legal, ethical, and institutional requirements before sharing data.

## Running the app

There are two independent ways to run the app. Both install the same pinned dependency versions.

| | Local with uv | Docker |
|---|---|---|
| Best for | Development, running on a workstation | Deploying on a server |
| Requires | Python ≥ 3.13 and [uv](https://docs.astral.sh/uv/) | [Docker](https://docs.docker.com/get-docker/) with Compose |
| Installs from | `uv.lock` | `requirements.txt` (with pip, no uv) |
| Port | `8504`, configurable | `8504` inside the container, mapped in `docker-compose.yml` |

### Local with uv

1. **Clone the repository:**

   ```bash
   git clone https://github.com/jlleongarcia/DICOM-anonymizer.git
   cd DICOM-anonymizer
   ```

2. **Install dependencies:**

   ```bash
   uv sync
   ```

3. **Run the app:**

   ```bash
   uv run python main.py
   ```

   The app will be accessible at `http://localhost:8504`. You can pass a custom port as an argument:

   ```bash
   uv run python main.py 8080
   ```

### Docker

A multi-architecture image (`linux/amd64` and `linux/arm64`) is built by GitHub Actions and published to `ghcr.io/jlleongarcia/dicom-anonymizer` on every push to `main`.

1. **Start the container** using the published image:

   ```bash
   docker compose pull
   docker compose up -d
   ```

   Or build the image locally instead:

   ```bash
   docker compose up -d --build
   ```

   The app will be accessible at `http://localhost:8504`. The container always listens on port `8504`; to serve it on a different host port, change the left side of the `ports` mapping in `docker-compose.yml` (e.g. `"8080:8504"`). The container is configured with `restart: always`, so it comes back after a crash or a server reboot.

2. **Update to the latest image:**

   ```bash
   docker compose pull
   docker compose up -d
   ```

3. **Stop it:**

   ```bash
   docker compose down
   ```

> **Note:** If the published package is private on GitHub Container Registry, run `docker login ghcr.io` on the server before pulling, or make the package public in its GitHub settings.

#### How the image is built

- **Base image:** `python:3.13-slim`.
- **Dependencies:** installed with `pip install -r requirements.txt`, which pins every package to the versions in `uv.lock`.
- **Process:** Streamlit runs directly as the main process (not through `main.py`), so it receives the stop signal from `docker stop` and shuts down cleanly.
- **Security:** the app runs as a non-root user.
- **Health check:** Docker polls Streamlit's `/_stcore/health` endpoint, so `docker ps` shows whether the app is healthy.
- **Privacy:** Streamlit's usage statistics are disabled, given the clinical setting.
- **No volumes needed:** files are uploaded through the browser and processed in memory, so the container doesn't need access to any host folder.

## Usage

The app has two tabs. Both work on files uploaded from the browser; the originals are never modified.

### Anonymize Files

1. **Select tags:** the application lists DICOM tags recommended for anonymization, grouped by category. By default, all are selected. You can expand the categories and deselect any tags you wish to keep.
2. **Upload files:** drag and drop one or more DICOM files, or a ZIP archive containing them. Any file name is accepted, since DICOM files often have no extension; files that aren't DICOM are skipped and listed after processing.
3. **Anonymize:** click "Anonymize files".
4. **Download:** a single file is downloaded as `<name>_anonymized.dcm`. Several files are downloaded as `anonymized_dicom.zip`, keeping the original file names and, for ZIP uploads, the original folder structure.

> **Tip:** to anonymize a whole study folder, compress it into a ZIP archive and upload the archive.

### Modify Tags

1. **Upload files:** drag and drop one or more `.dcm` files into the uploader.
2. **Set values:** fill in new values for the common tags shown, and/or add rows in the "Other tags" table for any tag by keyword (e.g. `PatientName`) or number (e.g. `0010,0010`). Blank common-tag fields are left unchanged; use `\` to separate multiple values.
3. **Apply:** click "Apply modifications". A per-file report shows which tags were updated or added.
4. **Download:** download each modified file (named `<name>_modified.dcm`) individually, or grab them all as a single ZIP.

## How it works

The anonymizer performs the following actions on the selected tags of each file:

- **Removes/blanks personal information:** tags containing names (`PN`), short text (`SH`, `LO`), long text (`LT`, `ST`), and other descriptive fields are replaced with `"ANONYMIZED"` or blanked.
- **Replaces dates and times:** date (`DA`) and time (`TM`) tags are replaced with dummy values (`18000101` and `000000`).
- **Generates new UIDs:** unique identifier (`UI`) tags are replaced with newly generated UIDs to break links between studies, series, and instances.
- **Removes private tags:** all private tags are removed to prevent potential data leakage.

The anonymization logic is based on the recommendations in **DICOM Standard PS3.15, Annex E**.

## Dependencies

| Package | Version |
|---|---|
| Python | ≥ 3.13 |
| [Streamlit](https://streamlit.io/) | 1.66.1 |
| [pydicom](https://pydicom.github.io/) | 3.0.1 |

`uv.lock` is the source of truth. `requirements.txt` is generated from it for the Docker image, so both ways of running the app use exactly the same versions.

### Updating dependencies

After changing dependencies in `pyproject.toml`, relock and regenerate `requirements.txt`:

```bash
uv lock
uv export --format requirements-txt --no-hashes --no-dev --no-emit-project --frozen -o requirements.txt
```

Never edit `requirements.txt` by hand; the [requirements sync workflow](#cicd) will fail if it doesn't match `uv.lock`.

## CI/CD

Two GitHub Actions workflows run on this repository:

- **`requirements-sync.yml`** runs on every push and pull request. It fails if `uv.lock` is out of date with `pyproject.toml`, or if `requirements.txt` doesn't match `uv.lock`. This keeps the local and Docker setups on the same versions.
- **`docker-publish.yml`** builds the image for `linux/amd64` and `linux/arm64`.
  - On pull requests to `main`, it only builds the image, to check that the Dockerfile still works.
  - On pushes to `main` (including merges), it also publishes the image to `ghcr.io/jlleongarcia/dicom-anonymizer`, tagged `latest` and with the commit SHA.
  - It can also be started manually from the Actions tab.

## Project structure

```
├── main.py                     # Local entry point – launches Streamlit
├── anonymize_dicom.py          # Streamlit application
├── pyproject.toml              # Project metadata and dependencies
├── uv.lock                     # Locked dependency versions (source of truth)
├── requirements.txt            # Same versions exported for pip (Docker)
├── Dockerfile                  # Container image definition
├── docker-compose.yml          # Deployment configuration
├── .dockerignore               # Files excluded from the Docker build context
├── LICENSE                     # MIT License
├── .github/workflows/
│   ├── requirements-sync.yml   # Checks requirements.txt matches uv.lock
│   └── docker-publish.yml      # Builds and publishes the multi-arch image
└── .streamlit/
    └── config.toml             # Streamlit config (upload limit)
```

## License

This project is licensed under the [MIT License](LICENSE).
