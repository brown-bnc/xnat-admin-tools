import os
from datetime import datetime, timedelta

import psutil
import pyxnat
import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()


@app.command()
def remove_stale(connection: pyxnat.Interface, days: int):
    """Removes participant data form an XNAT host that is older
    than the specified number of days"""
    typer.echo(f"Searching sessions older than {days} days")
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    date_time = cutoff.strftime("%Y-%m-%d, %H:%M:%S")
    to_delete = (
        connection.select(
            "xnat:mrSessionData",
            [
                "xnat:mrSessionData/PROJECT",
                "xnat:mrSessionData/SUBJECT_ID",
                "xnat:mrSessionData/SUBJECT_LABEL",
                "xnat:mrSessionData/INSERT_DATE",
            ],
        )
        .where([("xnat:mrSessionData/INSERT_DATE", "<", date_time)])
        .data
    )

    typer.echo(f"Found {len(to_delete)} sessions")
    for session in to_delete:
        typer.echo(f"Deleting {session}")
        p = connection.select.project(session["project"])
        p.subject(session["subject_id"]).delete()
        assert not p.subject(
            session["subject_id"]
        ).exists(), "Participant data was not deleted"


@app.command()
def enforce_disk_usage(
    path: str, percent: int, min_days: int, max_days: int, step_days: int = -5
):
    """Checks the percent usage of a location,
    then remove stale projects until target percent min_days is hit,
    whichever comes first"""

    xnat_host = os.environ.get("XNAT_RELAY_HOST", "https://xrelay.bnc.brown.edu")
    xnat_user = os.environ.get("XNAT_RELAY_USER", "admin")
    xnat_pass = os.environ.get("XNAT_RELAY_PASS", "")

    connection = pyxnat.Interface(server=xnat_host, user=xnat_user, password=xnat_pass)

    for days in range(max_days, min_days, step_days):
        disk_usage = psutil.disk_usage(path).percent
        typer.echo(f"Current disk usage for {path} is {disk_usage}")
        if disk_usage > percent:
            remove_stale(connection, days)
        else:
            break

    connection.disconnect()


def main():
    app()
