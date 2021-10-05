import typer
import pyxnat
import os
from datetime import datetime, timedelta
from dotenv import load_dotenv

load_dotenv()

def main(days: int):
    typer.echo(f"Searching sessions older than {days} days")
    xnat_host = os.environ.get("XNAT_HOST", "")
    xnat_user = os.environ.get("XNAT_USER", "")
    xnat_pass = os.environ.get("XNAT_PASS", "")
    connection = pyxnat.Interface(server=xnat_host,
                                  user=xnat_user,
                                  password=xnat_pass)
    now = datetime.now()
    cutoff = now - timedelta(days=days)
    date_time = cutoff.strftime("%Y-%m-%d, %H:%M:%S")
    to_delete = connection.select("xnat:mrSessionData",
                                 ['xnat:mrSessionData/PROJECT', 
                                  'xnat:mrSessionData/SUBJECT_ID', 
                                  'xnat:mrSessionData/INSERT_DATE']).where(
                                 [('xnat:mrSessionData/INSERT_DATE', '<', date_time)]).data
    
    typer.echo(f"Found {len(to_delete)} sessions")
    for session in to_delete:
        typer.echo(f"{session}")


    connection.disconnect()


if __name__ == "__main__":
    typer.run(main)