%global _smp_mflags -j1

%global debug_package   %{nil}
%global _unpackaged_files_terminate_build 0
%global _missing_build_ids_terminate_build 0
%define __debug_install_post   \
   %{_rpmconfigdir}/find-debuginfo.sh %{?_find_debuginfo_opts} "%{_builddir}/%{?buildsubdir}"\
%{nil}

%global sname deepin-daemon
%global release_name server-industry

Name:           dde-daemon
Version:        5.13.16.11
Release:        1
Summary:        Daemon handling the DDE session settings
License:        GPLv3
URL:            http://shuttle.corp.deepin.com/cache/tasks/18802/unstable-amd64/
Source0:        %{name}-%{version}.orig.tar.xz
Source1:        vendor.tar.gz

BuildRequires:  python3
BuildRequires:  golang
BuildRequires:  deepin-gettext-tools
BuildRequires:  fontpackages-devel
BuildRequires:  librsvg2-tools
BuildRequires:  pam-devel >= 1.3.1
BuildRequires:  pam >= 1.3.1
BuildRequires:  glib2-devel
BuildRequires:  gtk3-devel
BuildRequires:  systemd-devel
BuildRequires:  alsa-lib-devel
BuildRequires:  alsa-lib
BuildRequires:  pulseaudio-libs-devel
BuildRequires:  gdk-pixbuf-xlib
BuildRequires:  libnl3-devel
BuildRequires:  libnl3
BuildRequires:  libgudev-devel
BuildRequires:  libgudev
BuildRequires:  libinput-devel
BuildRequires:  libinput
BuildRequires:  librsvg2-devel
BuildRequires:  librsvg2
BuildRequires:  libXcursor-devel
BuildRequires:  libddcutil-devel
BuildRequires:  pkgconfig(sqlite3)
BuildRequires:  dde-api-devel

Requires:       bluez-libs
Requires:       deepin-desktop-base
Requires:       deepin-desktop-schemas
Requires:       dde-session-ui
Requires:       dde-polkit-agent
Requires:       rfkill
Requires:       gvfs
Requires:       iw

Recommends:     iso-codes
Recommends:     imwheel
Recommends:     mobile-broadband-provider-info
Recommends:     google-noto-mono-fonts
Recommends:     google-noto-sans-fonts

%description
Daemon handling the DDE session settings

%prep
%autosetup
tar -xf %{SOURCE1}
patch langselector/locale.go < rpm/locale.go.patch

# Fix library exec path
sed -i '/deepin/s|lib|libexec|' Makefile
sed -i '/${DESTDIR}\/usr\/lib\/deepin-daemon\/service-trigger/s|${DESTDIR}/usr/lib/deepin-daemon/service-trigger|${DESTDIR}/usr/libexec/deepin-daemon/service-trigger|g' Makefile
sed -i '/${DESTDIR}${PREFIX}\/lib\/deepin-daemon/s|${DESTDIR}${PREFIX}/lib/deepin-daemon|${DESTDIR}${PREFIX}/usr/libexec/deepin-daemon|g' Makefile
sed -i 's|lib/NetworkManager|libexec|' network/utils_test.go

for file in $(grep "/usr/lib/deepin-daemon" * -nR |awk -F: '{print $1}')
do
    sed -i 's|/usr/lib/deepin-daemon|/usr/libexec/deepin-daemon|g' $file
done

# Fix grub.cfg path
sed -i 's|boot/grub|boot/grub2|' grub2/{grub2,grub_params,theme}.go

# Fix activate services failed (Permission denied)
# dbus service
pushd misc/system-services/
sed -i '$aSystemdService=deepin-accounts-daemon.service' com.deepin.system.Power.service \
    com.deepin.daemon.{Accounts,Apps,Daemon}.service \
    com.deepin.daemon.{Gesture,SwapSchedHelper,Timedated}.service
sed -i '$aSystemdService=dbus-com.deepin.dde.lockservice.service' com.deepin.dde.LockService.service
popd
# systemd service
cat > misc/systemd/services/dbus-com.deepin.dde.lockservice.service <<EOF
[Unit]
Description=Deepin Lock Service
Wants=user.slice dbus.socket
After=user.slice dbus.socket

[Service]
Type=dbus
BusName=com.deepin.dde.LockService
ExecStart=%{_libexecdir}/%{sname}/dde-lockservice

[Install]
WantedBy=graphical.target
EOF

# Replace reference of google-chrome to chromium-browser
sed -i 's/google-chrome/chromium-browser/g' misc/dde-daemon/mime/data.json

%build
go env -w GO111MODULE=auto
export GOPATH=%{_builddir}/%{name}-%{version}/vendor:$GOPATH

BUILDID="0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n')"
%make_build GO_BUILD_FLAGS=-trimpath GOBUILD="go build -compiler gc -ldflags \"-B $BUILDID\""
#make GOPATH=/usr/share/gocode

%install
BUILDID="0x$(head -c20 /dev/urandom|od -An -tx1|tr -d ' \n')"
export GOPATH=%{_builddir}/%{name}-%{version}/vendor:$GOPATH
%make_install PAM_MODULE_DIR=%{_libdir}/security GOBUILD="go build -compiler gc -ldflags \"-B $BUILDID\""

# fix systemd/logind config
install -d %{buildroot}/usr/lib/systemd/logind.conf.d/
cat > %{buildroot}/usr/lib/systemd/logind.conf.d/10-%{sname}.conf <<EOF
[Login]
HandlePowerKey=ignore
HandleSuspendKey=ignore
EOF

%find_lang %{name}

%post
if [ $1 -ge 1 ]; then
  systemd-sysusers %{sname}.conf
  %{_sbindir}/alternatives --install %{_bindir}/x-terminal-emulator \
    x-terminal-emulator %{_libexecdir}/%{sname}/default-terminal 30
fi

%preun
if [ $1 -eq 0 ]; then
  %{_sbindir}/alternatives --remove x-terminal-emulator \
    %{_libexecdir}/%{sname}/default-terminal
fi

%postun
if [ $1 -eq 0 ]; then
  rm -f /var/cache/deepin/mark-setup-network-services
  rm -f /var/log/deepin.log 
fi

%files -f %{name}.lang
%doc README.md
%license LICENSE
%{_sysconfdir}/default/grub.d/10_deepin.cfg
%{_sysconfdir}/grub.d/35_deepin_gfxmode
%{_sysconfdir}/pam.d/deepin-auth-keyboard
%{_libexecdir}/%{sname}/
%{_prefix}/lib/systemd/logind.conf.d/10-%{sname}.conf
%{_datadir}/dbus-1/services/*.service
%{_datadir}/dbus-1/system-services/*.service
%{_datadir}/dbus-1/system.d/*.conf
%{_datadir}/icons/hicolor/*/status/*
%{_datadir}/%{name}/
%{_datadir}/dde/
%{_datadir}/polkit-1/actions/*.policy
%{_var}/lib/polkit-1/localauthority/10-vendor.d/com.deepin.daemon.Accounts.pkla
%{_var}/lib/polkit-1/localauthority/10-vendor.d/com.deepin.daemon.Grub2.pkla
%{_sysconfdir}/acpi/actions/deepin_lid.sh
%{_sysconfdir}/acpi/events/deepin_lid
%{_sysconfdir}/pulse/daemon.conf.d/10-deepin.conf
/lib/udev/rules.d/80-deepin-fprintd.rules
/var/lib/polkit-1/localauthority/10-vendor.d/com.deepin.daemon.Fprintd.pkla
/lib/systemd/system/dbus-com.deepin.dde.lockservice.service
/lib/systemd/system/deepin-accounts-daemon.service

%changelog
* Mon Jul 18 2022 konglidong <konglidong@uniontech.com> - 5.13.16.11-1
- Update to 5.13.16.11

* Sat Jan 29 2022 liweigang <liweiganga@uniontech.com> - 5.12.0.18-4
- fix build error and format spec.

* Thu Aug 26 2021 heyitao <heyitao@uniontech.com> - 5.12.0.18-3
- Update vendor.tag.gz.

* Tue Jul 20 2021 weidong <weidong@uniontech.com> - 5.12.0.18-2
- Suggest use deepin-desktop-server to provide deepin-desktop-base.

* Thu Jul 08 2021 weidong <weidong@uniontech.com> - 5.12.0.18-1
- Update 5.12.0.18.

* Thu Mar 04 2021 weidong <weidong@uniontech.com> - 5.10.0.23-10
- Update license.

* Thu Feb 18 2021 chenbo pan <panchenbo@uniontech.com> - 5.10.0.23-9
- fix build error
* Wed Sep 2 2020 chenbo pan <panchenbo@uniontech.com> - 5.10.0.23-8
- fix requires golang devel
* Wed Aug 19 2020 openEuler Buildteam <buildteam@openeuler.org> - 5.10.0.23-7
- change python37 to python3
* Thu Jul 30 2020 openEuler Buildteam <buildteam@openeuler.org> - 5.10.0.23-6
- remove golang devel
* Thu Jul 30 2020 openEuler Buildteam <buildteam@openeuler.org> - 5.10.0.23-5
- Package init

