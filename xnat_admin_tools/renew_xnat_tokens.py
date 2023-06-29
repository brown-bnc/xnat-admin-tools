import requests
import typer
from requests.auth import HTTPBasicAuth

from xnat_admin_tools.create_new_projects import set_xsync_credentials

app = typer.Typer()


def fetch_all_projects(xserver_host, xserver_user, xserver_pass):
    # GET all projects from xnat remote server
    basic = HTTPBasicAuth(xserver_user, xserver_pass)
    get_url = xserver_host + "/data/projects"
    response = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )
    return response.json()


# Iterates over all projects, applying updated token
@app.command()
def renew_xnat_tokens(
    xrelay_host: str,
    xrelay_user: str,
    xrelay_pass: str,
    xserver_host: str,
    xserver_user: str,
    xserver_pass: str,
):
    projects = fetch_all_projects(xserver_host, xserver_user, xserver_pass)

    for project in projects["ResultSet"]["Result"]:
        project_id = project["ID"]
        set_xsync_credentials(
            xrelay_host,
            xrelay_user,
            xrelay_pass,
            xserver_host,
            xserver_user,
            xserver_pass,
            project_id,
        )


def main():
    app()

