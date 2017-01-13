#!/usr/bin/env python

from __future__ import print_function

# something like openssl x509
# but when used on a gid file we show all the parts

import os
import argparse

begin = "-----BEGIN CERTIFICATE-----\n"
end   = "-----END CERTIFICATE-----"

default_openssl_options = "-noout -text"

tmpfilename = "/tmp/sfax509.pem"

def openssl_x509_string(string, openssl_options):

    if not string.startswith(begin):
        string = begin + string
    if not string.endswith(end):
        string = string + end
    with open(tmpfilename, "w") as f:
        f.write(string)

    command = "openssl x509 -in {} {}".format(tmpfilename, openssl_options)
    os.system(command)

# typically on .gids
def openssl_x509_gid(filename, openssl_options):
    with open(filename) as f:
        pem = f.read()

    # remove begins altogether
    pem = pem.replace(begin, "")
    # split along end - last item in list is '\n'
    parts = pem.split(end)[:-1]

    for part in parts:
        print("==============================")
        openssl_x509_string(part, openssl_options)
    

example = 'sfax509.py -x "-noout -dates" foo.gid'
        
def main():
    parser = argparse.ArgumentParser(usage="example: {}".format(example))
    parser.add_argument("gids", nargs='+')
    parser.add_argument("-x", "--openssl-option", action='store',
                        default=default_openssl_options, dest='openssl_options',
                        help = "options passed to openssl x509 instead of {}"
                        .format(default_openssl_options))
    args = parser.parse_args()

    for gid in args.gids:
        openssl_x509_gid(gid, openssl_options=args.openssl_options)

if __name__ == '__main__':
    main()
