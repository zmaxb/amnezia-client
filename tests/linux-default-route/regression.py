#!/usr/bin/env python3
"""Exercise the production Linux gateway lookup in an isolated network namespace.

Requires g++, Qt Core/Network headers and libraries, iproute2, and unprivileged
network namespaces. No Amnezia process, settings, or host routes are modified.
"""
import argparse
import ipaddress
import json
from pathlib import Path
import subprocess
import sys
import tempfile

ROOT = Path(__file__).resolve().parents[2]
SOURCE = Path('client/core/utils/networkUtilities.cpp')


def body(source):
    start = source.index('#ifdef Q_OS_LINUX', source.index(
        'QPair<QString, QNetworkInterface> NetworkUtilities::getGatewayAndIface()'))
    return source[start + len('#ifdef Q_OS_LINUX'):source.index('#endif', start)]


def isolated(args):
    # This branch is only entered by the unshare child below.
    def ip(*words):
        subprocess.run(['ip', *words], check=True, capture_output=True, text=True)

    if args.sites:
        sites = json.loads(args.sites.read_text())
        networks = [ipaddress.ip_network(site['hostname'], strict=True) for site in sites]
    else:
        # Synthetic addresses stay entirely inside this network namespace.
        # No private site list or real VPN credentials are needed.
        first = int(ipaddress.IPv4Address('172.20.0.1'))
        networks = [ipaddress.ip_network((first + index, 32))
                    for index in range(8589)]
    assert all(net.version == 4 for net in networks)
    ip('link', 'add', 'test0', 'type', 'dummy')
    ip('link', 'set', 'test0', 'up')
    ip('address', 'add', '10.254.254.2/24', 'dev', 'test0')
    results = []

    def probe(version, gateway='10.254.254.1', interface='test0', repetitions=1):
        result = subprocess.run([str(args.build / version), gateway, interface,
                                 str(repetitions)], capture_output=True, text=True, timeout=30)
        record = dict(version=version, exit=result.returncode,
                      stdout=result.stdout.strip(), stderr=result.stderr.strip())
        results.append(record)
        return result

    assert probe('fixed', '', '', 100).returncode == 0, 'No-default/socket cleanup failed'
    ip('route', 'add', 'default', 'via', '10.254.254.1', 'dev', 'test0')
    for count in sorted(set([0, min(70, len(networks)), min(200, len(networks)), len(networks)])):
        batch = ''.join(f'route replace {net} via 10.254.254.1 dev test0\n'
                        for net in networks[:count])
        subprocess.run(['ip', '-batch', '-'], input=batch, text=True,
                       check=True, capture_output=True)
        old = probe('baseline')
        fixed = probe('fixed')
        results[-2]['routes'] = results[-1]['routes'] = count
        assert fixed.returncode == 0, f'Fixed lookup failed at {count} routes: {fixed.stdout}'
        if count == 0:
            assert old.returncode == 0, 'Baseline fixture invalid'
        if count == len(networks) and count >= 200:
            assert old.returncode != 0, 'Fixture did not reproduce the baseline bug'

    assert probe('fixed', repetitions=100).returncode == 0, 'Repeated lookup/socket leak'
    ip('route', 'add', '1.0.0.1/32', 'via', '10.254.254.9', 'dev', 'test0')
    assert probe('fixed').returncode == 0, 'Non-default route selected as gateway'
    ip('route', 'add', 'default', 'via', '10.254.254.3', 'dev', 'test0', 'metric', '100')
    ip('route', 'add', 'default', 'via', '10.254.254.4', 'dev', 'test0', 'table', '100')
    assert probe('fixed').returncode == 0, 'Wrong table or default-route metric'
    ip('route', 'del', 'default', 'via', '10.254.254.1', 'dev', 'test0')
    assert probe('fixed', '10.254.254.3').returncode == 0, 'Gateway change not detected'
    report = dict(fixture='external' if args.sites else 'synthetic',
                  subnets=len(networks), checks=results)
    print(json.dumps(report, indent=2))


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--sites', type=Path, help='Optional IP-only exported site list')
    parser.add_argument('--qt-include', type=Path)
    parser.add_argument('--qt-lib', type=Path)
    parser.add_argument('--baseline-ref', default='5.0.3.0')
    parser.add_argument('--inside', action='store_true', help=argparse.SUPPRESS)
    parser.add_argument('--build', type=Path, help=argparse.SUPPRESS)
    args = parser.parse_args()
    if args.sites:
        args.sites = args.sites.resolve()
    if args.inside:
        isolated(args)
        return
    if not args.qt_include or not args.qt_lib:
        parser.error('--qt-include and --qt-lib are required')
    old = subprocess.check_output(['git', 'show', f'{args.baseline_ref}:{SOURCE}'],
                                  cwd=ROOT, text=True)
    with tempfile.TemporaryDirectory(prefix='amnezia-gateway-') as temp:
        build = Path(temp)
        for version, source in [('baseline', old), ('fixed', (ROOT / SOURCE).read_text())]:
            fragment = build / f'{version}.inc'
            fragment.write_text(body(source))
            subprocess.run([
                'g++', '-std=c++17', '-fPIC',
                f'-I{args.qt_include}', f'-I{args.qt_include / "QtCore"}',
                f'-I{args.qt_include / "QtNetwork"}', f'-DGATEWAY_BODY="{fragment}"',
                str(Path(__file__).with_name('probe.cpp')),
                f'-L{args.qt_lib}', f'-Wl,-rpath,{args.qt_lib}',
                '-l:libQt6Network.so.6', '-l:libQt6Core.so.6', '-o', str(build / version)
            ], check=True)
        command = ['unshare', '--user', '--map-root-user', '--net', '--',
                   sys.executable, str(Path(__file__).resolve()), '--inside',
                   '--build', str(build)]
        if args.sites:
            command.extend(['--sites', str(args.sites)])
        subprocess.run(command, check=True)


if __name__ == '__main__':
    main()
