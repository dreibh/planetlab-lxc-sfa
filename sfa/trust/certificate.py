# ----------------------------------------------------------------------
# Copyright (c) 2008 Board of Trustees, Princeton University
#
# Permission is hereby granted, free of charge, to any person obtaining
# a copy of this software and/or hardware specification (the "Work") to
# deal in the Work without restriction, including without limitation the
# rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Work, and to permit persons to whom the Work
# is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be
# included in all copies or substantial portions of the Work.
#
# THE WORK IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS
# OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF
# MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND
# NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS OR COPYRIGHT
# HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY,
# WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE WORK OR THE USE OR OTHER DEALINGS
# IN THE WORK.
# ----------------------------------------------------------------------

#
# SFA uses two crypto libraries: pyOpenSSL and M2Crypto to implement
# the necessary crypto functionality. Ideally just one of these libraries
# would be used, but unfortunately each of these libraries is independently
# lacking. The pyOpenSSL library is missing many necessary functions, and
# the M2Crypto library has crashed inside of some of the functions. The
# design decision is to use pyOpenSSL whenever possible as it seems more
# stable, and only use M2Crypto for those functions that are not possible
# in pyOpenSSL.
#
# This module exports two classes: Keypair and Certificate.
##
#

# Notes on using the openssl command line
#
# for verifying the chain in a gid,
# assuming it is split into pieces p1.pem p2.pem p3.pem
# you can use openssl to verify the chain using this command
# openssl verify -verbose -CAfile <(cat p2.pem p3.pem) p1.pem
# also you can use sfax509 to invoke openssl x509 on all parts of the gid
#




import functools
import os
import tempfile
import base64
from tempfile import mkstemp

import OpenSSL
# M2Crypto is imported on the fly to minimize crashes
# import M2Crypto

from sfa.util.faults import (CertExpired, CertMissingParent,
                             CertNotSignedByParent)
from sfa.util.sfalogging import logger

# this tends to generate quite some logs for little or no value
debug_verify_chain = True

glo_passphrase_callback = None

##
# A global callback may be implemented for requesting passphrases from the
# user. The function will be called with three arguments:
#
#    keypair_obj: the keypair object that is calling the passphrase
#    string: the string containing the private key that's being loaded
#    x: unknown, appears to be 0, comes from pyOpenSSL and/or m2crypto
#
# The callback should return a string containing the passphrase.


def set_passphrase_callback(callback_func):
    global glo_passphrase_callback

    glo_passphrase_callback = callback_func

##
# Sets a fixed passphrase.


def set_passphrase(passphrase):
    set_passphrase_callback(lambda k, s, x: passphrase)

##
# Check to see if a passphrase works for a particular private key string.
# Intended to be used by passphrase callbacks for input validation.


def test_passphrase(string, passphrase):
    try:
        OpenSSL.crypto.load_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, string, (lambda x: passphrase))
        return True
    except:
        return False


def convert_public_key(key):
    keyconvert_path = "/usr/bin/keyconvert.py"
    if not os.path.isfile(keyconvert_path):
        raise IOError(
            "Could not find keyconvert in {}".format(keyconvert_path))

    # we can only convert rsa keys
    if "ssh-dss" in key:
        raise Exception("keyconvert: dss keys are not supported")

    (ssh_f, ssh_fn) = tempfile.mkstemp()
    ssl_fn = tempfile.mktemp()
    os.write(ssh_f, key.encode())
    os.close(ssh_f)

    cmd = keyconvert_path + " " + ssh_fn + " " + ssl_fn
    os.system(cmd)

    # this check leaves the temporary file containing the public key so
    # that it can be expected to see why it failed.
    # TODO: for production, cleanup the temporary files
    if not os.path.exists(ssl_fn):
        raise Exception(
            "generated certificate not found. keyconvert may have failed.")

    k = Keypair()
    try:
        k.load_pubkey_from_file(ssl_fn)
        return k
    except:
        logger.log_exc("convert_public_key caught exception")
        raise
    finally:
        # remove the temporary files
        if os.path.exists(ssh_fn):
            os.remove(ssh_fn)
        if os.path.exists(ssl_fn):
            os.remove(ssl_fn)

##
# Public-private key pairs are implemented by the Keypair class.
# A Keypair object may represent both a public and private key pair, or it
# may represent only a public key (this usage is consistent with OpenSSL).


class Keypair:
    key = None       # public/private keypair
    m2key = None     # public key (m2crypto format)

    ##
    # Creates a Keypair object
    # @param create If create==True, creates a new public/private key and
    #     stores it in the object
    # @param string If string != None, load the keypair from the string (PEM)
    # @param filename If filename != None, load the keypair from the file

    def __init__(self, create=False, string=None, filename=None):
        if create:
            self.create()
        if string:
            self.load_from_string(string)
        if filename:
            self.load_from_file(filename)

    ##
    # Create a RSA public/private key pair and store it inside the keypair
    # object

    def create(self):
        self.key = OpenSSL.crypto.PKey()
        self.key.generate_key(OpenSSL.crypto.TYPE_RSA, 2048)

    ##
    # Save the private key to a file
    # @param filename name of file to store the keypair in

    def save_to_file(self, filename):
        with open(filename, 'wb') as output:
            output.write(self.as_pem())
        self.filename = filename

    ##
    # Load the private key from a file. Implicity the private key includes the
    # public key.

    def load_from_file(self, filename):
        self.filename = filename
        buffer = open(filename, 'r').read()
        self.load_from_string(buffer)

    ##
    # Load the private key from a string. Implicitly the private key includes
    # the public key.

    def load_from_string(self, string):
        import M2Crypto
        if glo_passphrase_callback:
            self.key = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM, string,
                functools.partial(glo_passphrase_callback, self, string))
            self.m2key = M2Crypto.EVP.load_key_string(
                string.encode(encoding="utf-8"),
                functools.partial(glo_passphrase_callback, self, string))
        else:
            self.key = OpenSSL.crypto.load_privatekey(
                OpenSSL.crypto.FILETYPE_PEM, string)
            self.m2key = M2Crypto.EVP.load_key_string(
                string.encode(encoding="utf-8"))

    ##
    #  Load the public key from a string. No private key is loaded.

    def load_pubkey_from_file(self, filename):
        import M2Crypto
        # load the m2 public key
        m2rsakey = M2Crypto.RSA.load_pub_key(filename)
        self.m2key = M2Crypto.EVP.PKey()
        self.m2key.assign_rsa(m2rsakey)

        # create an m2 x509 cert
        m2name = M2Crypto.X509.X509_Name()
        m2name.add_entry_by_txt(field="CN", type=0x1001,
                                entry="junk", len=-1, loc=-1, set=0)
        m2x509 = M2Crypto.X509.X509()
        m2x509.set_pubkey(self.m2key)
        m2x509.set_serial_number(0)
        m2x509.set_issuer_name(m2name)
        m2x509.set_subject_name(m2name)
        ASN1 = M2Crypto.ASN1.ASN1_UTCTIME()
        ASN1.set_time(500)
        m2x509.set_not_before(ASN1)
        m2x509.set_not_after(ASN1)
        # x509v3 so it can have extensions
        # prob not necc since this cert itself is junk but still...
        m2x509.set_version(2)
        junk_key = Keypair(create=True)
        m2x509.sign(pkey=junk_key.get_m2_pubkey(), md="sha1")

        # convert the m2 x509 cert to a pyopenssl x509
        m2pem = m2x509.as_pem()
        pyx509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, m2pem)

        # get the pyopenssl pkey from the pyopenssl x509
        self.key = pyx509.get_pubkey()
        self.filename = filename

    ##
    # Load the public key from a string. No private key is loaded.

    def load_pubkey_from_string(self, string):
        (f, fn) = tempfile.mkstemp()
        os.write(f, string)
        os.close(f)
        self.load_pubkey_from_file(fn)
        os.remove(fn)

    ##
    # Return the private key in PEM format.

    def as_pem(self):
        return OpenSSL.crypto.dump_privatekey(
            OpenSSL.crypto.FILETYPE_PEM, self.key)

    ##
    # Return an M2Crypto key object

    def get_m2_pubkey(self):
        import M2Crypto
        if not self.m2key:
            self.m2key = M2Crypto.EVP.load_key_string(self.as_pem())
        return self.m2key

    ##
    # Returns a string containing the public key represented by this object.

    def get_pubkey_string(self):
        m2pkey = self.get_m2_pubkey()
        return base64.b64encode(m2pkey.as_der())

    ##
    # Return an OpenSSL pkey object

    def get_openssl_pkey(self):
        return self.key

    ##
    # Given another Keypair object, return TRUE if the two keys are the same.

    def is_same(self, pkey):
        return self.as_pem() == pkey.as_pem()

    def sign_string(self, data):
        k = self.get_m2_pubkey()
        k.sign_init()
        k.sign_update(data)
        return base64.b64encode(k.sign_final())

    def verify_string(self, data, sig):
        import M2Crypto
        k = self.get_m2_pubkey()
        k.verify_init()
        k.verify_update(data)
        return M2Crypto.m2.verify_final(k.ctx, base64.b64decode(sig), k.pkey)

    def compute_hash(self, value):
        return self.sign_string(str(value))

    # only informative
    def get_filename(self):
        return getattr(self, 'filename', None)

    def dump(self, *args, **kwargs):
        print(self.dump_string(*args, **kwargs))

    def dump_string(self):
        result = ""
        result += "KEYPAIR: pubkey={:>40}...".format(self.get_pubkey_string())
        filename = self.get_filename()
        if filename:
            result += "Filename {}\n".format(filename)
        return result

##
# The certificate class implements a general purpose X509 certificate, making
# use of the appropriate pyOpenSSL or M2Crypto abstractions. It also adds
# several addition features, such as the ability to maintain a chain of
# parent certificates, and storage of application-specific data.
#
# Certificates include the ability to maintain a chain of parents. Each
# certificate includes a pointer to it's parent certificate. When loaded
# from a file or a string, the parent chain will be automatically loaded.
# When saving a certificate to a file or a string, the caller can choose
# whether to save the parent certificates as well.


class Certificate:
    digest = "sha256"

#    x509 = None
#    issuerKey = None
#    issuerSubject = None
#    parent = None
    isCA = None  # will be a boolean once set

    separator = "-----parent-----"

    ##
    # Create a certificate object.
    #
    # @param lifeDays life of cert in days - default is 1825==5 years
    # @param create If create==True, then also create a blank X509 certificate.
    # @param subject If subject!=None, then create a blank certificate and set
    #     it's subject name.
    # @param string If string!=None, load the certificate from the string.
    # @param filename If filename!=None, load the certificate from the file.
    # @param isCA If !=None, set whether this cert is for a CA

    def __init__(self, lifeDays=1825, create=False, subject=None, string=None,
                 filename=None, isCA=None):
        # these used to be defined in the class !
        self.x509 = None
        self.issuerKey = None
        self.issuerSubject = None
        self.parent = None

        self.data = {}
        if create or subject:
            self.create(lifeDays)
        if subject:
            self.set_subject(subject)
        if string:
            self.load_from_string(string)
        if filename:
            self.load_from_file(filename)

        # Set the CA bit if a value was supplied
        if isCA is not None:
            self.set_is_ca(isCA)

    # Create a blank X509 certificate and store it in this object.

    def create(self, lifeDays=1825):
        self.x509 = OpenSSL.crypto.X509()
        # FIXME: Use different serial #s
        self.x509.set_serial_number(3)
        self.x509.gmtime_adj_notBefore(0)  # 0 means now
        self.x509.gmtime_adj_notAfter(
            lifeDays * 60 * 60 * 24)  # five years is default
        self.x509.set_version(2)  # x509v3 so it can have extensions

    ##
    # Given a pyOpenSSL X509 object, store that object inside of this
    # certificate object.

    def load_from_pyopenssl_x509(self, x509):
        self.x509 = x509

    ##
    # Load the certificate from a string

    def load_from_string(self, string):
        # if it is a chain of multiple certs, then split off the first one and
        # load it (support for the ---parent--- tag as well as normal chained
        # certs)

        if string is None or string.strip() == "":
            logger.warning("Empty string in load_from_string")
            return

        string = string.strip()

        # If it's not in proper PEM format, wrap it
        if string.count('-----BEGIN CERTIFICATE') == 0:
            string = '-----BEGIN CERTIFICATE-----'\
                     '\n{}\n-----END CERTIFICATE-----'\
                     .format(string)

        # If there is a PEM cert in there, but there is some other text first
        # such as the text of the certificate, skip the text
        beg = string.find('-----BEGIN CERTIFICATE')
        if beg > 0:
            # skipping over non cert beginning
            string = string[beg:]

        parts = []

        if string.count('-----BEGIN CERTIFICATE-----') > 1 and \
                string.count(Certificate.separator) == 0:
            parts = string.split('-----END CERTIFICATE-----', 1)
            parts[0] += '-----END CERTIFICATE-----'
        else:
            parts = string.split(Certificate.separator, 1)

        self.x509 = OpenSSL.crypto.load_certificate(
            OpenSSL.crypto.FILETYPE_PEM, parts[0])

        if self.x509 is None:
            logger.warning(
                "Loaded from string but cert is None: {}".format(string))

        # if there are more certs, then create a parent and let the parent load
        # itself from the remainder of the string
        if len(parts) > 1 and parts[1] != '':
            self.parent = self.__class__()
            self.parent.load_from_string(parts[1])

    ##
    # Load the certificate from a file

    def load_from_file(self, filename):
        file = open(filename)
        string = file.read()
        self.load_from_string(string)
        self.filename = filename

    ##
    # Save the certificate to a string.
    #
    # @param save_parents If save_parents==True,
    # then also save the parent certificates.

    def save_to_string(self, save_parents=True):
        if self.x509 is None:
            logger.warning("None cert in certificate.save_to_string")
            return ""
        string = OpenSSL.crypto.dump_certificate(
            OpenSSL.crypto.FILETYPE_PEM, self.x509)
        if isinstance(string, bytes):
            string = string.decode()
        if save_parents and self.parent:
            string = string + self.parent.save_to_string(save_parents)
        return string

    ##
    # Save the certificate to a file.
    # @param save_parents If save_parents==True,
    #  then also save the parent certificates.

    def save_to_file(self, filename, save_parents=True, filep=None):
        string = self.save_to_string(save_parents=save_parents)
        if filep:
            f = filep
        else:
            f = open(filename, 'w')
        if isinstance(string, bytes):
            string = string.decode()
        f.write(string)
        f.close()
        self.filename = filename

    ##
    # Save the certificate to a random file in /tmp/
    # @param save_parents If save_parents==True,
    #  then also save the parent certificates.
    def save_to_random_tmp_file(self, save_parents=True):
        fp, filename = mkstemp(suffix='cert', text=True)
        fp = os.fdopen(fp, "w")
        self.save_to_file(filename, save_parents=True, filep=fp)
        return filename

    ##
    # Sets the issuer private key and name
    # @param key Keypair object containing the private key of the issuer
    # @param subject String containing the name of the issuer
    # @param cert (optional)
    #  Certificate object containing the name of the issuer

    def set_issuer(self, key, subject=None, cert=None):
        self.issuerKey = key
        if subject:
            # it's a mistake to use subject and cert params at the same time
            assert(not cert)
            if isinstance(subject, dict) or isinstance(subject, str):
                req = OpenSSL.crypto.X509Req()
                reqSubject = req.get_subject()
                if isinstance(subject, dict):
                    for key in list(reqSubject.keys()):
                        setattr(reqSubject, key, subject[key])
                else:
                    setattr(reqSubject, "CN", subject)
                subject = reqSubject
                # subject is not valid once req is out of scope, so save req
                self.issuerReq = req
        if cert:
            # if a cert was supplied, then get the subject from the cert
            subject = cert.x509.get_subject()
        assert(subject)
        self.issuerSubject = subject

    ##
    # Get the issuer name

    def get_issuer(self, which="CN"):
        x = self.x509.get_issuer()
        return getattr(x, which)

    ##
    # Set the subject name of the certificate

    def set_subject(self, name):
        req = OpenSSL.crypto.X509Req()
        subj = req.get_subject()
        if isinstance(name, dict):
            for key in list(name.keys()):
                setattr(subj, key, name[key])
        else:
            setattr(subj, "CN", name)
        self.x509.set_subject(subj)

    ##
    # Get the subject name of the certificate

    def get_subject(self, which="CN"):
        x = self.x509.get_subject()
        return getattr(x, which)

    ##
    # Get a pretty-print subject name of the certificate
    # let's try to make this a little more usable as is makes logs hairy
    # FIXME: Consider adding 'urn:publicid' and 'uuid' back for GENI?
    pretty_fields = ['email']

    def filter_chunk(self, chunk):
        for field in self.pretty_fields:
            if field in chunk:
                return " " + chunk

    def pretty_cert(self):
        message = "[Cert."
        x = self.x509.get_subject()
        ou = getattr(x, "OU")
        if ou:
            message += " OU: {}".format(ou)
        cn = getattr(x, "CN")
        if cn:
            message += " CN: {}".format(cn)
        data = self.get_data(field='subjectAltName')
        if data:
            message += " SubjectAltName:"
            filtered = [self.filter_chunk(chunk) for chunk in data.split()]
            message += " ".join([f for f in filtered if f])
            omitted = len([f for f in filtered if not f])
            if omitted:
                message += "..+{} omitted".format(omitted)
        message += "]"
        return message

    def pretty_chain(self):
        message = "{}".format(self.x509.get_subject())
        parent = self.parent
        while parent:
            message += "->{}".format(parent.x509.get_subject())
            parent = parent.parent
        return message

    def pretty_name(self):
        return self.get_filename() or self.pretty_chain()

    ##
    # Get the public key of the certificate.
    #
    # @param key Keypair object containing the public key

    def set_pubkey(self, key):
        assert(isinstance(key, Keypair))
        self.x509.set_pubkey(key.get_openssl_pkey())

    ##
    # Get the public key of the certificate.
    # It is returned in the form of a Keypair object.

    def get_pubkey(self):
        import M2Crypto
        m2x509 = M2Crypto.X509.load_cert_string(self.save_to_string())
        pkey = Keypair()
        pkey.key = self.x509.get_pubkey()
        pkey.m2key = m2x509.get_pubkey()
        return pkey

    def set_intermediate_ca(self, val):
        return self.set_is_ca(val)

    # Set whether this cert is for a CA.
    # All signers and only signers should be CAs.
    # The local member starts unset, letting us check that you only set it once
    # @param val Boolean indicating whether this cert is for a CA
    def set_is_ca(self, val):
        if val is None:
            return

        if self.isCA is not None:
            # Can't double set properties
            raise Exception(
                "Cannot set basicConstraints CA:?? more than once. "
                "Was {}, trying to set as {}".format(self.isCA, val))

        self.isCA = val
        if val:
            self.add_extension('basicConstraints', 1, 'CA:TRUE')
        else:
            self.add_extension('basicConstraints', 1, 'CA:FALSE')

    ##
    # Add an X509 extension to the certificate. Add_extension can only
    # be called once for a particular extension name, due to
    # limitations in the underlying library.
    #
    # @param name string containing name of extension
    # @param value string containing value of the extension

    def add_extension(self, name, critical, value):
        oldExtVal = None
        try:
            oldExtVal = self.get_extension(name)
        except:
            # M2Crypto LookupError when the extension isn't there (yet)
            pass

        # This code limits you from adding the extension with the same value
        # The method comment says you shouldn't do this with the same name
        # But actually it (m2crypto) appears to allow you to do this.
        if oldExtVal and oldExtVal == value:
            # don't add this extension again
            # just do nothing as here
            return
        # FIXME: What if they are trying to set with a different value?
        # Is this ever OK? Or should we raise an exception?
#        elif oldExtVal:
#            raise "Cannot add extension {} which had val {} with new val {}"\
#                  .format(name, oldExtVal, value)

        if isinstance(name, str):
            name = name.encode()
        if isinstance(value, str):
            value = value.encode()

        ext = OpenSSL.crypto.X509Extension(name, critical, value)
        self.x509.add_extensions([ext])

    ##
    # Get an X509 extension from the certificate

    def get_extension(self, name):

        import M2Crypto
        if name is None:
            return None

        certstr = self.save_to_string()
        if certstr is None or certstr == "":
            return None
        # pyOpenSSL does not have a way to get extensions
        m2x509 = M2Crypto.X509.load_cert_string(certstr)
        if m2x509 is None:
            logger.warning("No cert loaded in get_extension")
            return None
        if m2x509.get_ext(name) is None:
            return None
        value = m2x509.get_ext(name).get_value()

        return value

    ##
    # Set_data is a wrapper around add_extension. It stores the
    # parameter str in the X509 subject_alt_name extension. Set_data
    # can only be called once, due to limitations in the underlying
    # library.

    def set_data(self, string, field='subjectAltName'):
        # pyOpenSSL only allows us to add extensions, so if we try to set the
        # same extension more than once, it will not work
        if field in self.data:
            raise Exception("Cannot set {} more than once".format(field))
        self.data[field] = string
        # call str() because we've seen unicode there
        # and the underlying C code doesn't like it
        self.add_extension(field, 0, str(string))

    ##
    # Return the data string that was previously set with set_data

    def get_data(self, field='subjectAltName'):
        if field in self.data:
            return self.data[field]

        try:
            uri = self.get_extension(field)
            self.data[field] = uri
        except LookupError:
            return None

        return self.data[field]

    ##
    # Sign the certificate using the issuer private key and issuer subject
    # previous set with set_issuer().

    def sign(self):
        logger.debug('certificate.sign')
        assert self.x509 is not None
        assert self.issuerSubject is not None
        assert self.issuerKey is not None
        self.x509.set_issuer(self.issuerSubject)
        self.x509.sign(self.issuerKey.get_openssl_pkey(), self.digest)

    ##
    # Verify the authenticity of a certificate.
    # @param pkey is a Keypair object representing a public key. If Pkey
    #     did not sign the certificate, then an exception will be thrown.

    def verify(self, pubkey):
        import M2Crypto
        # pyOpenSSL does not have a way to verify signatures
        m2x509 = M2Crypto.X509.load_cert_string(self.save_to_string())
        m2pubkey = pubkey.get_m2_pubkey()
        # verify it
        # https://www.openssl.org/docs/man1.1.0/crypto/X509_verify.html
        # verify returns
        # 1  if it checks out
        # 0  if if does not
        # -1 if it could not be checked 'for some reason'
        m2result = m2x509.verify(m2pubkey)
        result = m2result == 1
        if debug_verify_chain:
            logger.debug("Certificate.verify: <- {} (m2={}) ({} x {})"
                         .format(result, m2result,
                                 self.pretty_cert(), m2pubkey))
        return result

        # XXX alternatively, if openssl has been patched, do the much simpler:
        # try:
        #   self.x509.verify(pkey.get_openssl_key())
        #   return 1
        # except:
        #   return 0

    ##
    # Return True if pkey is identical to the public key that is
    # contained in the certificate.
    # @param pkey Keypair object

    def is_pubkey(self, pkey):
        return self.get_pubkey().is_same(pkey)

    ##
    # Given a certificate cert, verify that this certificate was signed by the
    # public key contained in cert. Throw an exception otherwise.
    #
    # @param cert certificate object

    def is_signed_by_cert(self, cert):
        key = cert.get_pubkey()
        logger.debug("Certificate.is_signed_by_cert -> verify on {}\n"
                     "with pubkey {}"
                     .format(self, key))
        result = self.verify(key)
        return result

    ##
    # Set the parent certificate.
    #
    # @param p certificate object.

    def set_parent(self, p):
        self.parent = p

    ##
    # Return the certificate object of the parent of this certificate.

    def get_parent(self):
        return self.parent

    ##
    # Verification examines a chain of certificates to ensure that each parent
    # signs the child, and that some certificate in the chain is signed by a
    # trusted certificate.
    #
    # Verification is a basic recursion: <pre>
    #     if this_certificate was signed by trusted_certs:
    #         return
    #     else
    #         return verify_chain(parent, trusted_certs)
    # </pre>
    #
    # At each recursion, the parent is tested to ensure that it did sign the
    # child. If a parent did not sign a child, then an exception is thrown. If
    # the bottom of the recursion is reached and the certificate does not match
    # a trusted root, then an exception is thrown.
    # Also require that parents are CAs.
    #
    # @param Trusted_certs is a list of certificates that are trusted.
    #

    def verify_chain(self, trusted_certs=None):
        # Verify a chain of certificates. Each certificate must be signed by
        # the public key contained in it's parent. The chain is recursed
        # until a certificate is found that is signed by a trusted root.

        # verify expiration time
        if self.x509.has_expired():
            if debug_verify_chain:
                logger.debug("verify_chain: NO, Certificate {} has expired"
                             .format(self.pretty_cert()))
            raise CertExpired(self.pretty_cert(), "client cert")

        # if this cert is signed by a trusted_cert, then we are set
        for i, trusted_cert in enumerate(trusted_certs, 1):
            logger.debug(5*'-' +
                         " Certificate.verify_chain - trying trusted #{} : {}"
                         .format(i, trusted_cert.pretty_name()))
            if self.is_signed_by_cert(trusted_cert):
                # verify expiration of trusted_cert ?
                if not trusted_cert.x509.has_expired():
                    if debug_verify_chain:
                        logger.debug("verify_chain: YES."
                                     " Cert {} signed by trusted cert {}"
                                     .format(self.pretty_name(),
                                             trusted_cert.pretty_name()))
                    return trusted_cert
                else:
                    if debug_verify_chain:
                        logger.debug("verify_chain: NO. Cert {} "
                                     "is signed by trusted_cert {}, "
                                     "but that signer is expired..."
                                     .format(self.pretty_cert(),
                                             trusted_cert.pretty_cert()))
                    raise CertExpired("{} signer trusted_cert {}"
                                      .format(self.pretty_name(),
                                              trusted_cert.pretty_name()))
            else:
                logger.debug("verify_chain: not a direct"
                             " descendant of trusted root #{}".format(i))

        # if there is no parent, then no way to verify the chain
        if not self.parent:
            if debug_verify_chain:
                logger.debug("verify_chain: NO. {} has no parent "
                             "and issuer {} is not in {} trusted roots"
                             .format(self.pretty_name(), self.get_issuer(),
                                     len(trusted_certs)))
            raise CertMissingParent("{}: Issuer {} is not "
                                    "one of the {} trusted roots, "
                                    "and cert has no parent."
                                    .format(self.pretty_name(),
                                            self.get_issuer(),
                                            len(trusted_certs)))

        # if it wasn't signed by the parent...
        if not self.is_signed_by_cert(self.parent):
            if debug_verify_chain:
                logger.debug("verify_chain: NO. {} is not signed by parent {}"
                             .format(self.pretty_name(),
                                     self.parent.pretty_name()))
                self.save_to_file("/tmp/xxx-capture.pem", save_parents=True)
            raise CertNotSignedByParent("{}: Parent {}, issuer {}"
                                        .format(self.pretty_name(),
                                                self.parent.pretty_name(),
                                                self.get_issuer()))

        # Confirm that the parent is a CA. Only CAs can be trusted as
        # signers.
        # Note that trusted roots are not parents, so don't need to be
        # CAs.
        # Ugly - cert objects aren't parsed so we need to read the
        # extension and hope there are no other basicConstraints
        if not self.parent.isCA and not (
                self.parent.get_extension('basicConstraints') == 'CA:TRUE'):
            logger.warning("verify_chain: cert {}'s parent {} is not a CA"
                            .format(self.pretty_name(), self.parent.pretty_name()))
            raise CertNotSignedByParent("{}: Parent {} not a CA"
                                        .format(self.pretty_name(),
                                                self.parent.pretty_name()))

        # if the parent isn't verified...
        if debug_verify_chain:
            logger.debug("verify_chain: .. {}, -> verifying parent {}"
                         .format(self.pretty_name(),
                                 self.parent.pretty_name()))
        self.parent.verify_chain(trusted_certs)

        return

    # more introspection
    def get_extensions(self):
        import M2Crypto
        # pyOpenSSL does not have a way to get extensions
        triples = []
        m2x509 = M2Crypto.X509.load_cert_string(self.save_to_string())
        nb_extensions = m2x509.get_ext_count()
        logger.debug("X509 had {} extensions".format(nb_extensions))
        for i in range(nb_extensions):
            ext = m2x509.get_ext_at(i)
            triples.append(
                (ext.get_name(), ext.get_value(), ext.get_critical(),))
        return triples

    def get_data_names(self):
        return list(self.data.keys())

    def get_all_datas(self):
        triples = self.get_extensions()
        for name in self.get_data_names():
            triples.append((name, self.get_data(name), 'data',))
        return triples

    # only informative
    def get_filename(self):
        return getattr(self, 'filename', None)

    def dump(self, *args, **kwargs):
        print(self.dump_string(*args, **kwargs))

    def dump_string(self, show_extensions=False):
        result = ""
        result += "CERTIFICATE for {}\n".format(self.pretty_cert())
        result += "Issued by {}\n".format(self.get_issuer())
        filename = self.get_filename()
        if filename:
            result += "Filename {}\n".format(filename)
        if show_extensions:
            all_datas = self.get_all_datas()
            result += " has {} extensions/data attached".format(len(all_datas))
            for n, v, c in all_datas:
                if c == 'data':
                    result += "   data: {}={}\n".format(n, v)
                else:
                    result += "    ext: {} (crit={})=<<<{}>>>\n".format(n, c, v)
        return result
