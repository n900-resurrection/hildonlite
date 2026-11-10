# hildonlite: Python 3 layer over GTK 2 / Hildon, as a .deb (python3-hildonlite) and as a pip package. Targets and conventions: ../../mk/app.mk
override APP     := hildonlite
PKG      := python3-hildonlite
VERSION ?= 0.3.0
include ../../mk/app.mk
