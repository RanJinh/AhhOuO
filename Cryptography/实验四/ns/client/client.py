"""
This file represents a client who wants to transfer a file to a storage server.
"""
from socket import socket, AF_INET, SOCK_STREAM
import subprocess, sys, os
from helpers import *


NAME = "client"


def ns_authentication(sock, server_name):
    """(socket, str) -> bytes or NoneType
    Performs authentication via Needham-Schroeder public-key protocol.
    Returns a symmetric session key if authentication is successful,
    a None otherwise.

    :sock: connection to storage server
    :server_name: name of storage server
    """
    # WRITE YOUR CODE HERE!
    address = (PKI_HOST, PKI_PORT)

    # get RSA key of Client
    with open("RsaKey.asc", "r") as fileStream_A:
        buffer_A = fileStream_A.read()
    A_sk = rsa.import_key(str.encode(buffer_A))

    # get public key of file transfer server
    buffer_B = ns.get_public_key(address, server_name, NAME, A_sk)
    B_pk = rsa.import_key(buffer_B)

    # A -- {N_A, A}(K_PB) --> B
    N_A = ns.generate_nonce()
    send_data = str(N_A) + ',' + NAME
    cipher = rsa.big_encrypt(B_pk, send_data)
    send_byte = b''
    for chunk in cipher:
        send_byte += chunk + b','
    sock.send(send_byte[:-1])

    # A <-- {N_A, N_B}(K_PA) -- B
    recv_data = sock.recv(1024)
    plaintext = rsa.big_decrypt(A_sk, recv_data.split(b','))
    N_AB = plaintext.split(",")

    # check if Server actually did recieve Client's nonce
    if str(N_A) != N_AB[0]:
        return print("Nonce wrong from {}, exiting... ".format(server_name))

    # A -- {K, N_B}(K_PB) --> B
    ssn_key = aes.generate_key()
    send_data = ssn_key.decode("UTF-8") + ',' + N_AB[1]
    cipher = rsa.big_encrypt(B_pk, send_data)
    send_byte = b''
    for chunk in cipher:
        send_byte += chunk + b','
    sock.send(send_byte[:-1])

    # get confirmation
    if int(sock.recv(1024)) == RESP_VERIFIED:
        print("Client: connection verified!")
        return ssn_key
    else:
        print("Client:connection failed!")



def upload_file(sock, ssn_key, file_name):
    """(socket, bytes, str) -> NoneType

    Uploads a file to the storage server.

    :sock: connection to storage server
    :ssn_key: session key for symmetric encryption
    :file_name: name of file to upload
    """
    # read file contents
    contents = None
    with open(file_name, "r") as fileStream:
        buffer = fileStream.read()
        contents = [buffer[0+i:16+i] for i in range(0, len(buffer), 16)]
    print("Client: {} is read and ready for upload".format(file_name))

    # send signal to begin upload of contents
    request = aes.encrypt(ssn_key, SIG_START)
    sock.sendall(request)
    if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
        return print("Client: something went wrong with file transfer, exiting...")
    print("Client: beginning file upload...")

    # upload file contents
    for i, content in enumerate(contents):
        request = aes.encrypt(ssn_key, content)
        sock.sendall(request)
        if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
            return print("Client: something went wrong with file transfer, exiting...")
        print("Client: uploading file... ({}/{})".format(i+1, len(contents)))

    # send signal that upload is complete
    request = aes.encrypt(ssn_key, SIG_END)
    sock.sendall(request)
    if aes.decrypt(ssn_key, sock.recv(1024)) != SIG_GOOD:
        return print("Client: something went wrong with file transfer, exiting...")
    print("Client: successful upload for {}".format(file_name))


def download_file(sock, ssn_key, file_name):
    """(socket, bytes, str) -> NoneType

    Downloads a file to the storage server.

    :sock: connection to storage server
    :ssn_key: session key for symmetric encryption
    :file_name: name of file to download
    """
    # send signal to begin download
    request = aes.encrypt(ssn_key, SIG_START)
    sock.sendall(request)
    print("Client: beginning download for {}...".format(file_name))

    # get file contents from client
    contents = list()
    completed_upload = False
    request = aes.encrypt(ssn_key, SIG_GOOD)
    while not completed_upload:
        response = aes.decrypt(ssn_key, sock.recv(1024))
        if response == SIG_END:
            completed_upload = True
            print("Client: completed download for {}".format(file_name))
        else:
            contents.append(response)
        sock.sendall(request)

    # save file to current folder
    with open(file_name, "w") as outputStream:
        outputStream.write(''.join(contents))
    print("Client: file saved in {}".format(file_name))


def communicate_storage(server_name, file_name, mode):
    """(str, str, str) -> NoneType

    Communicates with the storage server to upload or download a file with the given name.

    :file_name: name of file to upload or download

    REQ: if server_name == server, server.py is running
    REQ: if server_name == adversary, server.py and adversary.py are running
    """
    # if mode is upload, check if file exists
    if mode == UPLOAD and not os.path.isfile(file_name):
        return print("Client: file {} does not exist".format(file_name))

    # get connection details of storage server
    address = None
    if server_name == "server":
        address = (SERVER_HOST, SERVER_PORT)
    elif server_name == "adversary":
        address = (ADV_HOST, ADV_PORT)
    else:
        return print("Client: not a valid file storage server!")

    # begin communication with Server
    with socket(AF_INET, SOCK_STREAM) as sock:
        sock.connect(address)
        # go through NS protocol, get session key
        ssn_key = ns_authentication(sock, server_name)

        # if connection is not verified, exit
        if not ssn_key:
            return print("Client: something went wrong with authentication, exiting...")
        print("Client: using session key {}".format(ssn_key))

        # send over file name and mode of transfer
        request = "{},{}".format(file_name, mode)
        sock.sendall(aes.encrypt(ssn_key, request))
        print("Client: sent file name {} for mode {}".format(file_name, mode))

        response = aes.decrypt(ssn_key, sock.recv(1024))
        if response == SIG_BAD and mode == DOWNLOAD:
            return print("Client: {} does not exist in server, exiting...".format(file_name))
        elif response != SIG_GOOD:
            return print("Client: something went wrong with file transfer, exiting...")

        # upload or download file from server
        if mode == UPLOAD:
            upload_file(sock, ssn_key, file_name)
        elif mode == DOWNLOAD:
            download_file(sock, ssn_key, file_name)

    print("Client: client shutting down...")


if __name__ == "__main__":
    import getopt
    def usage():
        print ('Usage:    ' + os.path.basename(__file__) + ' options input_file')
        print ('Options:')
        print ('\t -s server_name, --server=server_name')
        print ('\t -u, --upload')
        print ('\t -d, --download')
        sys.exit(2)
    try:
        opts, args = getopt.getopt(sys.argv[1:], "hs:ud", ["help", "server=", "upload", "download"])
        if not opts:
            raise getopt.GetoptError("Enter an option")
    except getopt.GetoptError as err:
        print(err)
        usage()
    # extract parameters
    mode = None
    host_name = None
    input_file = args[0] if len(args) > 0 else None
    for opt, arg in opts:
        if opt in ("-h", "--help"):
            usage()
        elif opt in ("-s", "--server"):
            host_name = arg
        elif opt in ("-d", "--download"):
            mode = "d"
        elif opt in ("-u", "--upload"):
            mode = "u"
    # check arguments
    if host_name is None:
        print('host name option is missing\n')
        usage()
    if input_file is None:
        print('input file is missing\n')
        usage()
    if mode is None:
        print('select a mode: [u,d]\n')
        usage()        
    # run the command
    communicate_storage(host_name, input_file, mode)
