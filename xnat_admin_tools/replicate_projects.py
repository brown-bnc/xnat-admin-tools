import os

import pyxnat
import typer
from dotenv import load_dotenv

from xnat_admin_tools.utils.common import (
    copy_project_settings,
    create_new_project,
    fetch_all_projects,
)

load_dotenv()

app = typer.Typer()


@app.command()
def replicate_projects():
    prod_xserver_host = os.environ.get("PROD_XNAT_SERVER_HOST", "")
    qa_xserver_host = os.environ.get("QA_XNAT_SERVER_HOST", "")

    xserver_user = os.environ.get("XNAT_SERVER_USER", "")
    xserver_pass = os.environ.get("XNAT_SERVER_PASS", "")

    # Establish connections to source and destination XNAT instances
    prod_connection = pyxnat.Interface(
        server=prod_xserver_host, user=xserver_user, password=xserver_pass
    )
    qa_connection = pyxnat.Interface(
        server=qa_xserver_host, user=xserver_user, password=xserver_pass
    )

    # Fetch projects from production and backup relays
    prod_relay_projects = fetch_all_projects(
        prod_xserver_host, xserver_user, xserver_pass
    )
    qa_relay_projects = fetch_all_projects(qa_xserver_host, xserver_user, xserver_pass)

    # Extract project IDs from project lists
    my_project_ids = {
        project["ID"] for project in prod_relay_projects["ResultSet"]["Result"]
    }
    other_project_ids = {
        project["ID"] for project in qa_relay_projects["ResultSet"]["Result"]
    }

    # Find projects that are in prod but not in backup
    unique_to_other = my_project_ids - other_project_ids

    print("Projects unique to other relay: ", unique_to_other)

    # # For all projects, fetch from adjacent relay and create on local.
    for project_id in unique_to_other:
        try:
            create_new_project(
                project_id,
                prod_connection,
                qa_connection,
            )
        except Exception as e:
            print("Error: ", e)
            continue

        # Copy latest xsync project settings
        response = copy_project_settings(
            prod_xserver_host,
            xserver_user,
            xserver_pass,
            qa_xserver_host,
            xserver_user,
            xserver_pass,
            project_id,
        )

        if response.status_code == 200:
            typer.echo(response.text)
        else:
            typer.echo(
                """Project settings for {} could not be set.
                    Please manually set the credentials""".format(
                    project_id
                )
            )
            print(response.status_code, response.text)

    prod_connection.disconnect()
    qa_connection.disconnect()


def main():
    app()
