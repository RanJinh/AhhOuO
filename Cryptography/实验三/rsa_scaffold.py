
import math
import random
import gmpy2

def fastExpMod(b, e, m):
    result = 1
    e = int(e)
    while e != 0:
        if e % 2 != 0:
            e -= 1
            result = (result * b) % m
        e >>= 1
        b = (b * b) % m
    return result

def ext_gcd(a, b):
    if b == 0:
        return 1, 0
    else:
        x, y = ext_gcd(b, a % b)
        x, y = y, (x - (a // b) * y)
        return x, y

def multiplicative_inverse(e, phi):
    '''
    extended Euclid's algorithm for finding the multiplicative inverse 
    '''
    # WRITE YOUR CODE HERE!
    x, y = ext_gcd(phi, e)
    if y < 0:
        return y + phi
    return y

def selectE(euler_totient):
    while True:
        # e and fn are relatively prime
        e = random.randint(0, euler_totient)
        if math.gcd(e, euler_totient) == 1:
            return e

def key_generation(p, q):
    # WRITE YOUR CODE HERE!
    n = p * q
    phi = (p - 1) * (q - 1)
    e = selectE(phi)
    d = multiplicative_inverse(e, phi)
    return n, e, d

def encrypt(pk, plaintext):
    # WRITE YOUR CODE HERE!
    n, e = pk
    res = 1
    tmp = plaintext
    while e:
        if e & 0x1:
            res = res * tmp % n
        tmp = tmp * tmp % n
        e >>= 1
    return res

def decrypt(sk, ciphertext):
    # WRITE YOUR CODE HERE!
    n, d = sk
    res = 1
    tmp = ciphertext
    while d:
        if d & 0x1:
            res = res * tmp % n
        tmp = tmp * tmp % n
        d >>= 1
    return res

def bytes2num(b):
    s='0x'
    for x in b:
        tmp=str(hex(x))[2:]
        if len(tmp)==2:
            pass
        else:
            tmp='0'+tmp
        s+=tmp
        num=int(s,16)
    return num

def num2str(n):
    tmp=str(hex(n))[2:]
    if len(tmp)%2==0:
        pass
    else:
        tmp='0'+tmp
    s=''
    for i in range(0,len(tmp),2):
        temp=tmp[i]+tmp[i+1]
        s+=chr(int(temp,16))
    return s

if __name__ == '__main__':
    n = "0xC2636AE5C3D8E43FFB97AB09028F1AAC6C0BF6CD3D70EBCA281BFFE97FBE30DD"
    n = int(n, 16)
    e = 65537
    p, q = 275127860351348928173285174381581152299, 319576316814478949870590164193048041239
    phi_n = (p - 1) * (q - 1)
    d = multiplicative_inverse(e, phi_n)
    fi = open('secret.enc', 'rb')
    cipher = fi.read()
    cipher = bytes2num(cipher)
    fi.close()
    std_plaintext = pow(cipher, d, n)
    plaintext = decrypt((n, d), cipher)
    if std_plaintext == plaintext:
        print("解密正确！")
    cipher2 = encrypt((n, e), plaintext)
    if cipher == cipher2:
        print("加密正确！")
    print(num2str(plaintext))
