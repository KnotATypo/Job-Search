import os
import sqlite3


def main():
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()

    jobs = cursor.execute("SELECT DISTINCT(title), file FROM jobs WHERE status='new'").fetchall()
    jobs.sort(key=lambda x: x[1])
    last_file = ''
    for i, (name, file) in enumerate(jobs):
        choice = 0
        print(f'{i}/{len(jobs)}')
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


if __name__ == '__main__':
    main()
