#!/usr/bin/env python

"""
Encrypts or decrypts single file using AES and SHA256

**Replaces eventually existing output file**

If output filename is not specified, will make it up following these rules:

   a) if encryption, will add ".enc" to end of input filename
   b) if decryption, will add ".dec" to end of input filename
"""

import os
import random
from Crypto.Cipher import AES
from Crypto.Hash import SHA256
import argparse
import sys
import a107
import a107.cryptography as ay


# default output filename
AUTO = '(auto)'


def encrypt_file(key, filename_in, filename_out):
    chunk_size = 64*1024
    file_size = bytes("{:016}".format(os.path.getsize(filename_in)), "ASCII")
    # input vector

    iv = bytes(bytearray((random.randint(0, 0xFF) for _ in range(16))))

    encryptor = AES.new(key, AES.MODE_CBC, iv)

    with open(filename_in, "rb") as infile:
        with open(filename_out, "wb") as outfile:
            outfile.write(file_size)
            outfile.write(iv)

            while True:
                chunk = infile.read(chunk_size)

                n = len(chunk)
                if n == 0:
                    break
                elif n % 16 != 0:
                    chunk += b" " * (16 - n % 16)

                outfile.write(encryptor.encrypt(chunk))


def decrypt_file(key, filename_in, filename_out):
    chunk_size = 64*1024

    with open(filename_in, "rb") as infile:
        file_size = int(infile.read(16))
        iv = infile.read(16)

        decryptor = AES.new(key, AES.MODE_CBC, iv)

        with open(filename_out, "wb") as outfile:
            while True:
                chunk = infile.read(chunk_size)

                if len(chunk) == 0:
                    break

                outfile.write(decryptor.decrypt(chunk))

            outfile.truncate(file_size)


def get_key(password):
    if isinstance(password, str):
        password = bytes(password, "UTF8")
    hasher = SHA256.new(password)
    return hasher.digest()


def make_fn_output(fn_input, fn_output, flag_encrypt):
    """See file docstring"""

    if fn_output != AUTO:
        return fn_output

    if flag_encrypt:
        fn_output = fn_input+".enc"
    else:
        fn_output = fn_input+".dec"

    return fn_output


def main(args):
    flag_encrypt = args.encrypt
    fn_output = make_fn_output(args.input, args.output, flag_encrypt)
    print("Output filename: '{}'".format(fn_output))
    key = get_key(args.password)
    if flag_encrypt:
        ay.encrypt_file(key, args.input, fn_output)
    else:
        ay.decrypt_file(key, args.input, fn_output)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)

    parser.add_argument('password', type=str, help='encryption/decryption password')
    parser.add_argument('input', type=str, help='name of file to encrypt')
    parser.add_argument('-o', '--output', help='output filename', default=AUTO)
    parser.add_argument('-e', '--encrypt', help='encrypt mode', action="store_true")
    parser.add_argument('-d', '--decrypt', help='decrypt mode', action="store_true")
    parser = argparse.ArgumentParser(description=__doc__, formatter_class=a107.SmartFormatter)

    parser.add_argument('password', type=str, help='encryption/decryption password')
    parser.add_argument('input', type=str, help='name of file to encrypt')
    parser.add_argument('-o', '--output', help='output filename', default=AUTO)
    parser.add_argument('-e', '--encrypt', help='encrypt mode', action="store_true")
    parser.add_argument('-d', '--decrypt', help='decrypt mode', action="store_true")

    args = parser.parse_args()

    if args.decrypt and args.encrypt:
        print("Please choose either encryption or decryption, not both")
        sys.exit()

    if not args.decrypt and not args.encrypt:
        print("Please choose either encryption or decryption")
        sys.exit()

    main(args)
