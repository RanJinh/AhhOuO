from socket import socket, AF_INET, SOCK_STREAM
import sys, os
from helpers import *

def extract():
    """() -> NoneType
    Opens the public key infrastructure server to extract RSA public keys.
    The public keys must have already been in the server's folder.
    """
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.bind((PKI_HOST, PKI_PORT))
        sock.listen()
        while True:
            conn, addr = sock.accept()
            with conn:
                print('PKI: connection from address', addr)
                # A, B --->
                M = conn.recv(1024)
                A, B = M.decode("UTF-8").split(',')
                file_name_A = A + ".asc"
                file_name_B = B + ".asc"
                with open(file_name_A, "r") as fileStream_A:
                    buffer_A = fileStream_A.read()
                with open(file_name_B, "r") as fileStream_B:
                    buffer_B = fileStream_B.read()
                A_pk = rsa.import_key(str.encode(buffer_A))

                # <--- {K_PB, B}(K_PA)
                data = buffer_B + "," + B
                cipher = rsa.big_encrypt(A_pk, data)
                response = b''
                for chunk in cipher:
                    response += chunk + b','
                conn.send(response[:-1])

if __name__ == "__main__":
    print("PKI: I am the Public Key Infrastructure Server!")
    print("PKI: listening for a key to be extracted")
    extract()

