import os

import typer
from rq.job import Job

app = typer.Typer()


def get_redis_queue():
    """
    Initiates a connection to redis queue
    """
    import redis

    redis_conn = redis.Redis(
        host=os.getenv("REDIS_HOST", "localhost"),
        port=os.getenv("REDIS_PORT", "6379"),
        password=os.getenv("REDIS_PASSWORD", ""),
    )

    return redis_conn


@app.command()
def get_result(job_id):
    """Takes a job_id and returns the job's result."""

    redis_conn = get_redis_queue()

    job = Job.fetch(job_id, connection=redis_conn)

    typer.echo("Is the job queued: {}".format(job.is_queued))
    typer.echo("Is the job failed: {}".format(job.is_failed))
    typer.echo("Is the job started: {}".format(job.is_started))
    typer.echo("Is the job finished: {}".format(job.is_finished))

    if job.exc_info:
        typer.echo("Job exited with following exception:\n{}".format(job.exc_info))

    if not job.result:
        typer.echo("result not found")
    else:
        typer.echo("Results: {}".format(job.result))


def main():
    app()
