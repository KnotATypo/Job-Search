import socket


def main():
    addr = ("localhost", 8080)
    client = socket.create_connection(addr)


    message = get_message(client)
    if message == 'end':
        pass
    else:
        choice = 0
        name, dup_status = message.split('\n')
        if dup_status != 'none':
            print('Duplicate status:', dup_status)
        while choice not in {'n', 'y'}:
            choice = input(f'{name}\nAre you interested? [y/n/undo]: ')
            choice = choice.lower()



    client.close()


def get_message(client):
    message = ''
    while (temp := client.recv(2).decode()) != '':
        message += temp
    return message


if __name__ == '__main__':
    main()
