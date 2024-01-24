import os
import typer
import pyxnat
from dotenv import load_dotenv
from xnat_admin_tools.utils.common import fetch_all_projects, create_new_project, set_xsync_credentials, copy_project_settings

load_dotenv()

app = typer.Typer()

@app.command()
def replicate_projects():

    xrelay_host = os.environ.get("XNAT_RELAY_HOST", "")
    xrelay_user = os.environ.get("XNAT_RELAY_USER", "")
    xrelay_pass = os.environ.get("XNAT_RELAY_PASS", "")
    xrelay2_host = os.environ.get("XNAT_RELAY2_HOST", "")
    xrelay2_user = os.environ.get("XNAT_RELAY2_USER", "")
    xrelay2_pass = os.environ.get("XNAT_RELAY2_PASS", "")
    xserver_host = os.environ.get("XNAT_SERVER_HOST", "")
    xserver_user = os.environ.get("XNAT_SERVER_USER", "")
    xserver_pass = os.environ.get("XNAT_SERVER_PASS", "")


    # Establish connections to source and destination XNAT instances
    source_connection = pyxnat.Interface(server=xrelay_host, user=xrelay_user, password=xrelay_pass)
    dest_connection = pyxnat.Interface(server=xrelay2_host, user=xrelay2_user, password=xrelay2_pass)

    # Fetch projects from production and backup relays
    my_relay_projects = fetch_all_projects(xrelay_host, xrelay_user, xrelay_pass)
    other_relay_projects = fetch_all_projects(xrelay2_host, xrelay2_user, xrelay2_pass)


    # Extract project IDs from project lists
    my_project_ids = {project["ID"] for project in my_relay_projects["ResultSet"]["Result"]}
    other_project_ids = {project["ID"] for project in other_relay_projects["ResultSet"]["Result"]}

    # Find projects that are in prod but not in backup
    unique_to_other = other_project_ids - my_project_ids 

    # For all projects, fetch from adjacent relay and create on local.
    for project_id in unique_to_other:
        create_new_project(
            project_id,
            xrelay2_host, 
            xrelay2_user, 
            xrelay2_pass, 
            xrelay_host, 
            xrelay_user, 
            xrelay_pass,
            source_connection,
            dest_connection,
        )

        # Copy latest xsync project settings
        response = copy_project_settings(
            xrelay_host, 
            xrelay_user, 
            xrelay_pass, 
            xrelay2_host,
            xrelay2_user,
            xrelay2_pass,
            project_id
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

        # Set up Xsync remote credentials
        response = set_xsync_credentials(
            xrelay_host,
            xrelay_user,
            xrelay_pass,
            xserver_host,
            xserver_user,
            xserver_pass,
            project_id,
        )

        if response.status_code == 200:
            typer.echo(response.text)
        else:
            typer.echo(
                """Project credentials for {} could not be set.
                    Please manually set the credentials""".format(
                    project_id
                )
            )

    source_connection.disconnect()
    dest_connection.disconnect()

def main():
    app()
