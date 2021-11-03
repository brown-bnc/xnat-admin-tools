import os

import pyxnat
import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()


@app.command()
def create_new_projects(project_id: str):
    # I used export env variables as well as hard coding the fields
    xrelay_host = os.environ.get("XNAT_RELAY_HOST", "")
    xrelay_user = os.environ.get("XNAT_RELAY_USER", "")
    xrelay_pass = os.environ.get("XNAT_RELAY_PASS", "")
    xserver_host = os.environ.get("XNAT_SERVER_HOST", "")
    xserver_user = os.environ.get("XNAT_SERVER_USER", "")
    xserver_pass = os.environ.get("XNAT_SERVER_PASS", "")
    xrelay_connection = pyxnat.Interface(
        server=xrelay_host, user=xrelay_user, password=xrelay_pass
    )
    xserver_connection = pyxnat.Interface(
        server=xserver_host, user=xserver_user, password=xserver_pass
    )

    project_values = (
        xrelay_connection.select(
            "xnat:projectData",
            [
                "xnat:projectData/ID",
                "xnat:projectData/NAME",
                "xnat:projectData/DESCRIPTION",
                "xnat:projectData/PI",
            ],
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    for session in project_values:
        print(project_values)

    # server_project = xserver_connection.select.project(project_idß)

    # if not (server_project.exists()):
    #     server_project.create(**project_values[0])

    xrelay_connection.disconnect()
    xserver_connection.disconnect()


def main():
    app()
