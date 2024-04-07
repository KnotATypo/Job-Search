#!/bin/python3


#
# Complete the 'findMinimumOperations' function below.
#
# The function is expected to return an INTEGER.
# The function accepts STRING image as parameter.
#

from difflib import SequenceMatcher
from queue import PriorityQueue

def similar(a, b):
    max = len(a)
    score = 0
    for i in range(len(a)):
        if a[i] == b[i]:
            return i / max

def findMinimumOperations(image):
    return bfs(image, ''.join(reversed(image)))


def bfs(start: str, target):
    queue = PriorityQueue()
    for x in [(x, start, 1) for x in range(len(start))]:
        queue.put((similar(target, x[1]), x))

    while not queue.empty():
        i, (index, state, depth) = queue.get()
        state += state[index]
        state = state[:index] + state[index + 1:]

        if state == target:
            return depth

        for x in [(x, state, depth + 1) for x in range(len(state))]:
                queue.put((similar(target, x[1]), x))


if __name__ == '__main__':
    image = '00110101'

    result = findMinimumOperations(image)

    print(result)
