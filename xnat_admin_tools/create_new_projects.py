import os
import pyxnat
import typer
from dotenv import load_dotenv
from xnat_admin_tools.utils.common import create_new_project, set_project_settings, set_xsync_credentials, add_users_as_owners

load_dotenv()

app = typer.Typer()



@app.command()
def create_new_projects(project_id: str):
    """
    Create a project on server with the same settings on relay

    This funtion creates a project on xnat server with same settings on the relay
    Investigators are added as users
    """

    typer.echo("Creating project {} on XNAT server".format(project_id))

    xrelay_host = os.environ.get("XNAT_RELAY_HOST", "")
    xrelay_user = os.environ.get("XNAT_RELAY_USER", "")
    xrelay_pass = os.environ.get("XNAT_RELAY_PASS", "")
    xserver_host = os.environ.get("XNAT_SERVER_HOST", "")
    xserver_user = os.environ.get("XNAT_SERVER_USER", "")
    xserver_pass = os.environ.get("XNAT_SERVER_PASS", "")

    
    # Establish connections to source and destination XNAT instances
    source_connection = pyxnat.Interface(server=xrelay_host, user=xrelay_user, password=xrelay_pass)
    dest_connection = pyxnat.Interface(server=xserver_host, user=xserver_user, password=xserver_pass)

    project = create_new_project(
        project_id, 
        xrelay_host, 
        xrelay_user, 
        xrelay_pass, 
        xserver_host, 
        xserver_user, 
        xserver_pass,
        source_connection,
        dest_connection,
    )

    add_users_as_owners(project, project_id, source_connection, dest_connection)


    # set up Xsync project credentials
    response = set_project_settings( 
        xrelay_host,
        xrelay_user,
        xrelay_pass,
        xserver_host,
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

    # Xsync settings
    # set up Xsync remote credentials
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
