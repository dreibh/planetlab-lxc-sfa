##
# This module implements a general-purpose server layer for sfa.
# The same basic server should be usable on the registry, component, or
# other interfaces.
#
# TODO: investigate ways to combine this with existing PLC server?
##

import sys
import socket
import traceback
import threading
from queue import Queue
import socketserver
import ssl
import http.server
import xmlrpc.server
import xmlrpc.client

from sfa.util.sfalogging import logger
from sfa.util.config import Config
from sfa.util.cache import Cache
from sfa.trust.certificate import Certificate
from sfa.trust.trustedroots import TrustedRoots

# don't hard code an api class anymore here
from sfa.generic import Generic

##
# Verification callback for pyOpenSSL. We do our own checking of keys because
# we have our own authentication spec. Thus we disable several of the normal
# prohibitions that OpenSSL places on certificates


def verify_callback(conn, x509, err, depth, preverify):
    # if the cert has been preverified, then it is ok
    if preverify:
        # print "  preverified"
        return True

    # the certificate verification done by openssl checks a number of things
    # that we aren't interested in, so we look out for those error messages
    # and ignore them

    # XXX SMBAKER: I don't know what this error is, but it's being returned
    # xxx thierry: this most likely means the cert
    #     has a validity range in the future
    # by newer pl nodes.
    if err == 9:
        # print "  X509_V_ERR_CERT_NOT_YET_VALID"
        return True

    # allow self-signed certificates
    if err == 18:
        # print "  X509_V_ERR_DEPTH_ZERO_SELF_SIGNED_CERT"
        return False

    # allow certs that don't have an issuer
    if err == 20:
        # print "  X509_V_ERR_UNABLE_TO_GET_ISSUER_CERT_LOCALLY"
        return False

    # allow chained certs with self-signed roots
    if err == 19:
        return False

    # allow certs that are untrusted
    if err == 21:
        # print "  X509_V_ERR_UNABLE_TO_VERIFY_LEAF_SIGNATURE"
        return False

    # allow certs that are untrusted
    if err == 27:
        # print "  X509_V_ERR_CERT_UNTRUSTED"
        return False

    # ignore X509_V_ERR_CERT_SIGNATURE_FAILURE
    if err == 7:
        return False

    logger.debug("  unhandled error %s in verify_callback" % err)

    return False

##
# taken from the web (XXX find reference). Implements HTTPS xmlrpc request
# handler

# python-2.7 http://code.activestate.com/recipes/442473-simple-http-server-supporting-ssl-secure-communica/
# python-3.3 https://gist.github.com/ubershmekel/6194556
class SecureXMLRpcRequestHandler(xmlrpc.server.SimpleXMLRPCRequestHandler):
    """
    Secure XML-RPC request handler class.

    It it very similar to SimpleXMLRPCRequestHandler
    but it uses HTTPS for transporting XML data.
    """

    # porting to python3
    # setup() no longer needed

    def do_POST(self):
        """
        Handles the HTTPS POST request.

        It was copied out from SimpleXMLRPCServer.py and modified to shutdown
        the socket cleanly.
        """
        try:
            peer_cert = Certificate()
            peer_cert.load_from_pyopenssl_x509(
                self.connection.getpeercert())
            generic = Generic.the_flavour()
            self.api = generic.make_api(peer_cert=peer_cert,
                                        interface=self.server.interface,
                                        key_file=self.server.key_file,
                                        cert_file=self.server.cert_file,
                                        cache=self.cache)
            # logger.info("SecureXMLRpcRequestHandler.do_POST:")
            # logger.info("interface=%s"%self.server.interface)
            # logger.info("key_file=%s"%self.server.key_file)
            # logger.info("api=%s"%self.api)
            # logger.info("server=%s"%self.server)
            # logger.info("handler=%s"%self)
            # get arguments
            request = self.rfile.read(int(self.headers["content-length"]))
            remote_addr = (
                remote_ip, remote_port) = self.connection.getpeername()
            self.api.remote_addr = remote_addr
            response = self.api.handle(
                remote_addr, request, self.server.method_map)
        except Exception as fault:
            # This should only happen if the module is buggy
            # internal error, report as HTTP server error
            logger.log_exc("server.do_POST")
            response = self.api.prepare_response(fault)
            # self.send_response(500)
            # self.end_headers()

        # avoid session/connection leaks : do this no matter what
        finally:
            self.send_response(200)
            self.send_header("Content-type", "text/xml")
            self.send_header("Content-length", str(len(response)))
            self.end_headers()
            self.wfile.write(response.encode())
            self.wfile.flush()
            # close db connection
            self.api.close_dbsession()
            # shut down the connection
            self.connection.shutdown(socket.SHUT_RDWR)  # Modified here!

##
# Taken from the web (XXX find reference). Implements an HTTPS xmlrpc server


class SecureXMLRPCServer(http.server.HTTPServer,
                         xmlrpc.server.SimpleXMLRPCDispatcher):

    def __init__(self, server_address, HandlerClass,
                 key_file, cert_file, logRequests=True):
        """
        Secure XML-RPC server.

        It it very similar to SimpleXMLRPCServer
        but it uses HTTPS for transporting XML data.
        """
        logger.debug(
            f"SecureXMLRPCServer.__init__, server_address={server_address}, "
            f"cert_file={cert_file}, key_file={key_file}")
        self.logRequests = logRequests
        self.interface = None
        self.key_file = key_file
        self.cert_file = cert_file
        self.method_map = {}
        # add cache to the request handler
        HandlerClass.cache = Cache()
        xmlrpc.server.SimpleXMLRPCDispatcher.__init__(self, True, None)
        socketserver.BaseServer.__init__(self, server_address, HandlerClass)
        ssl_context = ssl.create_default_context(purpose=ssl.Purpose.CLIENT_AUTH)
        ssl_context.load_cert_chain(cert_file, key_file)
        # If you wanted to verify certs against known CAs..
        # this is how you would do it
        # ssl_context.load_verify_locations('/etc/sfa/trusted_roots/plc.gpo.gid')
        config = Config()
        trusted_cert_files = TrustedRoots(
            config.get_trustedroots_dir()).get_file_list()
        cadata = ""
        for cert_file in trusted_cert_files:
            with open(cert_file) as cafile:
                cadata += cafile.read()
        ssl_context.load_verify_locations(cadata=cadata)
#        ctx.set_verify(SSL.VERIFY_PEER |
#                       SSL.VERIFY_FAIL_IF_NO_PEER_CERT, verify_callback)
#        ctx.set_verify_depth(5)
#        ctx.set_app_data(self)
        # with python3 we use standard library SSLContext.wrap_socket()
        # instead of an OpenSSL.SSL.Connection object
        self.socket = ssl_context.wrap_socket(
            socket.socket(self.address_family, self.socket_type),
            server_side=True)
        self.server_bind()
        self.server_activate()

    # _dispatch
    #
    # Convert an exception on the server to a full stack trace and send it to
    # the client.

    def _dispatch(self, method, params):
        logger.debug("SecureXMLRPCServer._dispatch, method=%s" % method)
        try:
            return xmlrpc.server.SimpleXMLRPCDispatcher._dispatch(
                self, method, params)
        except:
            # can't use format_exc() as it is not available in jython yet
            # (even in trunk).
            type, value, tb = sys.exc_info()
            raise xmlrpc.client.Fault(1, ''.join(
                traceback.format_exception(type, value, tb)))

    # porting to python3
    # shutdown_request() no longer needed


# From Active State code: http://code.activestate.com/recipes/574454/
# This is intended as a drop-in replacement for the ThreadingMixIn class in
# module SocketServer of the standard lib. Instead of spawning a new thread
# for each request, requests are processed by of pool of reusable threads.

class ThreadPoolMixIn(socketserver.ThreadingMixIn):
    """
    use a thread pool instead of a new thread on every request
    """
    # XX TODO: Make this configurable
    # config = Config()
    # numThreads = config.SFA_SERVER_NUM_THREADS
    numThreads = 25
    allow_reuse_address = True  # seems to fix socket.error on server restart

    def serve_forever(self):
        """
        Handle one request at a time until doomsday.
        """
        # set up the threadpool
        self.requests = Queue()

        for _ in range(self.numThreads):
            thread = threading.Thread(target=self.process_request_thread)
            thread.setDaemon(1)
            thread.start()

        # server main loop
        while True:
            self.handle_request()

        self.server_close()

    def process_request_thread(self):
        """
        obtain request from queue instead of directly from server socket
        """
        while True:
            socketserver.ThreadingMixIn.process_request_thread(
                self, *self.requests.get())

    def handle_request(self):
        """
        simply collect requests and put them on the queue for the workers.
        """
        try:
            request, client_address = self.get_request()
        except socket.error:
            return
        if self.verify_request(request, client_address):
            self.requests.put((request, client_address))


class ThreadedServer(ThreadPoolMixIn, SecureXMLRPCServer):
    pass
