import os
import sqlite3


def main():
    connection = sqlite3.Connection('jobs.db')
    cursor = connection.cursor()

    files = os.listdir("job_descriptions")
    status = []
    for file in files:
        try:
            job = cursor.execute(f"SELECT id, status FROM job_search WHERE file='{file}'").fetchone()
            if job is not None:
                if job[1] == 'not_interested':
                    os.remove(f'job_descriptions/{file}')
                else:
                    status.append(job[1])
            else:
                os.remove(f'job_descriptions/{file}')
        except sqlite3.OperationalError:
            os.remove(f'job_descriptions/{file}')

    if all([s == 'applied' for s in status]):
        print('Only remaining jobs are applied')
    else:
        print('There are remaining jobs that need processing')


if __name__ == '__main__':
    main()
