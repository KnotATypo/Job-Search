import socket


def main():
    addr = ("localhost", 8080)
    server = socket.create_server(addr)
    server.listen(5)
    client, _ = server.accept()

    client.send('Hello Server'.encode())
    client.close()


if __name__ == '__main__':
    main()
