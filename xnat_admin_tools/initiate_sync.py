import os

import typer
from dotenv import load_dotenv

load_dotenv()

app = typer.Typer()


def get_redis_queue():
    """
    Initiates a connection to redis queue
    """
    import redis
    from rq import Queue

    redis_conn = redis.Redis(
        host=os.getenv("REDIS_HOST", "127.0.0.1"),
        port=os.getenv("REDIS_PORT", "6379"),
        password=os.getenv("REDIS_PASSWORD", ""),
    )

    return Queue(connection=redis_conn)


def check_status(label_id):
    """
    Check if the project was alraedy synced previously
    """
    from psycopg2 import connect

    status_whitelist = ["SYNCED_AND_VERIFIED", "SYNCED_AND_NOT_VERIFIED", "SKIPPED"]

    conn = connect(
        host=os.getenv("POSTGRES_HOST", "127.0.0.1"),
        database="xnat",
        user=os.getenv("POSTGRES_USER", ""),
        password=os.getenv("POSTGRES_PASS", ""),
    )
    cur = conn.cursor()
    cur.execute(
        """
        SELECT sync_status
        FROM (
            SELECT created, sync_status
            FROM xhbm_xsync_experiment_history
            WHERE local_label = '{}'
            ORDER BY created DESC
            FETCH FIRST 1 ROWS ONLY) as sub
        ;
    """.format(
            label_id
        )
    )

    if cur.rowcount == 1:
        result = cur.fetchone()
        return result[0] not in status_whitelist

    return True


def sync_project(experiment_id, label_id):
    """
    Basic method to initiated sync

    This method intiates a sync -
        1) The method runs via a redis queue
        2) If the respose code == 423 the method is requeued
        3) skip sync if the project was already synced
    """
    import time

    import requests
    from requests.auth import HTTPBasicAuth

    xrelay_host = os.environ.get("XNAT_RELAY_HOST", "")
    xrelay_user = os.environ.get("XNAT_RELAY_USER", "")
    xrelay_pass = os.environ.get("XNAT_RELAY_PASS", "")

    if check_status(label_id):
        post_url = xrelay_host + "/xapi/xsync/syncexperiment/" + experiment_id
        basic = HTTPBasicAuth(xrelay_user, xrelay_pass)
        post_url = xrelay_host + "/data/services/tokens/issue" + experiment_id
        response = requests.request(
            "POST",
            post_url,
            headers={"Content-Type": "application/json"},
            auth=basic,
        )

        if response.status_code == 423:
            time.sleep(300)
            enqueue_sync(experiment_id)
            return "xsync servers LOCKED"
        elif response.status_code == 200:
            return "xsync on {} started".format(experiment_id)
        else:
            return "xsync could not be completed. Status code : {}".format(
                response.status_code
            )
    else:
        return "Session was already synced previously"


@app.command()
def enqueue_sync(experiment_id, label_id):

    redis_queue = get_redis_queue()
    job = redis_queue.enqueue(sync_project, args=(experiment_id, label_id))

    typer.echo("Job started - JOB_ID: {}".format(job.id))


def main():
    app()
