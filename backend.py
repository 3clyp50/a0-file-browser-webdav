"""HTTPS WebDAV adapter with conditional writes and bounded, same-origin requests."""
import email.utils
import posixpath
from contextlib import contextmanager
from urllib.parse import quote, unquote, urljoin, urlsplit

import requests
from defusedxml import ElementTree

DAV = "{DAV:}"


class Provider:
    id = "webdav"
    plugin_name = "file_browser_webdav"
    title = "WebDAV over HTTPS"
    fields = [
        {"name": "url", "label": "WebDAV folder URL", "default": "", "placeholder": "https://cloud.example.com/remote.php/dav/files/user/"},
        {"name": "username", "label": "Username", "default": ""},
        {"name": "password", "label": "Password or app password", "secret": True},
        {"name": "ca_file", "label": "Trusted CA file (optional)", "default": "", "advanced": True},
    ]

    def validate(self, config):
        url = str(config.get("url", "")).strip()
        parts = urlsplit(url)
        if parts.scheme != "https" or not parts.hostname or parts.username or parts.password or parts.query or parts.fragment:
            raise ValueError("Use an HTTPS WebDAV folder URL without credentials, query or fragment.")
        username = str(config.get("username", "")).strip()
        if not username:
            raise ValueError("A username is required.")
        return {"url": url.rstrip("/") + "/", "username": username,
                "password": str(config.get("password") or ""), "ca_file": str(config.get("ca_file") or "").strip()}

    @contextmanager
    def open(self, config, directory):
        with requests.Session() as session:
            session.auth = (config["username"], config.get("password", ""))
            session.verify = config.get("ca_file") or True
            yield WebDAV(session, config["url"])


class WebDAV:
    def __init__(self, session, base):
        self.session, self.base = session, base.rstrip("/") + "/"

    def url(self, relative):
        return self.base + quote(relative, safe="/")

    def request(self, method, relative, **kwargs):
        response = self.session.request(method, self.url(relative), timeout=(10, 30), allow_redirects=False, **kwargs)
        if 200 <= response.status_code < 300:
            return response
        status = response.status_code
        response.close()
        if status == 404:
            raise FileNotFoundError(relative)
        if status in (401, 403):
            raise PermissionError("WebDAV server denied this operation.")
        if status in (409, 412, 423):
            raise ValueError("Remote file changed, already exists, is locked, or its parent is missing.")
        if 300 <= status < 400:
            raise ValueError("The server redirected this URL. Configure its final HTTPS WebDAV address.")
        raise ValueError(f"WebDAV operation failed (HTTP {status}).")

    def entries(self, relative, depth):
        body = b'<?xml version="1.0"?><d:propfind xmlns:d="DAV:"><d:prop><d:resourcetype/><d:getcontentlength/><d:getlastmodified/><d:getetag/></d:prop></d:propfind>'
        with self.request("PROPFIND", relative, headers={"Depth": str(depth), "Content-Type": "application/xml"}, data=body, stream=True) as response:
            content = bytearray()
            for chunk in response.iter_content(65536):
                content.extend(chunk)
                if len(content) > 8 * 1024 * 1024:
                    raise ValueError("Directory listing is too large.")
        root = ElementTree.fromstring(content)
        base = urlsplit(self.base)
        base_path = unquote(base.path).rstrip("/")
        result = []
        for node in root.findall(DAV + "response"):
            target = urlsplit(urljoin(self.base, node.findtext(DAV + "href", "")))
            decoded = unquote(target.path).rstrip("/")
            if (target.scheme, target.netloc) != (base.scheme, base.netloc):
                continue
            if decoded != base_path and not decoded.startswith(base_path + "/"):
                continue
            path = decoded[len(base_path):].strip("/")
            if ".." in path.split("/"):
                continue
            properties = None
            for section in node.findall(DAV + "propstat"):
                if " 200 " in section.findtext(DAV + "status", ""):
                    properties = section.find(DAV + "prop")
                    break
            if properties is None:
                continue
            date = properties.findtext(DAV + "getlastmodified", "")
            try:
                modified = email.utils.parsedate_to_datetime(date).timestamp() * 1000
            except (TypeError, ValueError):
                modified = 0
            result.append({"path": path, "name": posixpath.basename(path),
                           "is_dir": properties.find(DAV + "resourcetype/" + DAV + "collection") is not None,
                           "size": int(properties.findtext(DAV + "getcontentlength", "0") or 0),
                           "modified": modified, "revision": {"etag": properties.findtext(DAV + "getetag", "")}})
        return result

    def stat(self, relative):
        for item in self.entries(relative, 0):
            if item["path"] == relative.strip("/"):
                return item
        raise FileNotFoundError(relative)

    def list(self, relative):
        return [item for item in self.entries(relative, 1)
                if item["path"] != relative.strip("/") and posixpath.dirname(item["path"]) == relative.strip("/")]

    def read(self, relative, limit):
        with self.request("GET", relative, stream=True) as response:
            if int(response.headers.get("Content-Length", 0)) > limit:
                raise ValueError("File exceeds the size limit.")
            data = bytearray()
            for chunk in response.iter_content(65536):
                data.extend(chunk)
                if len(data) > limit:
                    raise ValueError("File exceeds the size limit.")
            return bytes(data), {"etag": response.headers.get("ETag", "")}

    def write(self, relative, content, expected=None):
        if expected is None:
            headers = {"If-None-Match": "*"}
        else:
            etag = expected.get("etag", "")
            if not etag or etag.startswith("W/"):
                raise ValueError("This server did not supply a strong ETag; safe replacement is unavailable.")
            headers = {"If-Match": etag}
        with self.request("PUT", relative, data=content, headers=headers) as response:
            etag = response.headers.get("ETag", "")
        return {"etag": etag} if etag else self.stat(relative)["revision"]

    def mkdir(self, relative):
        self.request("MKCOL", relative).close()

    def rename(self, source, destination):
        self.request("MOVE", source, headers={"Destination": self.url(destination), "Overwrite": "F"}).close()

    def remove(self, relative, directory=False):
        self.request("DELETE", relative).close()
