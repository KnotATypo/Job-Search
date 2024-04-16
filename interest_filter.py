import psycopg2

import util


def main():
    connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
    connection.autocommit = True
    cursor = connection.cursor()

    cursor.execute("SELECT title, file, id, duplicate FROM job_search WHERE status='new'")
    jobs = cursor.fetchall()

    jobs.sort(key=lambda x: x[1])
    for i, (name, file, id, duplicate) in enumerate(jobs):
        choice = 0
        print(f'{i}/{len(jobs)}')
        if duplicate is not None:
            dup_status = util.get_duplicate_status(id, cursor)
            print('Duplicate status:', dup_status)
        while choice not in {'n', 'y'}:
            choice = input(f'{name}\nAre you interested? [y/n/undo]: ')
            choice = choice.lower()
            if choice == 'undo':
                cursor.execute(f"UPDATE job_search SET status='new' WHERE file='{jobs[i - 1][1]}'")
        if choice == 'y':
            cursor.execute(f"UPDATE job_search SET status='interested' WHERE file='{file}'")
        elif choice == 'n':
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE file='{file}'")
        else:
            print('Oops')
            exit()
        print('\n')

    print('That\'s all for now!')


if __name__ == '__main__':
    main()
