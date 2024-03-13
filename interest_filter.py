import sqlite3
import os

from tqdm import tqdm

def main():
    connection = sqlite3.connect('jobs.db')
    cursor = connection.cursor()

    jobs = cursor.execute("SELECT DISTINCT(title), file FROM jobs WHERE status='new'").fetchall()
    jobs.sort(key=lambda x: x[1])
    last_file = ''
    for i, (name, file) in tqdm(enumerate(jobs)):
        choice = 0
        while choice not in {'n', 'y', 'undo'}:
            choice = input(f'\n{name}\nAre you interested? [y/n/undo]: ')
            choice = choice.lower()
            if choice == 'undo':
                cursor.execute(f"UPDATE jobs SET status='new' WHERE file='{jobs[i - 1][1]}'")
                with open(f'job_descriptions/{jobs[i - 1][1]}', 'w+') as f:
                    f.write(last_file)
        if choice == 'y':
            cursor.execute(f"UPDATE jobs SET status='interested' WHERE title='{name}'")
        elif choice == 'n':
            with open(f'job_descriptions/{file}') as f:
                last_file = f.read()
            os.remove(f'job_descriptions/{file}')
            cursor.execute(f"UPDATE jobs SET status='not_interested' WHERE title='{name}'")
        else:
            print('Oops')
            exit()
        connection.commit()
        print('\n')

    print('That\'s all for now!')


if __name__ == '__main__':
    main()
