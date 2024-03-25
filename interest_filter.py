import os
import sqlite3


def main():
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()

    jobs = cursor.execute("SELECT title, file, id, duplicate FROM jobs WHERE status='new'").fetchall()
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
                cursor.execute(f"UPDATE jobs SET status='new' WHERE file='{jobs[i - 1][1]}'")
                with open(f'job_descriptions/{jobs[i - 1][1]}', 'w+') as f:
                    f.write(last_file)
        if choice == 'y':
            cursor.execute(f"UPDATE jobs SET status='interested' WHERE file='{file}'")
        elif choice == 'n':
            with open(f'job_descriptions/{file}') as f:
                last_file = f.read()
            os.remove(f'job_descriptions/{file}')
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE file='{file}'")
        else:
            print('Oops')
            exit()
        connection.commit()
        print('\n')

    print('That\'s all for now!')


def get_duplicate_status(id_source, cursor):
    status = []
    for id_target in str(cursor.execute(f"SELECT duplicate FROM jobs WHERE id='{id_source}'").fetchone()[0]).split(','):
        status.append(cursor.execute(f"SELECT status FROM jobs WHERE id='{id_target}'").fetchone()[0])
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
    return '???'


if __name__ == '__main__':
    main()
