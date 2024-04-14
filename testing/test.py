import os
import time

listdir = set(os.listdir('../job_descriptions'))

while True:
    time.sleep(5)
    listdir_new = set(os.listdir('../job_descriptions'))

    new = listdir_new - listdir
    for i in new:
        print(i)
    listdir = listdir_new