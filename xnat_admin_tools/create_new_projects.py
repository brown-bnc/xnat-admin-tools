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


def set_xsync_credentials(
    xrelay_host: str,
    xrelay_user: str,
    xrelay_pass: str,
    xserver_host: str,
    xserver_user: str,
    xserver_pass: str,
    project_id: str,
):
    """
    Sets remote server credentials for Xsync service on the relay

    If this step fails please set credentials manually
    """
    import json

    import requests
    from requests.auth import HTTPBasicAuth

    # get token from xnat remote server
    basic = HTTPBasicAuth(xserver_user, xserver_pass)
    get_url = xserver_host + "/data/services/tokens/issue"
    R = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )
    response = R.json()

    alias, secret, expiration = (
        response["alias"],
        response["secret"],
        response["estimatedExpirationTime"],
    )

    get_url = xserver_host + f"/data/projects/{project_id}/config/xsync"
    R = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )

    response = R.json()

    xsync_config = response["ResultSet"]["Result"][0]["contents"]
    content_dict = json.loads(xsync_config)
    remote_project_id = content_dict["remote_project_id"]
    # make the post call to xsync on relay
    basic = HTTPBasicAuth(xrelay_user, xrelay_pass)
    payload = {
        "username": xserver_user,
        "secret": secret,
        "host": xserver_host,
        "alias": alias,
        "localProject": project_id,
        "remoteProject": remote_project_id,
        "estimatedExpirationTime": expiration,
    }

    post_url = xrelay_host + "/xapi/xsync/credentials/save/projects/" + project_id
    # print(post_url)
    R = requests.request(
        "POST",
        post_url,
        headers={"Content-Type": "text/plain"},
        data=json.dumps(payload),
        auth=basic,
    )

    return R


def set_project_settings(
    xrelay_host: str,
    xrelay_user: str,
    xrelay_pass: str,
    xserver_host: str,
    project_id: str,
):
    """
    Sets project settings for the project on the relay

    If this step fails please set the project settings manually
    """
    import json

    import requests
    from requests.auth import HTTPBasicAuth

    basic = HTTPBasicAuth(xrelay_user, xrelay_pass)
    payload = {
        "project_resources": {"sync_type": "none"},
        "subject_resources": {"sync_type": "none"},
        "subject_assessors": {"sync_type": "none"},
        "imaging_sessions": {"sync_type": "all"},
        "enabled": True,
        "source_project_id": project_id,
        "sync_frequency": "on demand",
        "sync_new_only": True,
        "identifiers": "use_local",
        "remote_url": xserver_host,
        "remote_project_id": project_id,
        "notification_emails": "",
        "customIdentifiers": "dateTimeLabelGenerator",
        "anonymize": False,
        "no_of_retry_days": 3,
    }

    post_url = xrelay_host + "/xapi/xsync/setup/projects/" + project_id
    R = requests.request(
        "POST",
        post_url,
        headers={"Content-Type": "text/plain"},
        data=json.dumps(payload),
        auth=basic,
    )

    return R


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

    typer.echo("Found project with project details {}".format(project_values[0]))

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

    accessibility = (
        xrelay_connection.select(
            "xnat:projectData",
            ["xnat:projectData/PROJECT_ACCESS"],
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    try:
        values_to_insert = remove_empty(values_to_select, project_values[0])
        typer.echo("Creating project on server")
        server_project = xserver_connection.select.project(project_id)

        if not (server_project.exists()):
            server_project.create(**values_to_insert)
            typer.echo("Project {} created".format(project_id))
            typer.echo("Project created with values {}".format(values_to_insert))
            server_project.set_accessibility(
                accessibility=accessibility[0]["project_access"]
            )
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

            # set up Xsync project credentials
            response = set_project_settings(
                xrelay_host, xrelay_user, xrelay_pass, xserver_host, project_id
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

        else:
            typer.echo("{} project already exists on server".format(project_id))
    except IndexError:
        typer.echo("Project with {} not found".format(project_id))

    xrelay_connection.disconnect()
    xserver_connection.disconnect()


def main():
    app()
