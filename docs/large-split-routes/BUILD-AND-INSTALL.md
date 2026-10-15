# Community Linux release

This is an unofficial, GPL-3.0 community build of AmneziaVPN based on upstream
5.0.3.0. The application version is `5.0.3.0-large-routes.1`. It targets Linux
x86_64 and the self-hosted AmneziaWG 2 scenario in the
[test report](README.md). Other upstream platforms are not released by this fork.

## Build

The `Community Linux build` GitHub Actions workflow builds on Ubuntu 22.04 with
Qt 6.10.1, Qt Installer Framework 4.7, and Conan 2.28.0. It first runs the
synthetic gateway regression against upstream 5.0.3.0 and the patched source,
then builds the normal client/service and an offline `.run` installer.

To build manually, follow the upstream prerequisites, initialize submodules,
install the same Qt modules and Qt Installer Framework, then run:

```sh
git submodule update --init --recursive
cmake -S . -B build -G Ninja -C cmake/fork-linux-release.cmake \
  -DCMAKE_BUILD_TYPE=Release \
  -DCMAKE_PREFIX_PATH=/path/to/Qt/6.10.1/gcc_64
cmake --build build --parallel 2
cd build
cpack -G IFW -D QTIFWDIR=/path/to/Qt/Tools/QtInstallerFramework/4.7
```

The optional preset keeps the CMake/installer numeric package version at
5.0.3.0, adds the community application label, and sets
`CLIENT_ENABLE_APP_UPDATES=0`. Updates are manual through this fork's releases.
The ordinary upstream configuration remains available without this preset.

Release assets include the installer, build commit/tool versions, a synthetic
regression result, license notices, the English report, and SHA-256 checksums.
GitHub's source archive does not include submodule contents; use a recursive Git
checkout to rebuild. The installer is not signed by the Amnezia project.

## Install

This package uses the existing upstream installation path, service, and settings
namespace. It is a replacement installation, not a side-by-side application.

1. Save a private backup/export of the current application settings and keep a
   known-good official installer for rollback. Backups may contain VPN secrets;
   keep them local and do not attach them to issues.
2. Download the release and verify its assets with `sha256sum -c SHA256SUMS`.
3. Schedule a connection interruption. Use **Disconnect** in the current GUI,
   then exit it. Killing the GUI can leave the service tunnel active.
4. Run the downloaded `.run` installer through the normal desktop flow. Review
   the displayed target path and administrator prompt.
5. Confirm the version label contains `large-routes.1`, connect to the intended
   self-hosted profile, and verify included/excluded destinations. Allow roughly
   10-12 seconds for the full tested list, or about 22 seconds with Kill Switch.
6. Test Disconnect and reconnect before relying on the new installation.

The upstream installer restarts/replaces the system service. Installing it will
interrupt an active tunnel; downloading or building it does not.

## Rollback and updates

Disconnect in the GUI and exit it, reinstall the saved official package, and
restore the private settings backup only if needed. Keep that backup until the
new version has been checked.

This fork does not silently apply upstream updates. When rebasing onto a new
upstream version, review the gateway implementation and rerun the synthetic
regression plus the relevant tunnel tests before creating another release.

## Known limits

- Setup and teardown remain slower with thousands of individual routes.
- Physical network-change recovery and real desktop DNS-manager integration
  need a separate pilot check; the isolated test does not cover them.
- Official Free/Premium API configuration is not included. This build is aimed
  at self-hosted connections; do not infer service compatibility from the tunnel
  results.
- A test report for the routing patch is distinct from the build provenance of
  an installer produced later in CI.
