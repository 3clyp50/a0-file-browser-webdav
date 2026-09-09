# File Browser WebDAV access

![File Browser WebDAV access](webui/thumbnail.webp)

Browse and manage files on Nextcloud or another WebDAV service directly from Agent Zero’s File Browser. Connect securely using the service’s HTTPS WebDAV address.

## Compatibility

**Requires Agent Zero v2.12 or later.**

## Install and configure

1. Open **Plugin Hub**, find **File Browser WebDAV access**, and install it.
2. Enable the plugin globally, then open its settings and choose **Open connection settings**. You can also go to **Files → Settings → Add connection** and choose this plugin.
3. Enter the connection details described below, give the connection a name, and save it.
4. Test the connection, then use its folder icon to open your files.

Enter the final HTTPS folder endpoint and a registered account with a password or app password. An optional trusted CA file is an absolute path inside the Agent Zero instance. Redirects are rejected: use the final DAV endpoint. Certificate verification is always enabled.

## Use and permissions

Each connection has independent Browse, Download, Upload/create, Edit, Rename/move and Delete controls; unsupported actions are disabled. Browse and Download default on; mutations default off. Text and code files open in the shared Editor. Files supports list/icon views and the optional file tree for remote connections.

Permissions constrain File Browser operations, not arbitrary agent shell tools or server accounts. Editing necessarily reveals file content. Credentials are stored privately (0600) under this plugin's `data/connections.json` and are omitted from browser responses. An unchanged secret retains its saved value; replacing it updates it. Protect the instance and its backups.

## Limits

Editing requires strong ETags and a server that honors HTTP conditional writes. Creating a file uses If-None-Match; replacement uses If-Match. Weak or missing ETags prevent replacement. Server ACLs define access; collections may represent server-side aliases. Anonymous access and plain HTTP are not supported.

Set size limits in File Browser settings: transfers default to 100 MiB, text editing to 10 MiB, and archives to 1,000 entries. Transfers stream through temporary files; text editing supports UTF-8 files without binary content. Cross-connection moves and remote-to-local Save As are not supported. Use download/upload to transfer between connection types. Agent Zero must be able to reach the configured server; storage/network charges remain your provider's responsibility.

## Technical details

The adapter uses the Agent Zero v2.12 streaming interface: `read(relative, destination, limit)` writes bounded chunks and returns a revision; `write(relative, source, expected=None)` consumes a seekable binary stream and returns the new revision. Transfer limits come from File Browser settings.

Dependencies: Requests 2.34.2 and defusedxml 0.7.1. The installer calls `hooks.py install()` in the Agent Zero framework runtime. It is safe to rerun; there is no execute.py.

## Verification

Transport checks cover streamed transfers above 1 MiB, size-limit rejection, and safe-write behavior. Tests use disposable local servers or SDK mocks, without production credentials.

Actual isolated HTTPS WebDAV listing/read/write/rename/delete, stale ETag and duplicate-create rejection, bounded reads, and untrusted certificate rejection. Run `PYTHONPATH=/a0 python -m unittest -v test_transport` from the repository inside the Agent Zero container, using its framework interpreter; the test uses OpenSSL to create a disposable certificate.

Before production use, test a disposable folder on your actual server: listing, new upload, Editor save, duplicate destination rejection, stale-save rejection, download, rename where supported, and deletion. Confirm denied actions remain denied and disable the plugin to confirm connections become unavailable. Protocol differences and server permissions matter.

## Disable and remove

Disabling hides this provider and rejects further connection operations. Removing a connection deletes its saved credentials. Uninstalling deletes the plugin directory, including saved connections and any plugin-owned key; back up what you need first. Shared Python dependencies are not uninstalled because other plugins may use them. No service, mount or system symlink is created.

## License

MIT. See [LICENSE](LICENSE). Agent Zero-derived integration retains its upstream license notice.
