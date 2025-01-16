import typer

from xnat_admin_tools.utils.common import fetch_all_projects, set_xsync_credentials

app = typer.Typer()


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
    projects = fetch_all_projects(xrelay_host, xrelay_user, xrelay_pass)

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
