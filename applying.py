import os
import sqlite3

from sites import Seek


def main():
    seek = Seek(None)
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()
    jobs = cursor.execute("SELECT * FROM jobs WHERE status='interested_read'").fetchall()
    for job in jobs:
        choice = 0
        print(f'{job[1]} - {job[2]}\n{seek.build_job_link(job[0])}')
        while choice not in {'y', 'n', 'not available', 'not interested'}:
            choice = input('Have you applied? [y/n/not available/not interested]: ')
        if choice == 'y':
            cursor.execute(f"UPDATE jobs SET status='applied' WHERE id={job[0]}")
        if choice in {'not available', 'not interested'}:
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE id={job[0]}")
            try:
                os.remove(f'job_descriptions/{job[3]}')
            except FileNotFoundError:
                print('Could not find file to remove, skipping.')
        print()


if __name__ == '__main__':
    main()
