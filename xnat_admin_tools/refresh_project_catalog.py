import os

import requests
import typer
from dotenv import load_dotenv
from requests.auth import HTTPBasicAuth

load_dotenv()

app = typer.Typer()


@app.command()
def refresh_project_catalog():
    xserver_host = os.environ.get("PROD_XNAT_SERVER_HOST", "")
    xserver_user = os.environ.get("XNAT_SERVER_USER", "")
    xserver_pass = os.environ.get("XNAT_SERVER_PASS", "")

    project_id = "BREWER_TBD"
    subject_id = "P2157T2034"
    experiment_id = "XNAT_E00845"
    scan_id = "11"

    # Construct the resource parameter
    resource_param = (
        f"/archive/projects/{project_id}/subjects/{subject_id}/"
        f"experiments/{experiment_id}/scans/{scan_id}"
    )

    # Construct the URL with the resource parameter as a query string
    post_url = f"{xserver_host}/data/services/refresh/catalog?resource={resource_param}"

    # POST request to refresh catalog in XNAT
    basic = HTTPBasicAuth(xserver_user, xserver_pass)

    response = requests.post(
        post_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )

    print("Response: ", response)
    if response.status_code == 200:
        print("Catalog refreshed successfully.")
    else:
        print(f"Failed to refresh catalog. Status code: {response.status_code}")
        print(f"Response: {response.text}")


def main():
    app()


if __name__ == "__main__":
    main()
