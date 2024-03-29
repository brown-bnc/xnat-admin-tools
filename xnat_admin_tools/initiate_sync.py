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

    # Sleep till data is available for transfer
    # This container can get prematurely for large datasets
    # If we see file lock errors we might need to increase this
    # waitime
    time.sleep(300)
    post_url = xrelay_host + "/xapi/xsync/syncexperiment/" + experiment_id
    basic = HTTPBasicAuth(xrelay_user, xrelay_pass)
    response = requests.request(
        "POST",
        post_url,
        headers={"Content-Type": "application/json"},
        auth=basic,
    )

    if response.status_code == 423:
        enqueue_sync(experiment_id, label_id)
        return "xsync servers LOCKED: status code {}".format(response.status_code)
    elif response.status_code == 200:
        return "xsync on {} started".format(experiment_id)
    else:
        return "xsync could not be completed. Status code : {}".format(
            response.status_code
        )


@app.command()
def enqueue_sync(experiment_id, label_id):

    redis_queue = get_redis_queue()
    job = redis_queue.enqueue(
        sync_project, args=(experiment_id, label_id), job_timeout=600, result_ttl=604800
    )

    typer.echo("Job started - JOB_ID: {}".format(job.id))


def main():
    app()
