import glob
import json
import os
import shutil
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from xnat_tools.dicom_export import dicom_export

load_dotenv()

BASE_URL = "https://qa-xnat.bnc.brown.edu"
USERNAME = os.getenv("XNAT_SERVER_USER")
PASSWORD = os.getenv("XNAT_SERVER_PASS")


# Helper function for making requests
def make_request(method, endpoint, data=None, params=None):
    url = f"{BASE_URL}{endpoint}"
    try:
        response = requests.request(
            method,
            url,
            auth=HTTPBasicAuth(USERNAME, PASSWORD),
            headers={"Content-Type": "application/json"},
            data=json.dumps(data) if data else None,
            params=params,
        )
        response.raise_for_status()
        return response
    except requests.exceptions.RequestException as e:
        print(f"Request failed: {e}")
        sys.exit(1)


# Test Suite
def test_xnat_api():
    print("Starting XNAT API tests...")

    # Test authentication
    print("Testing authentication...")
    auth_response = make_request("GET", "/data/JSESSION")
    assert auth_response.status_code == 200, "Authentication failed"
    session_id = auth_response.text.strip()
    print(f"Authentication successful. Session ID: {session_id}")

    # Test getting projects
    print("Testing project retrieval...")
    projects_response = make_request("GET", "/data/projects")
    assert projects_response.status_code == 200, "Failed to retrieve projects"
    projects = projects_response.json()
    assert int(projects["ResultSet"]["totalRecords"]) != 0, "Zero projects retrieved"
    print(f"Projects retrieved: {int(projects['ResultSet']['totalRecords'])}")

    # Test getting an experiment
    print("Testing session retrieval...")
    session_response = make_request(
        "GET",
        "/data/experiments/XNAT_DEV_E00016",
        params={
            "format": "json",
            "handler": "values",
            "columns": "project,subject_ID,label",
        },
    )
    assert session_response.status_code == 200, "Failed to retrieve session"
    print(session_response)
    session = session_response.json()
    print(f"Session retrieved: {session}")

    # Test getting an experiment's scans
    print("Testing session scans retrieval...")
    scans_response = make_request(
        "GET", "/data/experiments/XNAT_DEV_E00016/scans", params={"format": "json"}
    )
    assert scans_response.status_code == 200, "Failed to retrieve session scans"
    scans = scans_response.json()
    print(f"Scans retrieved: {scans}")

    # Test getting a subject
    print("Testing subject retrieval...")
    subject_response = make_request(
        "GET",
        "/data/subjects/XNAT_DEV_S00014",
        params={"format": "json", "handler": "values", "columns": "label"},
    )
    assert subject_response.status_code == 200, "Failed to retrieve subject"
    subject = subject_response.json()
    print(f"Subject retrieved: {subject}")

    # Test exporting DICOM data
    print("Testing DICOM export...")
    bids_root_dir = "./tests/xnat2bids"

    if os.path.exists(bids_root_dir):
        shutil.rmtree(bids_root_dir, ignore_errors=True)

    os.makedirs(bids_root_dir, exist_ok=True)

    dicom_export(
        session="XNAT_DEV_E00017",
        bids_root_dir=bids_root_dir,
        user=USERNAME,
        password=PASSWORD,
        host=BASE_URL,
        session_suffix="-1",
        bidsmap_file="",
        includeseq=["11"],
        skipseq=[],
        log_id="pytest",
        verbose=0,
        overwrite=False,
        validate_frames=False,
        correct_dicoms_config="",
    )

    dicom_files = glob.glob(f"{bids_root_dir}/**/*.dcm", recursive=True)
    assert len(dicom_files) > 0, "DICOM export failed: No files found"
    print(f"DICOM export successful. Files exported: {len(dicom_files)}")


# Run the tests
def main():
    test_xnat_api()
