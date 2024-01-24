import pyxnat
import requests
import typer
from requests.auth import HTTPBasicAuth


def add_users_as_owners(project, project_id, src_conn, dst_conn):
    """
    Add users as owners to the specified project.

    :param project: The project object to which users will be added
    :param user_details: Dictionary of user details
    :param users: List of users to be added
    """

    # The PI are added as project investigators
    # users contains is a list of PI + project investigatos of the project
    # The API returns a list of dict(zip("project_invs",
    #               "PI(lastname, firstname) <br/>
    #                investigator 1(lastname, firstname) <br/>
    #                investigator 2(lastname, firstname) ..."))
    users = (
        src_conn.select(
            "xnat:projectData",
            ["xnat:projectData/PROJECT_INVS"],
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    user_details = get_user_details(dst_conn)

    for user in users:
        try:
            userid = user_details[user.strip()]
            project.add_user(userid, role="owner")
        except KeyError:
            typer.echo(f"Could not find PI {user} as a user on XNAT server")
            pass


def create_new_project(
    project_id: str,
    source_host: str,
    source_user: str,
    source_pass: str,
    dest_host: str,
    dest_user: str,
    dest_pass: str,
    src_conn,
    dst_conn,
):
    """
    Create a project on destination server with the same settings as on the source server

    This function creates a project on a destination XNAT server with the same
    settings as on the source server. Investigators are added as users.
    """

    typer.echo(f"Creating project {project_id} on destination XNAT server")

    typer.echo("Retrieved source and destination connections")

    values_to_select = [
        "xnat:projectData/ID",
        "xnat:projectData/NAME",
        "xnat:projectData/SECONDARY_ID",
        "xnat:projectData/PI",
        "xnat:projectData/DESCRIPTION",
    ]

    # The API returns a list of dictionary elements of all values selected
    project_values = (
        src_conn.select(
            "xnat:projectData",
            values_to_select,
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    typer.echo("Found project with project details {}".format(project_values[0]))

    accessibility = (
        src_conn.select(
            "xnat:projectData",
            ["xnat:projectData/PROJECT_ACCESS"],
        )
        .where([("xnat:projectData/ID", "=", project_id)])
        .data
    )

    try:
        values_to_insert = remove_empty(values_to_select, project_values[0])
        typer.echo("Creating project on server")
        server_project = dst_conn.select.project(project_id)

        if not (server_project.exists()):
            server_project.create(**values_to_insert)
            typer.echo("Project {} created".format(project_id))
            typer.echo("Project created with values {}".format(values_to_insert))

            server_project.set_accessibility(
                accessibility=accessibility[0]["project_access"]
            )

        else:
            typer.echo("{} project already exists on server".format(project_id))
    except IndexError:
        typer.echo("Project with {} not found".format(project_id))

    return server_project


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


def fetch_all_projects(xserver_host, xserver_user, xserver_pass):
    # GET all projects from xnat remote server
    basic = HTTPBasicAuth(xserver_user, xserver_pass)
    get_url = xserver_host + "/data/projects"
    print(get_url)
    response = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )
    print("Response: ", response)
    return response.json()


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

    get_url = xrelay_host + f"/data/projects/{project_id}/config/xsync"
    R = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )

    response = R.json()

    # XNAT stores all prior versions of XSync configs per project. Fetching the latest (-1 index).
    xsync_config = response["ResultSet"]["Result"][-1]["contents"]
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


def copy_project_settings(
    xrelay_host: str,
    xrelay_user: str,
    xrelay_pass: str,
    xrelay2_host: str,
    xrelay2_user: str,
    xrelay2_pass: str,
    project_id: str,
):
    """
    Sets project settings for the project on the relay

    If this step fails please set the project settings manually
    """
    import json

    import requests
    from requests.auth import HTTPBasicAuth

    basic = HTTPBasicAuth(xrelay2_user, xrelay2_pass)
    get_url = xrelay2_host + "/xapi/xsync/setup/projects/" + project_id
    R = requests.request(
        "GET",
        get_url,
        headers={"Content-Type": "text/plain"},
        auth=basic,
    )

    print("GET Response: ", R.json())
    payload = R.json()

    basic = HTTPBasicAuth(xrelay_user, xrelay_pass)
    post_url = xrelay_host + "/xapi/xsync/setup/projects/" + project_id

    print("POST URL: ", post_url)
    R = requests.request(
        "POST",
        post_url,
        headers={"Content-Type": "text/plain"},
        data=json.dumps(payload),
        auth=basic,
    )

    return R
