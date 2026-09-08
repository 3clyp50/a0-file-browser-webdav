# File Browser WebDAV access

![File Browser WebDAV access](webui/thumbnail.webp)

WebDAV over verified HTTPS, including Nextcloud-style DAV endpoints.

## Compatibility

**Requires Agent Zero v2.12 or later.**

## Install and configure

Install this repository through Agent Zero's Plugin Hub Git URL installer. Enable the plugin globally, then open its settings and choose **Open connection settings**, or use **Files → Settings → Add connection** and select this transport.

Enter the final HTTPS folder endpoint and a registered account with a password or app password. An optional trusted CA file is an absolute path inside the Agent Zero instance. Redirects are rejected: use the final DAV endpoint. Certificate verification is always enabled.

Dependencies: Requests 2.34.2 and defusedxml 0.7.1. The installer calls `hooks.py install()` in the Agent Zero framework runtime. It is safe to rerun; there is no execute.py.

## Use and permissions

Save a named connection, test it, then use the folder icon in the connection list. Each connection has independent Browse, Download, Upload/create, Edit, Rename/move and Delete controls; unsupported actions are disabled. Browse and Download default on; mutations default off. Text and code files open in the shared Editor. Files supports list/icon views and the optional file tree for remote connections.

Permissions constrain File Browser operations, not arbitrary agent shell tools or server accounts. Editing necessarily reveals file content. Credentials are stored privately (0600) under this plugin's `data/connections.json` and are omitted from browser responses. An unchanged secret retains its saved value; replacing it updates it. Protect the instance and its backups.

## Limits

Editing requires strong ETags and a server that honors HTTP conditional writes. Creating a file uses If-None-Match; replacement uses If-Match. Weak or missing ETags prevent replacement. Server ACLs define access; collections may represent server-side aliases. Anonymous access and plain HTTP are not supported.

Shared Files limits: 100 MiB uploads/download archives, 1000 archive entries, nesting depth 64; Editor supports UTF-8 nonbinary files up to 1 MiB. Cross-connection moves and remote-to-local Save As are not supported. Use download/upload to transfer between connection types. Internet access to the configured server is required; storage/network charges remain your provider's responsibility.

## Verification

Actual isolated HTTPS WebDAV listing/read/write/rename/delete, stale ETag and duplicate-create rejection, bounded reads, and untrusted certificate rejection. Run `python -m unittest -v test_transport` from the repository with the framework interpreter; the test uses OpenSSL to create a disposable certificate.

Before production use, test a disposable folder on your actual server: listing, new upload, Editor save, duplicate destination rejection, stale-save rejection, download, rename where supported, and deletion. Confirm denied actions remain denied and disable the plugin to confirm connections become unavailable. Protocol differences and server permissions matter.

## Disable and remove

Disabling hides this provider and rejects further connection operations. Removing a connection deletes its saved credentials. Uninstalling deletes the plugin directory, including saved connections and any plugin-owned key; back up what you need first. Shared Python dependencies are not uninstalled because other plugins may use them. No service, mount or system symlink is created. Legacy SSH data is preserved during migration and is not removed by uninstall.

## License

MIT. See [LICENSE](LICENSE). Agent Zero-derived integration retains its upstream license notice.
