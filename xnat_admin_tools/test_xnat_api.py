import glob
import json
import os
import random
import shutil
import sys

import requests
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth
from xnat_tools.dicom_export import dicom_export

load_dotenv()

BASE_URL = os.getenv("BASE_URL")
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


def extract_valid_sequence(session_report):
    smallest_seq = (None, float("inf"))
    for scan in session_report["items"][0]["children"][0]["items"]:
        file_size = scan["children"][0]["items"][0]["data_fields"]["file_size"]
        seq_id = scan["data_fields"]["ID"]

        if file_size < smallest_seq[1]:
            smallest_seq = (seq_id, file_size)

    return smallest_seq[0]


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
    num_projects = int(projects["ResultSet"]["totalRecords"])
    assert num_projects != 0, "Zero projects retrieved"
    print(f"Projects retrieved: {num_projects}")

    hasSessions = False
    while not hasSessions:
        # Fetch random project to export
        rand_proj_id = projects["ResultSet"]["Result"][random.randrange(num_projects)][
            "ID"
        ]
        rand_proj_resp = make_request(
            "GET", f"/data/projects/{rand_proj_id}", params={"format": "json"}
        )
        assert (
            rand_proj_resp.status_code == 200
        ), f"Failed to retrieve project {rand_proj_id}"

        # Fetch random session from project
        rand_sess_resp = make_request(
            "GET", f"/data/projects/{rand_proj_id}/experiments"
        )
        assert (
            rand_sess_resp.status_code == 200
        ), f"Failed to retrieve project {rand_proj_id} sessions"
        project_sessions = rand_sess_resp.json()

        # Ensure project has sessions before selecting
        num_sessions = int(project_sessions["ResultSet"]["totalRecords"])
        if num_sessions > 0:
            hasSessions = True

    rand_sess = project_sessions["ResultSet"]["Result"][random.randrange(num_sessions)][
        "ID"
    ]

    # # Test getting an experiment
    print("Testing session retrieval...")
    session_response = make_request(
        "GET",
        f"/data/experiments/{rand_sess}",
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

    # # Test getting an experiment's scans
    print("Testing session scans retrieval...")
    scans_response = make_request(
        "GET", f"/data/experiments/{rand_sess}/scans", params={"format": "json"}
    )
    assert scans_response.status_code == 200, "Failed to retrieve session scans"
    scans = scans_response.json()
    print(f"Scans retrieved: {scans}")

    # Test getting a subject
    print("Testing subject retrieval...")
    subject_id = session["ResultSet"]["Result"][0]["subject_ID"]
    subject_response = make_request(
        "GET",
        f"/data/subjects/{subject_id}",
        params={"format": "json", "handler": "values", "columns": "label"},
    )
    assert subject_response.status_code == 200, "Failed to retrieve subject"
    subject = subject_response.json()
    print(f"Subject retrieved: {subject}")

    # Test requesting single experiment record
    experiment_resp = make_request(
        "GET", f"/data/experiments/{rand_sess}", params={"format": "json"}
    )
    assert (
        experiment_resp.status_code == 200
    ), f"Failed to retrieve experiment report {rand_sess}"
    print(experiment_resp.json())

    seq_id = extract_valid_sequence(experiment_resp.json())

    # Test exporting DICOM data
    print("Testing DICOM export...")
    bids_root_dir = "./tests/xnat2bids"

    if os.path.exists(bids_root_dir):
        shutil.rmtree(bids_root_dir, ignore_errors=True)

    os.makedirs(bids_root_dir, exist_ok=True)

    dicom_export(
        session=f"{rand_sess}",
        bids_root_dir=bids_root_dir,
        user=USERNAME,
        password=PASSWORD,
        host=BASE_URL,
        session_suffix="-1",
        bidsmap_file="",
        includeseq=[f"{seq_id}"],
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
