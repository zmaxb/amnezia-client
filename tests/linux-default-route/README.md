# Linux default-route regression

This test compiles the Linux body of the production
`NetworkUtilities::getGatewayAndIface()` function twice: once from the upstream
`5.0.3.0` tag and once from the working tree. It checks the returned gateway and
interface and counts open file descriptors before and after each probe.

All route changes run in a new, unprivileged user/network namespace. The test
creates a dummy interface; it does not start a VPN or access the installed client.
Do not run it as root or replace `unshare` with commands on the host network.

Requirements: Python 3, g++, iproute2, util-linux, Qt 6 Core/Network development
files, and enabled unprivileged user namespaces.

```sh
python3 tests/linux-default-route/regression.py \
  --qt-include /path/to/Qt/6.10.1/gcc_64/include \
  --qt-lib /path/to/Qt/6.10.1/gcc_64/lib
```

The default fixture contains 8589 synthetic IPv4 host routes. Checks cover an
absent default route, small/large route tables, repeated lookups without socket
leaks, a non-default route with a different gateway, multiple tables/default
route metrics, and a changed default gateway. The upstream control must pass the
empty-table case and fail with the full table; the patched lookup must pass.

Use `--baseline-ref <ref>` for another known upstream version. An optional
`--sites <file>` accepts an IP-only JSON export for private local testing; it is
not needed in CI and no private fixture is included in this repository.
