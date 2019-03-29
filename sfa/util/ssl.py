import ssl

def simple_ssl_context():
    """
    an SSL context that turns off server verification
    """
    ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS)
    ssl_context.verify_mode = ssl.CERT_NONE
    return ssl_context
