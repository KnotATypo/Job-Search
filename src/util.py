import os
import re

root_path = os.path.realpath(__file__)[: os.path.realpath(__file__).rindex("Job-Search") + 10]


def del_job_description(job_file):
    try:
        os.remove(f"{root_path}/job_descriptions/{job_file}")
    except FileNotFoundError:
        print("Could not find file to remove, skipping.")


def get_job_description(job_file):
    with open(f"{root_path}/job_descriptions/{job_file}", "r") as f:
        return f.read()


def download_job_description(job, clas):
    file_name = f"{job[1]}-{job[2]}-{job[0]}.html".replace("/", "_")
    with open(f"{root_path}/job_descriptions/{file_name}", "w+") as f:
        description = clas.get_job_description(job[0])
        if description is not None:
            f.write(description)
        else:
            raise FileNotFoundError


def strip_string(s: str) -> str:
    return re.sub(r"\W", "", s.lower())


def get_duplicate_status(id_source, cursor):
    status = []
    cursor.execute(f"SELECT duplicate FROM job_search WHERE id='{id_source}'")
    for id_target in str(cursor.fetchone()[0]).split(","):
        cursor.execute(f"SELECT status FROM job_search WHERE id='{id_target}'")
        status.append(cursor.fetchone()[0])
    if "applied" in status:
        return "applied"
    if "easy_filter" in status:
        return "easy_filter"
    if "interested_read" in status:
        return "interested_read"
    if "interested" in status:
        return "interested"
    if all([x == "not_interested" for x in status]):
        return "not_interested"
    if all([x == "new" for x in status]):
        return "new"
    return "???"
