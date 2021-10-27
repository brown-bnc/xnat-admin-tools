import os

import pyxnat
from dotenv import load_dotenv

# from datetime import datetime, timedelta


load_dotenv()

if __name__ == "__main__":

    # I used export env variables as well as hard coding the fields
    xnat_host = os.environ.get("XNAT_HOST", "")
    xnat_user = os.environ.get("XNAT_USER", "")
    xnat_pass = os.environ.get("XNAT_PASS", "")
    connection = pyxnat.Interface(server=xnat_host, user=xnat_user, password=xnat_pass)

    # I tried listing the projects as they mention in documentation
    projects = connection.select("/project").get()
    # projects = connection.select.projects().get()

    print(projects)  # I get an empty array here

    # Then I tried to reproduce your code from other file and it again crashes

    # now = datetime.now()
    # cutoff = now - timedelta(days=days)
    # date_time = cutoff.strftime("%Y-%m-%d, %H:%M:%S")
    # to_delete = (
    #     connection.select(
    #         "xnat:mrSessionData",
    #         [
    #             "xnat:mrSessionData/PROJECT",
    #             "xnat:mrSessionData/SUBJECT_ID",
    #             "xnat:mrSessionData/INSERT_DATE",
    #         ],
    #     )
    #     .where([("xnat:mrSessionData/INSERT_DATE", "<", date_time)])
    #     .data
    # )
    # for session in to_delete:
    #     print(session)

    # connection.disconnect()
