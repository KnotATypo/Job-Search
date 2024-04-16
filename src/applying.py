import psycopg2

import sites


def main():
    connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
    connection.autocommit = True

    cursor = connection.cursor()
    cursor.execute("SELECT * FROM job_search WHERE status='interested_read'")
    jobs = cursor.fetchall()
    for job in jobs:
        site = sites.get_site_instance(job[6], connection, None)
        link = site.build_job_link(job[0])

        print(f'{job[1]} - {job[2]}\n{link}')
        choice = 0
        while choice not in {'y', 'n', 'not available'}:
            choice = input('Have you applied? [y/n/not available]: ')
        if choice == 'y':
            cursor.execute(f"UPDATE job_search SET status='applied' WHERE id='{str(job[0])}'")
        if choice in {'not available'}:
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE id='{str(job[0])}'")
        connection.commit()
        print()


if __name__ == '__main__':
    main()
