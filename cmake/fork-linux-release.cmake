# Optional preset for the community Linux release. CMake/IFW keep a numeric
# package version; the application and release filename carry an explicit label.
set(AMNEZIAVPN_VERSION "5.0.3.0" CACHE STRING "Upstream base version" FORCE)
set(AMNEZIA_BUILD_LABEL "-large-routes.1" CACHE STRING "Community build label" FORCE)
set(CLIENT_ENABLE_APP_UPDATES 0 CACHE STRING "Use manual fork releases" FORCE)
