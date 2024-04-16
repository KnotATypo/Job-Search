import os

import psycopg2


def main():
    connection = psycopg2.connect(database="monitoring", host="monitoring.lan", user="job_search", password="jobs")
    connection.autocommit = True
    cursor = connection.cursor()

    cursor.execute("SELECT title, file, id, duplicate FROM job_search WHERE status='new'")
    jobs = cursor.fetchall()

    jobs.sort(key=lambda x: x[1])
    last_file = ''
    for i, (name, file, id, duplicate) in enumerate(jobs):
        choice = 0
        print(f'{i}/{len(jobs)}')
        if duplicate is not None:
            dup_status = get_duplicate_status(id, cursor)
            print('Duplicate status:', dup_status)
        while choice not in {'n', 'y'}:
            choice = input(f'{name}\nAre you interested? [y/n/undo]: ')
            choice = choice.lower()
            if choice == 'undo':
                cursor.execute(f"UPDATE job_search SET status='new' WHERE file='{jobs[i - 1][1]}'")
                with open(f'job_descriptions/{jobs[i - 1][1]}', 'w+') as f:
                    f.write(last_file)
        if choice == 'y':
            cursor.execute(f"UPDATE job_search SET status='interested' WHERE file='{file}'")
        elif choice == 'n':
            with open(f'job_descriptions/{file}') as f:
                last_file = f.read()
            os.remove(f'job_descriptions/{file}')
            cursor.execute(f"UPDATE job_search SET status='not_interested' WHERE file='{file}'")
        else:
            print('Oops')
            exit()
        print('\n')

    print('That\'s all for now!')


def get_duplicate_status(id_source, cursor):
    status = []
    cursor.execute(f"SELECT duplicate FROM job_search WHERE id='{id_source}'")
    for id_target in str(cursor.fetchone()[0]).split(','):
        cursor.execute(f"SELECT status FROM job_search WHERE id='{id_target}'")
        status.append(cursor.fetchone()[0])
    if 'applied' in status:
        return 'applied'
    if 'easy_filter' in status:
        return 'easy_filter'
    if 'interested_read' in status:
        return 'interested_read'
    if 'interested' in status:
        return 'interested'
    if all([x == 'not_interested' for x in status]):
        return 'not_interested'
    if all([x == 'new' for x in status]):
        return 'new'
    return '???'


if __name__ == '__main__':
    main()
