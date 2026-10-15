# Linux large-route split tunneling

[Download the English PDF edition](report-en.pdf).

**Validation date:** 2026-10-15

**Upstream base:** [5.0.3.0](https://github.com/amnezia-vpn/amnezia-client/releases/tag/5.0.3.0),
commit `de93650a90739b87bb47a632872ea9d0adc9412f`

**Fix commit:** `59089ca`

**Scope:** Linux, IPv4 site exclusions, self-hosted AmneziaWG 2.

The patched client successfully applied all **8589 IPv4 exclusions** in an
isolated end-to-end test. Route destinations, outgoing interface, gateway,
traffic flow, and cleanup were verified. This is a candidate for a community
pilot release. It is not evidence of complete validation across all protocols,
desktop network managers, or long-running workloads.

## Problem and change

`NetworkUtilities::getGatewayAndIface()` used an 8192-byte buffer to accumulate
an entire multipart `NETLINK_ROUTE` dump. A sufficiently large route table
exhausted the buffer, causing gateway discovery to return an empty result.
Error paths also returned without closing the netlink socket. The failure can
occur while split routes are installed or removed, so a successful JSON import
or a `Connected` status is insufficient to prove correct routing.

The Linux implementation now:

- Reads and parses one netlink datagram at a time, using `MSG_PEEK | MSG_TRUNC`
  to allocate the actual datagram size.
- Uses a scope guard to close the socket on every exit, and `SOCK_CLOEXEC` to
  prevent inheritance across an exec.
- Requests IPv4 routes and selects a unicast default route in the main table,
  preferring the lowest route metric. It does not select an arbitrary subnet's
  gateway.
- Initializes the receive timeout, handles interrupted receives, validates
  message/attribute lengths, and rejects an interrupted dump.

The routing fix changes one production source file. Tests and the optional
community release configuration are separate. The release configuration labels
the application `5.0.3.0-large-routes.1` and disables the existing upstream update
path. The default upstream build configuration keeps its normal version and
update behavior.

Related upstream report: [amnezia-client issue #3090](https://github.com/amnezia-vpn/amnezia-client/issues/3090).

## Test environment and method

The end-to-end comparison used official 5.0.3.0 source, Qt 6.10.1, GCC 14.2,
Conan 2.28.0, and the AmneziaWG Go backend 3.1. The upstream control retained the
unmodified gateway function; the patched variant used the replacement function.

The client and service ran in separate user, network, PID, mount, and IPC
namespaces with dedicated settings, firewall rules, a virtual display, and
slirp4netns user-mode networking. A real self-hosted AmneziaWG 2 server used a
separate temporary peer, independent of any existing peer. The MTU was 1376.
A private benchmark listener was reachable through the test tunnel.

The input was an 829925-byte IP-only export containing 8589 valid,
non-overlapping IPv4 CIDRs. The public report retains only its size and count;
the private fixture, its contents, server identifiers, credentials, and local
machine identifiers are not distributed. The standalone regression instead
generates 8589 synthetic routes.

For every connection, checks compared every expected CIDR with the actual route
table, verified the route's gateway and outgoing interface, sent traffic, then
checked cleanup after Disconnect. The baseline namespace contained two main
table routes; cleanup was considered complete only when that baseline returned.

## Upstream control versus patch

| Variant | Applied exclusions | Missing | Extra main-table routes after Disconnect | Service open FDs while connected |
| --- | ---: | ---: | ---: | ---: |
| Upstream, 70 exclusions | 70 / 70 | 0 | 0 | 15 |
| Upstream, 8589 exclusions | 110 / 8589 | 8479 | 111 | 8495 |
| Patched, 8589 exclusions | 8589 / 8589 | 0 | 0 | 19 |
| Patched, 8589 + Kill Switch | 8589 / 8589 | 0 | 0 | 19 |

The upstream full-list run reported `Connected` despite the missing exclusions.
Its short connection time is therefore not comparable with a successful full
route setup. This control reproduced routing failure and descriptor leakage;
it did not reproduce every possible user-visible connection error.

The normal production executable was also tested independently of the QA
control entrypoint: **0 missing routes and 0 incorrect gateway/interface
selections** across all 8589 entries. All six HTTPS checks during a 60-second
observation succeeded. The normal GUI's Disconnect button restored the two-route
baseline in 11.88 seconds.

## Speed and setup cost

Each patched mode transferred two 10 MB HTTPS downloads from an external
endpoint, three 20 MB HTTP downloads through the tunnel to the private test
listener, and three 8 MB HTTP uploads to that listener. Values below are medians
in decimal Mbit/s. The comparison transferred approximately 416 MB of payload.

| Patched mode | External HTTPS download, n=2 | Tunnel HTTP download, n=3 | Tunnel HTTP upload, n=3 |
| --- | ---: | ---: | ---: |
| No exclusions | 40.72 | 17.09 | 33.30 |
| 70 exclusions | 43.94 | 21.97 | 45.91 |
| 8589 exclusions | 45.26 | 10.90 | 31.31 |
| 8589 + Kill Switch | 44.12 | 8.74 | 21.46 |

External HTTPS showed no evident throughput reduction in this small sample.
This does not establish a throughput improvement or a guaranteed line rate.
Tunnel HTTP download samples ranged from 5.37 to 66.76 Mbit/s. That variance and
the additional user-mode NAT prevent a reliable attribution of the difference
in medians to the route list. Recheck absolute throughput on a real desktop
installation before drawing capacity conclusions.

| Patched mode | Connect, seconds | Disconnect, seconds | Small HTTPS request median, seconds, n=5 |
| --- | ---: | ---: | ---: |
| No exclusions | 0.56 | 0.40 | 0.471 |
| 70 exclusions | 0.56 | 0.40 | 0.463 |
| 8589 exclusions | 10.70 | 12.14 | 0.457 |
| 8589 + Kill Switch | 21.94 | 16.37 | 0.465 |

Three further full-list cycles connected in 12.27-12.54 seconds and disconnected
in approximately 12.23 seconds. The normal production client connected in
12.51 seconds. Large lists still increase setup/teardown cost because gateway
discovery is repeated during individual route operations. Batched route changes
and carefully invalidated gateway caching are possible follow-up optimizations;
they are outside this patch.

## Reliability checks

| Check | Observation |
| --- | --- |
| Full-list import/export in private test settings | 8589 entries in, 8589 out; identical CIDR sets |
| Three further full-list connection cycles | No missing exclusions, HTTPS succeeded each time, baseline restored after each Disconnect |
| Unrelated route churn during setup | 562 route changes; no missing exclusions; HTTPS succeeded |
| Kill Switch with test-server UDP blocked | Both cached-DNS HTTPS requests timed out; HTTPS recovered when the block was removed |
| Descriptor stability | Patched service returned to 14 FDs after each tested disconnection; no accumulation observed |
| Memory | Service RSS approximately 60-61 MiB; GUI approximately 250 MiB under Xvfb/Mesa software rendering |
| Existing host connection | 73 HTTPS checks across 36.3 minutes, no failures; original process identities/start times, file hashes, host routes, and policy rules unchanged |
| Cleanup | Temporary peer and benchmark listener removed; isolated processes stopped |

The Kill Switch check demonstrates the tested IPv4 HTTPS failure path only; it
is not a comprehensive leak audit across IPv6, DNS transports, or all traffic.
GUI memory under software rendering is not a prediction for a normal desktop.

## Recovery observations and limitations

Bringing the virtual uplink down and back up removed its default route. The
sandbox had no NetworkManager/DHCP integration to recreate it. The initial
recovery request failed; reconnect tests passed after the sandbox default route
was explicitly restored. Automatic recovery after real Wi-Fi/Ethernet changes
therefore remains unvalidated.

Sending SIGTERM to the GUI left the tunnel and routes active in the separate
service. Relaunching the normal GUI and using Disconnect cleared them. Before
replacement or rollback, disconnect through the application; closing or killing
the GUI is not a substitute for Disconnect.

The tested scope excludes IPv6 internet access, other VPN protocols, application
split tunneling, multi-day uptime, and integration with real
NetworkManager/systemd-resolved. Sandbox DNS was configured explicitly.

The independent source build did not include the upstream CI-provided Gateway
configuration. Startup logs showed error 1105; the self-hosted tunnel worked,
but Free/Premium service screens and upstream API-based updates were not
validated. This release targets the tested self-hosted AWG2 use case.

## Reproduction and release status

Run the [standalone synthetic regression](../../tests/linux-default-route/README.md)
without a real VPN profile or private fixture. It invokes the production Linux
function body from the source, compares it with the upstream tag, and checks
descriptor counts, route metrics, routing tables, and a gateway change. Locally,
the upstream control failed at 200 and 8589 routes with one leaked descriptor
per failed lookup; all patched probes passed, including 100 repeated lookups.

[measurement-samples.json](measurement-samples.json) contains allowlisted numeric
samples and aggregate observations from the isolated end-to-end run. This
report describes the tested routing patch. CI installer build provenance and
checksums are recorded separately in release assets; successful packaging alone
does not constitute another real-server tunnel test.

See [BUILD-AND-INSTALL.md](BUILD-AND-INSTALL.md) for release build flags,
installation precautions, and rollback. No installed system service was replaced
as part of the isolated validation.
