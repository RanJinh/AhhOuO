"""
This file represents a simple file storage server.
"""
from socket import socket, AF_INET, SOCK_STREAM
import subprocess, sys, os
from helpers import *


NAME = "server"


def ns_authentication(conn):
    """(socket, str) -> bytes or NoneType
    Performs authentication via Needham-Schroeder public-key protocol.
    Returns a symmetric session key and client's name if authentication
    is successful, a None otherwise.

    :sock: connection to storage server
    :NAME: name of storage server
    """
    # WRITE YOUR CODE HERE!
    # get RSA key of Server for decrypting
    address = (PKI_HOST, PKI_PORT)
    with open("RsaKey.asc", "r") as fileStream_B:
        server_key_byte = fileStream_B.read()
    server_sk = rsa.import_key(str.encode(server_key_byte))

    # A -- {N_A, A}(K_PB) --> B
    recv_data = conn.recv(1024)
    plaintext = rsa.big_decrypt(server_sk, recv_data.split(b','))
    N_A, client_name = plaintext.split(",")
    N_B = ns.generate_nonce()
    send_data = str(N_A) + ',' + str(N_B)

    # get client's public key
    client_pk_byte = ns.get_public_key(address, client_name, NAME, server_sk)
    client_pk = rsa.import_key(client_pk_byte)

    # A <-- {N_A, N_B} -- B
    cipher = rsa.big_encrypt(client_pk, send_data)
    send_byte = b''
    for chunk in cipher:
        send_byte += chunk + b','
    conn.send(send_byte[:-1])

    # A -- {K, N_B} --> B
    recv_data = conn.recv(1024)
    plaintext = rsa.big_decrypt(server_sk, recv_data.split(b','))
    ssn_key, N_B_recv = plaintext.split(",")

    # check if client did actually recieve Server's nonce
    if N_B_recv != str(N_B):
        conn.send(str(RESP_DENIED).encode("UTF-8"))
        return print("Nonce wrong from", client_name)
    conn.send(str(RESP_VERIFIED).encode("UTF-8"))
    print("Server: connection verified!")
    return bytes(ssn_key, "utf-8"), client_name


 

def serve_upload(conn, ssn_key, file_name, client_name):
    """(socket, bytes, str, str) -> NoneType

    Downloads the file for the client is uploading.

    :conn: connection to client
    :ssn_key: session key for symmetric encryption
    :file_name: name of file to upload
    :client_name: name of client
    """
    # get signal to begin upload
    request = aes.decrypt(ssn_key, conn.recv(1024))
    if request != SIG_START:
        conn.sendall(aes.encrypt(ssn_key, SIG_BAD))
        return print("Server: something went wrong with file transfer")
    response = aes.encrypt(ssn_key, SIG_GOOD)
    conn.sendall(response)
    print("Server: beginning transfer for {}...".format(file_name))

    # get file contents from client
    contents = list()
    completed_upload = False
    response = aes.encrypt(ssn_key, SIG_GOOD)
    while not completed_upload:
        request = aes.decrypt(ssn_key, conn.recv(1024))
        if request == SIG_END:
            completed_upload = True
            print("Server: completed transfer for {}".format(file_name))
        else:
            contents.append(request)
        conn.sendall(response)

    # save file to server folder
    file_path = "{}/{}".format(client_name, file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as outputStream:
        outputStream.write(''.join(contents))
    print("Server: file saved in {}".format(file_path))


def serve_download(conn, ssn_key, file_name, client_name):
    """(socket, bytes, str, str) -> NoneType

    Uploads the file for the client is downloading.

    :conn: connection to client
    :ssn_key: session key for symmetric encryption
    :file_name: name of file to download
    :client_name: name of client
    """
    # read file contents
    file_path = "{}/{}".format(client_name, file_name)
    contents = None
    with open(file_path, "r") as fileStream:
        buffer = fileStream.read()
        contents = [buffer[0+i:16+i] for i in range(0, len(buffer), 16)]
    # get signal to begin download
    request = aes.decrypt(ssn_key, conn.recv(1024))
    if request != SIG_START:
        conn.sendall(aes.encrypt(ssn_key, SIG_BAD))
        return print("Server: something went wrong with file transfer")
    print("Server: beginning transfer for {}...".format(file_name))
    # upload file contents to client
    for i, content in enumerate(contents):
        response = aes.encrypt(ssn_key, content)
        conn.sendall(response)
        if aes.decrypt(ssn_key, conn.recv(1024)) != SIG_GOOD:
            return print("Server: something went wrong with file transfer, exiting...")
        print("Server: transferring file... ({}/{})".format(i+1, len(contents)))
    # send signal that transfer is complete
    request = aes.encrypt(ssn_key, SIG_END)
    conn.sendall(request)
    if aes.decrypt(ssn_key, conn.recv(1024)) != SIG_GOOD:
        return print("Server: something went wrong with file transfer, exiting...")
    print("Server: successful upload for {}".format(file_name))


def serve_client():
    """() -> NoneType

    Communicates with the client by first ensuring mutual authentication via the Needham-Schroeder
    protocol, then securely transfer the file between the client and server.
    """
    # begin to serve client
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.bind((SERVER_HOST, SERVER_PORT))
        sock.listen()
        conn, addr = sock.accept()
        with conn:
            print('Server: connection from client with address', addr)
            while True:
                # get session key and client name from NS auth
                ssn_key = client_name = None
                result = ns_authentication(conn)
                if result:
                    ssn_key, client_name = result
                else:
                    return print("Server: something went wrong with authentication, exiting...")
                print("Server: using session key {} from client {}".format(ssn_key, client_name))
                # get file name and mode of transfer
                request = aes.decrypt(ssn_key, conn.recv(1024))
                file_name, mode = request.split(',')
                response = aes.encrypt(ssn_key, SIG_GOOD)
                print("Server: recieved request of file {} for mode {}".format(file_name, mode))

                # serve to upload or download the file
                if mode == UPLOAD:
                    conn.sendall(response)
                    serve_upload(conn, ssn_key, file_name, client_name)

                # if download, check if file exists
                elif mode == DOWNLOAD:
                    file_path = "{}/{}".format(client_name, file_name)
                    if os.path.isfile(file_path):
                        conn.sendall(response)
                        serve_download(conn, ssn_key, file_name, client_name)
                    else:
                        response = aes.encrypt(ssn_key, SIG_BAD)
                        conn.sendall(response)
                        return print("Server: {} does not exist in server, exiting...".format(file_name))
                # done, stop server
                return print("Server: transfer complete, shutting down...")
    

if __name__ == "__main__":
    print("Server: storage server")
    print("Server: beginning to serve clients...")
    serve_client()
