#!/usr/bin/env python3
"""Render the public English report from allowlisted measurement data.

Requires reportlab. This script does not read private fixtures or raw logs.
"""
import argparse
import datetime
import json
import os
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.platypus import (
    PageBreak, Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle,
)

HERE = Path(__file__).resolve().parent
D = json.loads((HERE / 'measurement-samples.json').read_text())
# Reproducible metadata uses the public validation date, not local machine time.
os.environ.setdefault('SOURCE_DATE_EPOCH', str(int(datetime.datetime.fromisoformat(
    D['validation_date']).replace(tzinfo=datetime.timezone.utc).timestamp())))
NAVY = colors.HexColor('#173249')
TEAL = colors.HexColor('#08786C')
MUTED = colors.HexColor('#566674')
LIGHT = colors.HexColor('#EDF6F4')
GRAY = colors.HexColor('#F1F4F7')
WIDTH = A4[0] - 88
styles = getSampleStyleSheet()
for name, font, size, leading, after, color in [
    ('BodyReport', 'Helvetica', 10, 14.5, 9, NAVY),
    ('TitleReport', 'Helvetica-Bold', 25, 30, 13, NAVY),
    ('HeadingReport', 'Helvetica-Bold', 17, 22, 12, NAVY),
    ('SectionReport', 'Helvetica-Bold', 12, 16, 8, TEAL),
    ('SmallReport', 'Helvetica', 8.5, 12, 7, MUTED),
    ('CellReport', 'Helvetica', 8.8, 12, 0, NAVY),
    ('HeadReport', 'Helvetica-Bold', 8.8, 12, 0, colors.white),
]:
    styles.add(ParagraphStyle(name=name, fontName=font, fontSize=size,
                             leading=leading, spaceAfter=after, textColor=color))


def p(text, style='BodyReport'):
    return Paragraph(text, styles[style])


def h(text):
    return p(text, 'SectionReport')


def table(headers, rows, widths, highlight=()):
    data = [[p(x, 'HeadReport') for x in headers]]
    data += [[p(str(x), 'CellReport') for x in row] for row in rows]
    result = Table(data, colWidths=widths, repeatRows=1, hAlign='LEFT')
    commands = [
        ('BACKGROUND', (0, 0), (-1, 0), NAVY),
        ('VALIGN', (0, 0), (-1, -1), 'TOP'),
        ('LEFTPADDING', (0, 0), (-1, -1), 8),
        ('RIGHTPADDING', (0, 0), (-1, -1), 8),
        ('TOPPADDING', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 8),
        ('LINEBELOW', (0, 1), (-1, -1), .3, colors.HexColor('#D8E1E7')),
    ]
    for row in range(2, len(data), 2):
        commands.append(('BACKGROUND', (0, row), (-1, row), GRAY))
    for row in highlight:
        commands.append(('BACKGROUND', (0, row), (-1, row), colors.HexColor('#FFF1D9')))
    result.setStyle(TableStyle(commands))
    return result


def mode(row):
    return ('No exclusions' if row['case'] == 'none' else
            '70 exclusions' if row['case'] == '70' else
            '8589 + Kill Switch' if row['kill_switch'] else '8589 exclusions')


def footer(canvas, doc):
    canvas.saveState()
    canvas.setStrokeColor(colors.HexColor('#D8E1E7'))
    canvas.line(44, 35, A4[0] - 44, 35)
    canvas.setFont('Helvetica', 8)
    canvas.setFillColor(MUTED)
    canvas.drawString(44, 23, 'Community validation | AmneziaVPN 5.0.3.0 + Linux route fix | 2026-10-15')
    canvas.drawRightString(A4[0] - 44, 23, str(doc.page))
    canvas.restoreState()


def build(output):
    story = []
    def add(*items):
        story.extend(items)

    verdict = Table([[p('<b>Result:</b> all 8589 IPv4 exclusions were applied and '
        'cleaned up correctly with the patched client. The fix is suitable for a '
        'community pilot in the tested self-hosted AmneziaWG 2 scenario.')]],
        colWidths=[WIDTH])
    verdict.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, -1), LIGHT),
        ('BOX', (0, 0), (-1, -1), .6, TEAL),
        ('LEFTPADDING', (0, 0), (-1, -1), 12),
        ('RIGHTPADDING', (0, 0), (-1, -1), 12),
        ('TOPPADDING', (0, 0), (-1, -1), 12),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 5),
    ]))
    add(p('Linux split tunneling<br/>with large route lists', 'TitleReport'),
        p('Isolated validation report | 15 October 2026 | English public edition', 'SmallReport'),
        verdict, Spacer(1, 13), h('Scope and baseline'),
        table(['Parameter', 'Tested configuration'], [
            ['Source', 'Official tag 5.0.3.0, commit de93650a9073. Routing fix commit: 59089ca.'],
            ['Input', '8589 valid, non-overlapping IPv4 CIDRs; 829925-byte export. Private fixture is not distributed.'],
            ['Tunnel', 'Real self-hosted AmneziaWG 2 server, independent temporary test peer, MTU 1376.'],
            ['Isolation', 'Separate user/network/PID/mount/IPC namespaces, settings, firewall, virtual display, and slirp4netns networking.'],
        ], [96, WIDTH - 96]), Spacer(1, 13), h('Routing outcome'),
        table(['Variant', 'Applied / expected', 'Extra routes<br/>after Disconnect'], [
            ['Upstream, 70', '70 / 70', '0'],
            ['Upstream, 8589', '110 / 8589', '111'],
            ['Patched, 8589', '8589 / 8589', '0'],
            ['Patched + Kill Switch', '8589 / 8589', '0'],
        ], [205, 135, WIDTH - 340], highlight=(2,)), Spacer(1, 10),
        p('The upstream full-list run reported <b>Connected</b> while missing 8479 exclusions. '
          'Success was assessed by every CIDR, gateway/interface choice, real traffic, and cleanup; '
          'the GUI status alone was not a routing check.'),
        h('Confirmed cause'), p('The original gateway lookup accumulated the entire multipart '
          'netlink route dump in an 8 KiB buffer. Large tables exhausted it; error exits also '
          'leaked sockets. The patch reads datagrams individually, chooses the main-table IPv4 '
          'default route by metric, and closes the socket on every exit.', 'SmallReport'))

    add(PageBreak(), p('Performance and setup cost', 'HeadingReport'),
        p('Each patched mode used two external 10 MB HTTPS downloads, three private 20 MB HTTP '
          'downloads through the tunnel, and three private 8 MB HTTP uploads. Values are medians '
          'in decimal Mbit/s. Approximately <b>416 MB</b> of payload was transferred.'),
        table(['Mode', 'External HTTPS<br/>download, n=2', 'Tunnel HTTP<br/>download, n=3', 'Tunnel HTTP<br/>upload, n=3'],
              [[mode(r), f"{r['https_download']['median']:.2f}",
                f"{r['download_to_vps']['median']:.2f}", f"{r['upload_to_vps']['median']:.2f}"]
               for r in D['matrix']], [159, 116, 116, WIDTH - 391]), Spacer(1, 12),
        p('<b>Interpretation:</b> external HTTPS showed no evident throughput reduction with the '
          'full list in this small sample. It does not prove a speed improvement or a guaranteed '
          'line rate. Private download samples ranged from 5.37 to 66.76 Mbit/s; the variance and '
          'additional user-mode NAT prevent a reliable attribution of median differences to the list.'),
        h('Connection and disconnection'),
        table(['Mode', 'Connect,<br/>seconds', 'Disconnect,<br/>seconds', 'Small HTTPS<br/>median, n=5'],
              [[mode(r), f"{r['connect_s']:.2f}", f"{r['disconnect_s']:.2f}",
                f"{r['https_request_median_s']:.3f} s"] for r in D['matrix']],
              [159, 100, 107, WIDTH - 366]), Spacer(1, 12),
        p('Three additional full-list cycles connected in 12.27-12.54 seconds and disconnected '
          'in approximately 12.23 seconds. The normal production executable connected in 12.51 '
          'seconds; its GUI Disconnect button restored the baseline in 11.88 seconds.'),
        h('Remaining setup overhead'),
        p('Gateway discovery is still repeated during individual route changes. The full list '
          'therefore increases setup and teardown time, especially with Kill Switch. Batched '
          'route operations and carefully invalidated gateway caching are follow-up work, '
          'outside this patch.'),
        h('Measurement boundary'),
        p('These are measurements inside the isolated test network. Absolute throughput should '
          'be measured again during a real desktop pilot. The failed upstream full-list run '
          'is not a valid speed or setup-time baseline because it did not install the full list.', 'SmallReport'))

    add(PageBreak(), p('Reliability and recovery', 'HeadingReport'),
        table(['Check', 'Observed result'], [
            ['Import/export', '8589 entries in and out; identical CIDR sets in private test settings.'],
            ['Repeated full-list cycles', '3 cycles: no missing routes, HTTPS succeeded, two-route baseline restored every time.'],
            ['Route churn', '562 unrelated route changes during setup; no missing exclusions; HTTPS succeeded.'],
            ['Kill Switch', 'Both cached-DNS HTTPS probes timed out when test-server UDP was blocked; HTTPS recovered after unblocking.'],
            ['Normal production executable', 'All 8589 destinations had correct gateway/interface selection. Six HTTPS probes over 60 seconds passed.'],
            ['Open file descriptors', 'Upstream full-list service: 8495 FDs. Patched service: 19 connected, 14 after each Disconnect; no accumulation observed.'],
            ['Resident memory', 'Service approximately 60-61 MiB. GUI approximately 250 MiB under Xvfb/Mesa software rendering.'],
        ], [145, WIDTH - 145]), Spacer(1, 13), h('Network-change recovery was not established'),
        p('Taking the virtual uplink down and up removed its default route. The sandbox lacked '
          'NetworkManager/DHCP restoration; the first recovery probe failed. Reconnect tests '
          'passed after explicitly restoring the private default route. This does not validate '
          'automatic recovery after physical Wi-Fi/Ethernet changes.'),
        h('GUI termination and service lifetime'),
        p('SIGTERM stopped the GUI while the separate service retained the tunnel and routes. '
          'Relaunching the normal GUI and pressing Disconnect cleared them. Disconnect through '
          'the client before replacing or rolling back the installation.'),
        h('Existing connection and cleanup'),
        p('Across 36.3 minutes, all 73 host HTTPS checks succeeded. Original process identities '
          'and start times, installed/configuration file hashes, host routes, and policy rules '
          'were unchanged. The temporary peer and benchmark listener were removed and the '
          'isolated processes stopped.', 'SmallReport'))

    add(PageBreak(), p('Release decision and limits', 'HeadingReport'),
        p('<b>Recommendation:</b> prepare a labelled community pilot release for the tested '
          'self-hosted AmneziaWG 2 use case. The patch resolves the reproduced large-table '
          'routing failure. The main measured trade-off is slower connection setup/teardown.'),
        h('Build and update policy'),
        p('The optional fork release preset labels the application '
          '<b>5.0.3.0-large-routes.1</b> and disables the existing upstream in-app update path. '
          'Updates are manual through the fork. The standard upstream configuration retains '
          'its defaults. Linux x86_64 installer provenance and checksums are recorded separately '
          'in CI/release assets.'),
        h('Deployment and rollback'),
        p('Keep a private settings backup and a known-good official installer. Verify release '
          'checksums, disconnect in the GUI, and schedule an interruption before installation. '
          'The package replaces the upstream installation/service; it is not a side-by-side app. '
          'Verify the community version label, full-list routing, Disconnect, and reconnect. '
          'For rollback, disconnect and reinstall the saved official package.'),
        h('Unvalidated behavior'),
        p('IPv6 internet access, other VPN protocols, application split tunneling, multi-day '
          'uptime, physical network-change recovery, and real NetworkManager/systemd-resolved '
          'integration remain unvalidated. Sandbox DNS was configured explicitly. The Kill '
          'Switch probes cover the tested IPv4 HTTPS path, not a comprehensive leak audit.'),
        p('The independent build did not include upstream CI-provided Gateway configuration '
          '(startup error 1105). The self-hosted tunnel worked; official Free/Premium service '
          'screens and API-based updates were not validated.'),
        h('Reproducibility and publication'),
        p('The public regression generates 8589 synthetic routes and runs the production Linux '
          'function body against the upstream control in a private network namespace. The '
          'control failed at 200 and 8589 routes, leaking one descriptor per failed lookup. '
          'All patched probes passed, including 100 repeated lookups, multiple tables/metrics, '
          'a non-default gateway, and a gateway change.'),
        p('The repository includes an English Markdown report, allowlisted numeric samples, '
          'and build/install/rollback instructions. The private list, credentials, server '
          'identifiers, and local machine identifiers are excluded. End-to-end measurements '
          'describe the routing patch before release packaging; a successful installer build '
          'does not repeat the real-server validation.', 'SmallReport'),
        p('Sources: <link href="https://github.com/amnezia-vpn/amnezia-client/releases/tag/5.0.3.0" '
          'color="#08786C">upstream 5.0.3.0</link>; '
          '<link href="https://github.com/amnezia-vpn/amnezia-client/issues/3090" '
          'color="#08786C">related upstream issue #3090</link>. '
          'All numerical results are observations from the isolated validation.', 'SmallReport'))

    output.parent.mkdir(parents=True, exist_ok=True)
    doc = SimpleDocTemplate(str(output), pagesize=A4, leftMargin=44, rightMargin=44,
                            topMargin=40, bottomMargin=49,
                            title='AmneziaVPN Linux large-route split tunneling - isolated validation',
                            author='Community validation', subject='Linux gateway route dump fix')
    doc.build(story, onFirstPage=footer, onLaterPages=footer)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', type=Path, default=Path('output/pdf/amnezia-linux-large-routes-report-en.pdf'))
    args = parser.parse_args()
    build(args.output)
    print(args.output)
