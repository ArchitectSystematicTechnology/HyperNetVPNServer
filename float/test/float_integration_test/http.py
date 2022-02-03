import http.cookiejar
import http.client
import os
import re
import socket
import ssl
import urllib.request
import urllib.error
import urllib.parse


class AuthenticationError(Exception):
    pass


class HTTPNoRedirectHandler(urllib.request.HTTPRedirectHandler):

    def http_error_301(self, req, fp, code, msg, hdrs):
        raise urllib.error.HTTPError(req.get_full_url(), code, msg, hdrs, fp)

    def http_error_302(self, req, fp, code, msg, hdrs):
        raise urllib.error.HTTPError(req.get_full_url(), code, msg, hdrs, fp)

    def http_error_303(self, req, fp, code, msg, hdrs):
        raise urllib.error.HTTPError(req.get_full_url(), code, msg, hdrs, fp)


class SSOHandler(urllib.request.BaseHandler):
    """Intercept SSO login requests and fulfills them on-the-fly."""

    _form_pattern = re.compile(r'<input type="hidden" name="([^"]+)" value="([^"]+)"')
    _otp_pattern = re.compile(r'<input[^>]+ name="otp"')

    def __init__(self, username, password, otp=None, login_server=None,
                 auth_notify_cb=None):
        self._username = username
        self._password = password
        self._otp = otp
        self._login_server = login_server
        self._login_form_url = login_server.rstrip('/') + '/login'
        self._auth_notify_cb = auth_notify_cb

    def _extract_hidden_form_data(self, html):
        form = {}
        for name, value in self._form_pattern.findall(html):
            form[name] = value
        return form

    def https_response(self, req, resp):
        request_url = req.get_full_url()
        if resp.code == 200 and request_url.startswith(self._login_form_url):
            if hasattr(req, 'sso_attempt'):
                raise AuthenticationError('SSO authentication failure')
            request_baseurl = request_url.split('?')[0]
            response_data = resp.read().decode('utf-8')
            form_data = self._extract_hidden_form_data(response_data)
            form_data['username'] = self._username
            form_data['password'] = self._password
            # See if the form is requesting an OTP token.
            if self._otp_pattern.search(response_data):
                form_data['otp'] = self._otp
            newreq = urllib.request.Request(
                request_baseurl,
                data=urllib.parse.urlencode(form_data).encode('utf-8'))
            newreq.sso_attempt = True
            # Notify.
            if self._auth_notify_cb:
                self._auth_notify_cb()
            resp = self.parent.open(newreq)
        return resp


def _build_opener(ipaddr, follow_redirects=False, *extra_handlers):
    """Build an opener that resolves all DNS names to the same address."""
    # Sigh, all this just to override the DNS resolution at connection
    # time in a safe way.
    def _resolve(host):
        return ipaddr

    class HTTPConnection(http.client.HTTPConnection):
        def connect(self):
            self.sock = socket.create_connection(
                (_resolve(self.host), self.port), self.timeout)

    class HTTPSConnection(http.client.HTTPSConnection):
        def connect(self):
            sock = socket.create_connection(
                (_resolve(self.host), self.port), self.timeout)
            self.sock = self._context.wrap_socket(
                sock, server_hostname=self.host)

    class HTTPHandler(urllib.request.HTTPHandler):
        def http_open(self, req):
            return self.do_open(HTTPConnection, req)

    class HTTPSHandler(urllib.request.HTTPSHandler):
        def https_open(self, req):
            return self.do_open(HTTPSConnection, req,
                                context=self._context)

    # Create a tolerant SSL context that accepts the self-signed
    # certificates used by the testing environment.
    ssl_context = ssl.create_default_context(
        ssl.Purpose.CLIENT_AUTH)
    ssl_context.verify_mode = ssl.CERT_NONE

    debuglevel = 1 if os.getenv('HTTP_TRACE') else 0
    handlers = [
        HTTPHandler(debuglevel=debuglevel),
        HTTPSHandler(context=ssl_context, debuglevel=debuglevel),
    ]
    handlers.extend(extra_handlers)
    if not follow_redirects:
        handlers.append(HTTPNoRedirectHandler())
    return urllib.request.build_opener(*handlers)


def _request(url, opener, data=None):
    req = urllib.request.Request(url, data=data, headers={
        'User-Agent': 'ai3test/0.1',
        'Accept': '*; p=1',
    })
    result = {}

    try:
        resp = opener.open(req, timeout=5)
        result['status'] = resp.code
        result['body'] = resp.read()
    except urllib.error.HTTPError as e:
        result['status'] = e.code
        if e.code in (301, 302, 303, 307):
            result['location'] = e.headers['Location']
    except Exception as e:
        result['error'] = str(e)

    return result


def request(url, ip_addr, follow_redirects=False, data=None, handlers=None):
    if handlers is None:
        handlers = []
    opener = _build_opener(ip_addr, follow_redirects, *handlers)
    return _request(url, opener, data=data)


class Conversation(object):

    def __init__(self, sso_username=None, sso_password=None,
                 login_server=None):
        self.jar = http.cookiejar.CookieJar()
        self.sso_username = sso_username
        self.sso_password = sso_password
        self.login_server = login_server
        self.auth_requested = False

    def request(self, url, ip_addr, follow_redirects=True, data=None):
        handlers = [urllib.request.HTTPCookieProcessor(self.jar)]
        if self.sso_username:
            def _auth_notify_cb():
                self.auth_requested = True
            handlers.append(SSOHandler(
                username=self.sso_username,
                password=self.sso_password,
                login_server=self.login_server,
                auth_notify_cb=_auth_notify_cb))
        opener = _build_opener(
            ip_addr, follow_redirects,
            *handlers)
        return _request(url, opener, data=data)
