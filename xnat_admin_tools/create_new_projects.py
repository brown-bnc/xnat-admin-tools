import os

import pyxnat
import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()


def get_user_details(connection: pyxnat.Interface):
    """
    Get the details for all users on the server
    Input:
        connection: Instantiated pyxnat.Interface class
    Returns:
        user_details: Dictionary with userid associated for all users on the server
                      e.g. {"lastname, firstname": userid}
    """

    users = connection.manage.users()
    users_details = {}
    for user in users:
        firstname = connection.manage.users.firstname(user)
        lastname = connection.manage.users.lastname(user)
        users_details["{}, {}".format(lastname, firstname)] = user

    return users_details


def remove_empty(values_to_select, project_values):
    """
    Remove empty fields, create request for fields to be inserted on server
    Input:
        values_to_select: list of all variables selected from relay
        project_values: request returned by the relay (type: dictionary)
    Output:
        values_to_insert: request for values to be inserted on the server (type: dictionary)
    """
    values_to_insert = {}
    for insert_tag, value in zip(values_to_select, list(project_values.values())):
        if value:
            if insert_tag == "xnat:projectData/PI":
                values_to_insert["xnat:projectData/PI/firstname"] = value.split()[0]
                values_to_insert["xnat:projectData/PI/lastname"] = value.split()[1]
            else:
                values_to_insert[insert_tag] = value

    return values_to_insert


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
    xrelay_connection = pyxnat.Interface(
        server=xrelay_host, user=xrelay_user, password=xrelay_pass
    )
    xserver_connection = pyxnat.Interface(
        server=xserver_host, user=xserver_user, password=xserver_pass
    )

    typer.echo("Retrieved relay and server connections")

    values_to_select = [
        "xnat:projectData/ID",
        "xnat:projectData/NAME",
        "xnat:projectData/SECONDARY_ID",
        "xnat:projectData/PI",
        "xnat:projectData/DESCRIPTION",
    ]

    # The API returns a list of dictionary elements of all values selected
    project_values = (
        xrelay_connection.select(
            "xnat:projectData",
            values_to_select,
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    # The PI are added as project investigators
    # users contains is a list of PI + project investigatos of the project
    # The API returns a list of dict(zip("project_invs",
    #                                    "PI(lastname, firstname) <br/>
    #                                     investigator 1(lastname, firstname) <br/>
    #                                     investigator 2(lastname, firstname) ..."))
    users = (
        xrelay_connection.select(
            "xnat:projectData",
            ["xnat:projectData/PROJECT_INVS"],
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    user_details = get_user_details(xserver_connection)

    try:
        values_to_insert = remove_empty(values_to_select, project_values[0])
        typer.echo("Creating project on server")
        server_project = xserver_connection.select.project(project_id)

        if not (server_project.exists()):
            server_project.create(**values_to_insert)
            typer.echo("Project {} created".format(project_id))

            # Add users as owners
            for user in users[0]["project_invs"].split("<br/>"):
                try:
                    userid = user_details[user.strip()]
                    server_project.add_user(userid, role="owner")
                except KeyError:
                    typer.echo(
                        "Could not find PI {} as a user on xnat server".format(user)
                    )
                    pass
        else:
            typer.echo("{} project already exists on server".format(project_id))
    except IndexError:
        typer.echo("Project with {} not found".format(project_id))

    xrelay_connection.disconnect()
    xserver_connection.disconnect()


def main():
    app()
