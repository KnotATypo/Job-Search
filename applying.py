import os
import sqlite3

from sites import Seek, Jora, Indeed


def main():
    connection = sqlite3.connect('jobs.db')
    seek = Seek(connection)
    jora = Jora(connection)
    indeed = Indeed(connection, None)
    cursor = connection.cursor()
    jobs = cursor.execute("SELECT * FROM jobs WHERE status='interested_read'").fetchall()
    for job in jobs:
        choice = 0
        if job[6] == 'seek':
            link = seek.build_job_link(job[0])
        elif job[6] == 'jora':
            link = jora.build_job_link(job[0])
        elif job[6] == 'indeed':
            link = indeed.build_job_link(job[0])
        else:
            raise Exception('Unknown job site')
        print(f'{job[1]} - {job[2]}\n{link}')
        while choice not in {'y', 'n', 'not available'}:
            choice = input('Have you applied? [y/n/not available]: ')
        if choice == 'y':
            cursor.execute(f"UPDATE jobs SET status='applied' WHERE id='{str(job[0])}'")
        if choice in {'not available'}:
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE id='{str(job[0])}'")
            try:
                os.remove(f'job_descriptions/{job[3]}')
            except FileNotFoundError:
                print('Could not find file to remove, skipping.')
        connection.commit()
        print()


if __name__ == '__main__':
    main()
