%define name sfa
%define version 5.0
%define taglevel 0

%define release %{taglevel}%{?pldistro:.%{pldistro}}%{?date:.%{date}}
%global python_sitearch	%( python -c "from distutils.sysconfig import get_python_lib; print get_python_lib(1)" )
%{!?python_sitelib: %define python_sitelib %(%{__python} -c "from distutils.sysconfig import get_python_lib; print get_python_lib()")}

Name: %{name}
Version: %{version}
Release: %{release}
Source0: %{name}-%{version}.tar.bz2
License: GPL
Group: Applications/System
BuildRoot: %{_tmppath}/%{name}-%{version}-%{release}-buildroot

# xxx TODO : package cron.d/

Vendor: PlanetLab
Packager: PlanetLab Central <support@planet-lab.org>
Distribution: PlanetLab
URL: %{SCMURL}

Summary: Server-side for SFA, generic implementation derived from PlanetLab
Group: Applications/System
BuildRequires: make

# for uuidgen - used in db password generation
Requires: util-linux-ng
# for the registry
Requires: postgresql >= 8.2, postgresql-server >= 8.2
Requires: python3-pygresql
Requires: python3-psycopg2
Requires: python3-sqlalchemy
Requires: python3-migrate
# and of course the bulk of it
Requires: sfa-common

%package common
Summary: Python libraries for SFA, generic implementation derived from PlanetLab
Group: Applications/System
Requires: python3
Requires: python3-pyOpenSSL
Requires: python3-m2crypto
Requires: python3-dateutil
Requires: python3-lxml
# %if "%{distro}" == "Fedora" && "%{distrorelease}" <= "27"
# Requires: python-ZSI
# %else
# Requires: python2-zsi
# %endif
# Requires: libxslt-python
Requires: xmlsec1-openssl-devel

%package client
Summary: sfi, the SFA experimenter-side CLI
Group: Applications/System
Requires: sfa-common
Requires: pyOpenSSL >= 0.7

%package plc
Summary: the SFA layer around MyPLC
Group: Applications/System
Requires: sfa

%package iotlab
Summary: the SFA layer around IotLab
Group: Applications/System
Requires: sfa

%package dummy
Summary: the SFA layer around a Dummy Testbed
Group: Applications/System
Requires: sfa

%package sfatables
Summary: sfatables policy tool for SFA
Group: Applications/System
Requires: sfa

%package tests
Summary: unit tests suite for SFA
Group: Applications/System
Requires: sfa-common

%description
This package provides the registry, aggregate manager and slice
managers for SFA.  In most cases it is advisable to install additional
package for a given testbed, like e.g. sfa-plc for a PlanetLab tesbed.

%description common
This package contains the python libraries for SFA both client and server-side.

%description client
This package provides the client side of the SFA API, in particular
sfi.py, together with other utilities.

%description plc
This package implements the SFA interface which serves as a layer
between the existing PlanetLab interfaces and the SFA API.

%description iotlab
The SFA driver for IotLab.

%description dummy
The SFA driver for a Dummy Testbed.

%description sfatables
sfatables is a tool for defining access and admission control policies
in an SFA network, in much the same way as iptables is for ip
networks. This is the command line interface to manage sfatables

%description tests
Provides some binary unit tests in /usr/share/sfa/tests

%prep
%setup -q

%build
make VERSIONTAG="%{version}-%{taglevel}" SCMURL="%{SCMURL}"

%install
rm -rf $RPM_BUILD_ROOT
make VERSIONTAG="%{version}-%{taglevel}" SCMURL="%{SCMURL}" install DESTDIR="$RPM_BUILD_ROOT"

%clean
rm -rf $RPM_BUILD_ROOT

%files
/lib/systemd/system/*.service
%{_bindir}/sfa-start.py*
%{_bindir}/sfaadmin.py*
%{_bindir}/sfaadmin
%{_bindir}/keyconvert.py*
%{_bindir}/sfa-config-tty
%{_bindir}/sfa-config
%{_bindir}/sfa-setup.sh
%config /etc/sfa/default_config.xml
%config (noreplace) /etc/sfa/aggregates.xml
%config (noreplace) /etc/sfa/registries.xml
%config (noreplace) /etc/sfa/api_versions.xml
/usr/share/sfa/migrations
/usr/share/sfa/examples

%files common
%{python_sitelib}/sfa/__init__.py*
%{python_sitelib}/sfa/trust
%{python_sitelib}/sfa/storage
%{python_sitelib}/sfa/util
%{python_sitelib}/sfa/server
%{python_sitelib}/sfa/methods
%{python_sitelib}/sfa/generic
%{python_sitelib}/sfa/managers
%{python_sitelib}/sfa/importer
%{python_sitelib}/sfa/rspecs
%{python_sitelib}/sfa/client

%files client
%config (noreplace) /etc/sfa/sfi_config
%{_bindir}/sfi*.py*
%{_bindir}/sfi
%{_bindir}/get*.py*
%{_bindir}/setRecord.py*
%{_bindir}/sfascan.py*
%{_bindir}/sfascan
%{_bindir}/sfadump.py*
%{_bindir}/sfax509.py*

%files plc
%defattr(-,root,root)
%{python_sitelib}/sfa/planetlab
/etc/sfa/pl.rng
/etc/sfa/credential.xsd
/etc/sfa/top.xsd
/etc/sfa/sig.xsd
/etc/sfa/xml.xsd
/etc/sfa/protogeni-rspec-common.xsd
/etc/sfa/topology

%files iotlab
%{python_sitelib}/sfa/iotlab

%files dummy
%{python_sitelib}/sfa/dummy

%files sfatables
/etc/sfatables/*
%{_bindir}/sfatables
%{python_sitelib}/sfatables

%files tests
%{_datadir}/sfa/tests

# arbitrary choice here, subject to manual tweaks if needed
# this is in line with default_config.xml
# no need to enable sfa-db, will be activated as a dependency
%post
systemctl enable sfa-aggregate
systemctl enable sfa-registry
true

%preun
if [ "$1" = 0 ] ; then
    for service in sfa-aggregate sfa-registry sfa-db; do
        systemctl is-enabled $service && systemctl disable $service
        systemctl is-active $service && systemctl stop $service
    done
fi
true

%postun
if [ "$1" -ge "1" ] ; then
    for service in sfa-db sfa-registry sfa-aggregate; do
        systemctl is-active $service && systemctl restart $service
    done
fi
true

%changelog
* Fri Mar 29 2019 Thierry Parmentelat <thierry.parmentelat@inria.fr> - sfa-5.0-0
- ported to python3 - no other change

* Mon Jan 07 2019 Thierry <Parmentelat> - sfa-4.0-2
- have shebangs mention python2 since it is what this version runs on
- use rpm names in python2-something for expressing dependencies
- remove build dependency to python-setuptools
- Handle C-BAS hrn format with "\" (Loic)
- sfa-start does not daemonize anymore (this is handled by systemd)
- a little nicer logs when troubleshooting auth issues
- use systemctl in Makefile when syncing

* Wed May 30 2018 Thierry <Parmentelat> - sfa-4.0-1
- systemd service files install in /lib instead of /usr/lib for ubuntus
- removed all features relating to slice manager
- removed all features relating to component manager

* Mon May 28 2018 Thierry <Parmentelat> - sfa-4.0-0
- expose geni_api_versions as https://
- avoid publishing non-relevant entries in GetVersion
- fixes in the IoT-lab driver (thanks Loic)
- reviewed logging policy, less awkward and more reliable; /var/log/sfa{,-import}.log should now be alive and time rotate
- rewrote init-style startup script into systemd-native services: sfa-aggregate and sfa-registry, that both depend on sfa-db
- huge cleanup, removed everything related to init.d; debian; flash-policy; max aggregate; federica, openstack/nova and nitos drivers

* Fri Mar 16 2018 Thierry <Parmentelat> - sfa-3.1-22
- pl: tweaks for exposing country / city on nodes from site tags if set
- pl: tweaks for exposing hardware_types on nodes from node tag 'hardware_type' if set
- pl: fix exposing granularity
- sfaresetgids.py: a utility to reset gids when a update of the tolpevel gis is needed
- iotlab: various tweaks
- patch backported from plcapi about issues with xmlrpc and unicode under fedora >= 24

* Fri Jan 13 2017 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-21
- sfax509 command can run openssl x509 on all the parts of a gid
- bugfix in sfi when running the discover subcommand
- PEP8'ed a substantial part of the code
- additional debug in chain verification
- sfi myslice more robust - ignores broken slices
- new sfi introspect
- for myslice: the trust/ package should be python3-ready
- * provided that m2crypto is
- * although the devel version of m2crypto wroks just fine for us
- * even if it's incomplete for other aspects that we do not care about

* Thu Dec 17 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-20
- minor fixes for migrating on fedora23

* Tue Dec 08 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-19
- imported changes from GENI as reported - Aaron Helsinger
- minimal changes so that parts can be imported from nepi/py3
- iotlab driver : fix ASAP jobs with state != Waiting, Running - Frederic
- sfi client more accurately advertises rspec version - Loic
- + bugfix in initscript

* Mon Jun 08 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-18
- incorporated Frederic Saint Marcel's addition of ASAP management tag

* Fri Jun 05 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-17
- workaround for 'name' not being exposed properly by List() on authority objects
- fix a corner case in PL importer
- trashed module registry_manager_openstack

* Thu Jun 04 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-16
- added a new builtin column 'name' for authorities in the sfa registry
- this is kept in sync with MyPLC's site names when relevant
- sfa update -t authority thus now has a new -n/--name option
- sfi register or update can specify record type on only 2 characters (au, us, no, or sl)
- reviewed Describe and Allocate wrt slice tags for a PL AM:
- Describe now exposes all slice tags with a 'scope' being 'sliver' or 'slice'
- Allocate now by default ignores incoming slice tags
- Allocate's options can mention 'pltags' among 'ignore', 'append', 'sync'
- default being 'ignore'
- in 'ignore' mode, slice tags are unchanged in the PL db
- in 'append' mode, slice tags from the rspec are added to the db unless
- they are already present
- in 'sync' mode, the code attempts to leave the PL db in sync with the tags
- provided in rspec; this can be dangerous and is thus no longer the default
- behaviour

* Thu Apr 23 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-15
- major rework of the iotlab driver, that uses an IoT-lab REST API
- and so does not need to interact with LDAP and OAR directly
- deprecated cortexlab driver altogether
- cosmetic changes in displaying credentials, rights and certificates
- for hopefully more readable error messages
- always start postgresql if not running (ignore /etc/myplc-release)
- does not need lxc=enter-namespace anymore for make sync

* Thu Apr 09 2015 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-14
- for SSL & python-2.7.9: ignore server verification
- assume 2.7: remove compat code - always use HTTPSConnection (not HTTPS anymore)
- fix: Reset GIDs works even if user has no pub_key
- tweak for ubuntu (that does not have systemctl)
- iotlab driver:  fix ldap account creation at each lease
- miscell cosmetic & layout

* Mon Dec 01 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-13
- bugfix - was adding extraneous backslashes in email address when attempting to AddPerson

* Mon Sep 15 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-12
- getting closer with the pip/pypi packaging

* Mon Sep 15 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-11
- various tweaks for the openlab demo
- first stab at uploading onto a pypi (for pip install sfa)

* Wed Aug 20 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-10
- rewrote an optimized version of verify_persons in the PL driver:
- Allocate and Provision should now perform much faster
- in the bargain, changed the way dummy persons are created by SFA:
- the sfa email is used when free, otherwise a fake email is made up from hrn
- e.g. hrn=onelab.inria.thierry_parmentelat -> email=thierry_parmentelat@onelab.inria.stub
- verify_chain debug flow does not up any more by default
- various fixes in the iotlab driver

* Mon Jul 21 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-9
- Register can change the user keys using 'reg-keys' as well as 'keys'
- also accept a single string rather than a list of keys
- remove 'geni_api' from the registry GetVersion (which is not based on geni anymore)
- bump the 'sfa' tag in the same registry GetVersion to 3
- remove all mutable used as default arguments

* Thu Jun 05 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-8
- bugfix, sfi remove was broken

* Wed Jun 04 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-7
- sfi return code should be more meaningful - not yet for all commands though
- DEFAULT_CREDENTIAL_LIFETIME now 28 days (was 31)
- dropped support for legacy credentials
- bugfix: short-lived credentials triggered a bug with UTC translated into localtime
- further minor cleanup of timestamp formats

* Mon Jun 02 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-6
- iotlab driver: Allocate uses OAR
- iotlab driver: using actual_caller_hrn

* Thu May 29 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-5
- Slice Manager is down by default
- sfi renew -l/--as-long-as-possible and e.g. sfi renew <> +2[d|w|m]
- also renew tries to find a max date for renewal instead of bailing out
- sfaclientlib file names scheme keeps track of user as well as object for credentials
- none fields get removed before sending over xmlrpc - partially for now
- cleanup on time formats and - hopefully timezones
- cleanup on speaking_for
- Allocate passes actual_caller_hrn as part of options to driver
- iotlab driver and leases
- new modules abac_credential, credential_factory and speaksfor_util

* Tue May 06 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-4
- for register and update, client is expected to set
- reg-researchers rather than researcher
- reg-pis rather than pi
- although the old forms are still supported
- renamed sfi add into sfi register (add still works)
- sfaadmin to return a meaningful exit code when fails
- fix for sfadump
- plimporter to report and ignore person or slice without a hrn
- add support for stuff like sfi update -t slice -x the.slice.hrn -r none

* Thu Apr 03 2014 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-3
- fix for user hrn's that have a dash in their leaf
- fix for names of GENI federates
- fix for SFA_MAX_SLICE_RENEW

* Thu Feb 20 2014 Mohamed Larabi <mohamed.larabi@inria.fr> - sfa-3.1-2
- -- Core
- added support for geni_extend_alap (as long as possible) in RenewSliver.
- adding support for geni_speaking_for option,
- -- RSpecs
- Add support for Ofelia OpenFlow RSpecs
- -- PlanetLab
- Set Admins as PI's of the top authority while importing.
- -- IoTLab
- Iotlab and cortexlab ported to geni-v3.
- Moving methods using the SFA db and api object from Shell to Driver.
- Propagating the changes in iotlabimporter, iotlabaggregate and iotlabslices.
- Iotlab now using sfa database for the special table lease_table.
- Using alchemy.py classes to create a session to the DB.
- Cleaning and documenting.
- Fix Allocate() API call
- -- client
- handle single slivers.
- fix sfi.py version and trusted.
- -- PlanetLab
- handle single slivers by Provision(), Delete() and PerformOperationalAction().
- fix foreign slices mgt in sliver_to_slice_xrn() and check_sliver_credentials().
- wider mgt of new slice url and description.
- -- Packaging
- rename senslab package into iotlab.
- don't package xml-builder anymore.
- fix debian/ubuntu packaging.

* Tue Dec 10 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.1-1
- -- core
- clean up rspecs.
- GENIv3 rspecs enhirits everything from pgv2.
- fix dbsession mgt by attributing each incoming API call has its own dbsession.
- update all drivers and v2_to_v3_adapter according to dbsession fix.
- fix DB migration.
- -- client
- fix sfi.py myslice.
- sfi.py new option "my_pkcs12".
- sfi.py defaulr rspec version is GENIv3
- sfi.py trusted target either Registry interface or Slice interface.
- -- PlanetLab
- rebase all pl driver operations around the objects HRNs.
- ignore objects (Site/Slice/Person/Node) coming from MyPLC peering.
- importer ignores sites with tag sfa_created='True'.
- -- IoTLab
- In progress writing of native AM API v3 compliant driver.

* Thu Oct 10 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.0-2
- -- core
- Extend all versions of rspecs in order to support "links" and "channels" management methods
- several fixes aroung Rspecs in order to make the code usable by 3rd-party tools
- expose PL node tags in PGv2 and GENIv3 rspecs
- fix default slivers mgt in sfav1 rspecs
- fix SM and AM urn format in GetVersion
- fix sfaadmin.py to handle extra testbed-dependent info
- -- PlanetLab
- Better management of external Slices/Persons/Sites
- Importer ignores external Slices/Persons/Sites
- -- Nitos
- uniformize Leases management
- address channels with urn
- -- IotLab
- Renaming slab folders, files and variables to iotlab, the new name of the platform.
- New class ParsingResourcesFull in Oarrestapi file. Contain all the parsing nodes functions.
- Adding a mobile field to iotlab rspec and a mobility type attribute .
- Granularity changed to 60 sec.
- Fixing returned rspec in GetSlices and GetLeases.
- Corrections in import (importing nodes)
- More testis in script files under testbeds/iotlab/tests . Creation of Rspecs request models under r testbeds/iotlab/tests /tests_rspec
- Lease filtering by date added in GetLeases.
- Commenting and cleaning

* Wed Jun 19 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-3.0-1
- AM API v3-based first implementation.
- planetlab native V3 driver
- dummy native V3 driver
- introduction of v2_to_v3_adapter
- lease times in RFC3339 date format, not epoch
- mostly in line with geni-v2 for non-v3 issues like packaging and all

* Tue Feb 26 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-25
- sfi and sfaadmin list now share the same display code for related objs
- support for advertising alternate api urls - for other API versions - api_versions.xml
- cleaned up GID class
- senslab: improved importer
- senslab: add site to SlabLocation from Location
- senslab: new class JsonPage
- senslab:  fix debian packaging
- federica: fix list_slices

* Tue Jan 29 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-24
- merged the senslab driver from git.f-lab.fr
- merged the teagle flavour
- debian packaging should work much better
- added debug messsages for when db connection fails

* Sun Jan 20 2013 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-23
- minor fix in registry
- fix for sfi gid, use clientbootstrap
- support for debians and ubuntus (packaging and initscript)
- deprecated cm package altogether
- pl flavour, minor fix for tags
- various fixes for the dummy flavour

* Sun Dec 16 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-22
- suited (and required) to run with plcapi-5.1-5 b/c of changes to AddPerson
- tweaks in nitos importer
- improvements to sfaadmin check-gid

* Tue Dec 11 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-21
- PL importer: minor fixes for corner cases
- PL importer: also handles last_updated more accurately
- sfi update can be used to select a key among several in PL
- sfi add/update usage message fixes (no more record)
- new feature sfaadmin registry check_gid [-a]

* Mon Dec 03 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-20
- fix 2 major bugs in PL importer
- esp. wrt GID management against PLC key

* Wed Nov 28 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-19
- nicer sfi delegate, can handle multiple delegations and for authorities(pi) as well

* Wed Nov 28 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-18
- support fordelegation in sfaclientlib
- sfi delegate fixed
- other delegation-related sfi option trashed
- new config (based on ini format)
- new dummy driver and related package
- pl importer has more explicit error messages
- credential dump shows expiration

* Tue Oct 16 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-17
- bugfix in forwarding Resolve requests
- various fixes in the nitos driver wrt keys and users

* Mon Oct 01 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-16
- various tweaks for the nitos driver

* Wed Sep 26 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-15
- first stab at a driver for the NITOS/OMF testbed (sep. pkg)
- deeper cleanup of the data-dependencies between SFA and the testbed
- in particular, sfi create issues Resolve(details=False)
- for that purpose, Resolve exposes reg-* keys for SFA builtins
- which in turn allows sfi list to show PIs, slice members and keys
- NOTE: sfa-config-tty is known to be broken w/ less frequently used func's
- Shows stacktrace when startup fails (DB conn, wrong flavour, etc..)

* Mon Sep 17 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-14
- configurable data-dir (/var/lib/sfa)
- no more dependent on myplc-config
- some support for hrns with _ instead of \.
- fix for PL importing in presence of gpg keys
- DeleteSliver returns True instead of 1 in case of success
- Various improvements on the openstack/nova side
- new package sfa-nitos

* Wed Jul 11 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-13
- bugfix that prevented to call 'sfi create' - (was broken in sfa-2.1-12)
- sfi to remove expired credentials

* Tue Jul 10 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.1-12
- Update Openstack driver to support Essex release/
- Fix authority xrn bug.


* Thu Jun 07 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-11
- review packaging - site-packages/planetlab now come with sfa-plc
- new package sfa-federica
- clientbin moved one step upwards

* Wed Jun 6 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.1-10
- fix bug in sfi update()

* Sun Jun 03 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-9
- fix broken sfa.util.xrn class for lowercase

* Sat Jun 02 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-8
- new 'void' generic_flavour for running in registry-only mode
- first shot at refactoring importers - probably needs more work
- openstack: various enhancements
- sfi interface to registry not based on xml files anymore
- sfi show sorts result on record key
- bugfix in sfa update on users with a pl-backed registry

* Mon May 14 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-7
- renamed sfa/plc into sfa/planetlab
- plxrn moved in sfa/planetlab as well
- bugfix for sfaadmin reg update --pi <>

* Sat May 12 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-6
- native data model now has a authority x user (PI) relationship
- no call to 'augment_records_with_testbed_info' for GetCredential
- which means, registry can now be used without an underlying testbed
- reviewed code about relationships b/w objects and related in pl driver
- reviewed PL import wrt roles and pis
- removed mentions to is_enabled in driver
- small changes in update_relation* in driver interface
- sfaadmin: can create authorities and attach pi users to them
- sfaadmin: categories can be abbreviated
- sfi list and sfaadmin list have a new -r/--recursive option
- this means that List now supports an (optional) 'options' argument
- sfi config can display config vars
- sfaadmin code in sfa.client + /usr/bin/sfaadmin shortcut

* Mon Apr 16 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.1-5
- make sync now supports vserver or lxc.
- Added slice expiration and login info to SliverStatus response.
- Fixed CreateSliver bug that causes the method to fail if any node element is missing
  the 'component_name' attribute.
- Fixed various bugs that caused SFA to generate invalid or incorrect sliver ids.

* Tue Mar 20 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.1-4
- Introduced new administrative command line script, sfaadmin.py. Removed various single
 purpose scripts and migrated their functionality into sfaadmin.py.
- Refactored Registry import scripts.
- Removed SQLAlchemy dependency from sfi.py.
- Fixed bugs in sfi.py
- Registry, Aggregate and SliceManager now support the OpenStack framework.

* Fri Feb 24 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-3
- slice x researcher rel. in database,
- plimporter to maintain that, as well as user.email, and more robust
- ongoing draft for sfaadmin tool
- support for a federica driver
- support for a nova/euca driver
- no more sfa-clean-peer-records script

* Wed Feb 08 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-2
- registry database has user's keys and mail (known as v0 for migrate)
- pl importer properly maintains user's keys and mail
- pl driver now to handle 'role' when adding person record (exp.)
- first draft of federica driver with config section
- SFA_GENERIC_FLAVOUR in usual variables for sfa-config-tty
- plus, from master as of tag merged-in-sfa-2.1-2:
- disk_image revisited
- new nova_shell nova_driver & various tweaks for openstack

* Fri Jan 27 2012 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.1-1
- uses sqlalchemy and related migrate
- thorough migration and upgrade scheme
- sfa-import.py and sfa-nuke.py (no more -plc), uses FLAVOUR
- trashed dbinfo stuff in auth hierarchy
- data model still has little more than plain records
- checkpoint tag, not yet intended for release

* Wed Jan 25 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.0-10
- client: added -R --raw sfi cmdline option that displays raw server response.
- client: request GENI RSpec by default.
- server: remove database dependencies from sfa.server.sfaapi.
- server: increased default credential lifetime to 31 days.
- bugfix: fixed bug in sfa.storage.record.SfaRecord.delete().
- bugfix: fixed server key path in sfa.server.sfa-clean-peer-records.
- bugfix: fixed bug in sfa.server.sfa-start.install_peer_certs().

* Sat Jan 7 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.0-9
- bugfix: 'geni_api' should be in the top level struct, not the code struct
- bugfix: Display the correct host and port in 'geni_api_versions' field of the GetVersion
          output returned by the Aggregate Manager.
- bugfix: sfa.util.sfatime now handles numeric string inputs correctly.
- bugfix: sfa.util.sfatime.datetime_to_epoch() returns integers instead of doubles.
- bugfix: Fixed bug that prevented the rspec parser from identifying an rspec's schema when
          there is extra whitespace in the schemaLocation field.
- bugfix: Fixed bug that caused PlanetLab initscripts from showing up in the PGv2 and GENIv3
          advertisement rspecs.
- bugfix: <login> RSpec element should contain the 'username' attribute.
- bugfix: Use sfa.util.plxrn.PlXrn to parse the login_base (authority) out of a urn.

* Wed Jan 4 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.0-8
- bugfix: Fixed a bug in the sfa-import-plc.py script that caused the script to
  exit when it encountered a user with an invalid public key.
- server: imporved logging in sfa-import-plc.py

* Tue Jan 3 2012 Tony Mack <tmack@cs.princeton.edu> - sfa-2.0-7
- bugfix: Fixed appending public keys in CreateSliver
- bugfix: Fixed various bugs in the PGv2/GENIv3 request, advertisement and manifest rspecs.
- client: -c --current option allows users to request the current/uncached rspec.
- server: Added 'geni_api_versions' field to GetVersion() output.
- server: Moved PLC specific code from sfa.importer.sfaImport to sfa.importer.sfa-import-plc.

* Fri Dec 16 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-6
- bugfix: sfi was not sending call_id with ListResources to v2 servers
- SFA_API_DEBUG replaced with SFA_API_LOGLEVEL
- PlDriver / PlShell : PLCAPI methods now explicitly go to the shell

* Wed Dec 14 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-5
- client: sfi -a / -p deprecated (use -s instead)
- client: sfi cleaned up
- client: sfi has backward support for APIv1 aggregates again
- server: only APIv2 is supported and should be rather strict
- server: settings for turning on/off caching in sm or am
- server: plc-dependant code has moved from aggregate to pldriver
- server: driver interface extended accordingly

* Fri Dec 09 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-4
- screwed up previous tag

* Fri Dec 09 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-3
- client side revisited with a bootstrap library
- client side has a new source layout
- various (nasty) bug fixes wrt options and call_id

* Tue Dec 06 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-2
- various fixes in rspecs for sfav1&slice tags
- uses 'geni_rspec_version' and not just 'rspec_version'
- example flavour for the max testbed
- embryo for an sfa client library
- topology.py moved into plc
- sql: table is named records; record_types are enforced
- sql: table creation cleaned up

* Wed Nov 30 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-2.0-1
- cleaned up all references to SFA_*_TYPE in config
- enable cache at the aggregate by default
- registry now uses the driver in a sensible way (see managers/driver.py)
- slice manager supports sfav1/pgv2 neighbours
- get_key renamed into get_key_from_incoming_ip
- new sfa.storage module for record/table and all db-related stuff
- db schema in sfa.storage.sfa.sql
- init.d and cron.d move one step up
- cleaned up rspec/ directory
- add deps to pyopenssl and myplc-config
- start support for new API (return value)
- plc.remoteshell removed, use plshell instead
- plshell uses a 'capability' auth method whenever possible
- various tweaks in rspec elements
- made dependency on sfatables softer

* Thu Nov 24 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.1-5
- sfa should now be started *before* the initial import
- sfa to use its own database (default sfa) - can run without myplc
- server calls support optional 'options'
- client sends options in argument when needed
- fix infinite getattr recursion in elements/element.py
- error codes in line with geni

* Fri Nov 18 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.1-4
- fixed links and attributes in rspecs
- minor cleanup in the API methods, and more consistent names in manager methods

* Thu Nov 17 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.1-3
- ongoing refoactoring towards more genericity
- passes tests again although known issues remain with attributes/tags

* Mon Nov 07 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.1-2
- checkpoint tag: use SFA_GENERIC_FLAVOUR instead of SFA_*_TYPE
- improvements in the pgv2 rspecs
- driver separated from api
- code starts moving around where it belongs
- sfascan caches getversion across invokations
- vini topology extracted as a config file

* Fri Oct 28 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.1-1
- first support for protogeni rspecs is working
- vini no longer needs a specific manager
- refactoring underway towards more flexible/generic architecture

* Thu Sep 15 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-36
- Unicode-friendliness for user names with accents/special chars.
- Fix bug that could cause create the client to fail when calling CreateSliver for a slice that has the same hrn as a user.
- CreaetSliver no longer fails for users that have a capital letter in their URN.
- Fix bug in CreateSliver that generated incorrect login bases and email addresses for ProtoGENI requests.
- Allow files with .gid, .pem or .crt extension to be loaded into the server's list of trusted certs.
- Fix bugs and missing imports


* Tue Aug 30 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-35
- new method record.get_field for sface

* Mon Aug 29 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-34
- new option -c to sfa-nuke-plc.py
- CreateSliver fixed for admin-only slice tags

* Wed Aug 24 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-32
- Fixed exploit that allowed an authorities to issue certs for objects that dont belong to them.
- Fixed holes in certificate verification logic.
- Aggregates no longer try to lookup slice and person records when processing CreateSliver requests. Clients are now required to specify this info in the 'users' argument.
- Added 'boot_state' as an attribute of the node element in SFA rspec.
- Non authority certificates are marked as CA:FALSE.

* Tue Aug 16 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-32
- fix typo in sfa-1.0-31 tag.
- added CreateGid() Registry interface method.

* Tue Aug 16 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-31
- fix typo in sfa-1.0-30 tag

* Tue Aug 16 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-30
- Declare namespace and schema location in the credential.
- Fix bug that prevetend connections from timing out.
- Fix slice delegation.
- Add statistics to slicemaanger listresources/createsliver rspec.
- Added SFA_MAX_SLICE_RENEW which allows operators to configure the max ammout
  of days a user can extend their slice expiration.
- CA certs are only issued to objects of type authority

* Fri Aug 05 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-29
- tag 1.0-28 was broken due to typo in the changelog
- new class sfa/util/httpsProtocol.py that supports timeouts

* Thu Aug 4 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-28
- Resolved issue that caused sfa hold onto idle db connections.
- Fix bug that caused the registry to use the wrong type of credential.
- Support authority+sm type.
- Fix rspec merging bugs.
- Only load certs that have .gid extension from /etc/sfa/trusted_roots/
- Created a 'planetlab' extension to the ProtoGENI v2 rspec for supporting
 planetlab hosted initscripts using the <planetlab:initscript> tag
- Can now handle extraneous whitespace in the rspec without failing.

* Fri Jul 8 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-27
- ProtoGENI v2 RSpec updates.
- Convert expiration timestamps with timezone info in credentials to utc.
- Fixed redundant logging issue.
- Improved SliceManager and SFI client logging.
- Support aggregates that don't support the optional 'call_id' argument.
- Only call get_trusted_certs() at aggreage interfaces that support the call.
- CreateSliver() now handles MyPLC slice attributes/tags.
- Cache now supports persistence.
- Hide whitelisted nodes.

* Tue Jun 21 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-26
- fixed issues with sup authority signing
- fixed bugs in remove_slivers and SliverStatus

* Thu Jun 16 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-25
- fix typo that prevented aggregates from operating properly

* Tue Jun 14 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-24
- load trusted certs into ssl context prior to handshake
- client's logfile lives in ~/.sfi/sfi.log

* Fri Jun 10 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-23
- includes a change on passphrases that was intended in 1.0-22

* Mon Jun 6 2011 Tony Mack <tmack@cs.princeton.edu> - sfa-1.0-22
- Added support for ProtoGENI RSpec v2

* Wed Mar 16 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-21
- stable sfascan
- fix in initscript, *ENABLED tags in config now taken into account

* Fri Mar 11 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-20
- some commits had not been pushed in tag 19

* Fri Mar 11 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-19
- GetVersion should now report full URLs with path
- scansfa has nicer output and new syntax (entry URLs as args and not options)
- dos2unix'ed flash policy pill

* Wed Mar 09 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-18
- fix packaging again for f8

* Wed Mar 09 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-17
- fix packaging (apparently broken in 1.0-16)
- first working version of sfascan
- tweaks in GetVersion for exposing hrn(AM) and full set of aggregates(SM)
- deprecated the sfa_geni_aggregate config category

* Tue Mar 08 2011 Andy Bavier <acb@cs.princeton.edu> - sfa-1.0-16
- Fix build problem
- First version of SFA scanner

* Mon Mar 07 2011 Andy Bavier <acb@cs.princeton.edu> - sfa-1.0-15
- Add support for Flash clients using flashpolicy
- Fix problems with tag handling in RSpec

* Wed Mar 02 2011 Andy Bavier <acb@cs.princeton.edu> - sfa-1.0-14
- Modifications to the Eucalyptus Aggregate Manager
- Fixes for VINI RSpec
- Fix tag handling for PL RSpec
- Fix XML Schema ordering for <urn> element

* Tue Feb 01 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-13
- just set x509 version to 2

* Wed Jan 26 2011 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-12
- added urn to the node area in rspecs
- conversion to urn now exports fqdn
- sfa-import-plc.py now creates a unique registry record for each SFA interface

* Thu Dec 16 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-11
- undo broken attempt for python-2.7

* Wed Dec 15 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-10
- SMs avoid duplicates for when call graph has dags;
- just based on network's name, when a duplicate occurs, one is just dropped
- does not try to merge/aggregate 2 networks
- also reviewed logging with the hope to fix the sfa startup msg:
- TypeError: not all arguments converted during string formatting

* Tue Dec 07 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-9
- verify credentials against xsd schema
- Fix SM to SM communication
- Fix bug in sfa.util.sfalogging, sfa-import.py now logs to sfa_import.log
- new setting session_key_path

* Tue Nov 09 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-8
- fix registry credential regeneration and handle expiration
- support for setting slice tags (min_role=user)
- client can display its own version: sfi.py version --local
- GetVersion to provide urn in addition to hrn
- more code uses plxrn vs previous helper functions
- import replaces '+' in email addresses with '_'

* Fri Oct 22 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-7
- fix GetVersion code_tag and add code_url

* Fri Oct 22 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-6
- extend GetVersion towards minimum federation introspection, and expose local tag

* Wed Oct 20 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-5
- fixed some legacy issues (list vs List)
- deprecated sfa.util.namespace for xrn and plxrn
- unit tests ship as the sfa-tests rpm

* Mon Oct 11 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-2
- deprecated old methods (e.g. List/list, and GetCredential/get_credential)
- NOTE:  get_(self_)credential both have type and hrn swapped when moving to Get(Self)Credential
- hrn-urn translations tweaked
- fixed 'service sfa status'
- sfa-nuke-plc has a -f/--file-system option to clean up /var/lib/authorities (exp.)
- started to repair sfadump - although not usable yet
- trust objects now have dump_string method that dump() actually prints
- unit tests under review
- logging cleanup ongoing (always safe to use sfalogging.sfa_logger())
- binaries now support -v or -vv to increase loglevel
- trashed obsolete sfa.util.client

* Mon Oct 04 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-1.0-1
- various bugfixes and cleanup, improved/harmonized logging

* Tue Sep 07 2010 Tony Mack <tmack@cs.princeton.edu> - sfa-0.9-16
- truncate login base of external (ProtoGeni, etc) slices to 20 characters
  to avoid returning a PLCAPI exception that might confuse users.
- Enhance PLC aggregate performace by using a better filter when querying SliceTags.
- fix build errors.

* Tue Aug 24 2010 Tony Mack <tmack@cs.princeton.edu> - sfa-0.9-15
- (Architecture) Credential format changed to match ProtoGENI xml format
- (Architecture) All interfaces export a new set of methods that are compatible
   with the ProtoGeni Aggregate spec. These new methods are considered a
   replacement  for the pervious methods exported by the interfaces. All
   previous methods are still exported and work as normal, but they are
   considered deprecated and will not be supported in future releases.
- (Architecture) SFI has been updated to use the new interface methods.
- (Architecture) Changed keyconvet implementation from c to python.
- (Architecture) Slice Manager now attempts looks for a delegated credential
  provided by the client before using its own server credential.
- (Archiceture) Slice Interface no longers stores cache of resources on disk.
  This cache now exists only in memory and is cleared when service is restarted
  or cache lifetime is exceeded.
- (Performance) SliceManager sends request to Aggregates in parallel instead
  of sequentially.
- (Bug fix) SFA tickets now support the new rspec format.
- (Bug fix) SFI only uses cahced credential if they aren't expired.
- (Bug fix) Cerdential delegation modified to work with new credential format.
- (Enhancement) SFI -a --aggregatge option now sends requests directly to the
  Aggregate instead of relaying through the Slice Manager.
- (Enhancement) Simplified caching. Accociated a global cache instance with
  the api handler on every new server request, making it easier to access the
  cache and use in more general ways.

* Tue May 11 2010 Tony Mack <tmack@cs.princeton.edu> - sfa-0.9-11
- SfaServer now uses a pool of threads to handle requests concurrently
- sfa.util.rspec no longer used to process/manage rspecs (deprecated). This is now handled by sfa.plc.network and is not backwards compatible
- PIs can now get a slice credential for any slice at their site without having to be a member of the slice
- Registry records for federated peers (defined in registries.xml, aggregates.xml) updated when sfa service is started
- Interfaces will try to fetch and install gids from peers listed in registries.xml/aggregates.xml if gid is not found in /etc/sfa/trusted_roots dir
- Component manager does not install gid files if slice already has them
- Server automatically fetches and installs peer certificats (defined in registries/aggregates.xml) when service is restarted.
- fix credential verification exploit (verify that the trusted signer is a parent of the object it it signed)
- made it easier for root authorities to sign their sub's certifiacate using the sfa-ca.py (sfa/server/sfa-ca.py) tool

* Thu Jan 21 2010 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-10
- This tag is quite same as the previous one (sfa-0.9-9) except that the vini and max aggregate managers are also updated for urn support.  Other features are:
- - sfa-config-tty now has the same features like plc-config-tty
- - Contains code to support both urn and hrn
- - Cleaned up request_hash related stuff
- - SM, AM and Registry code is organized under respective managers
- - Site and Slice synchronization across federated aggregates
- - Script to generate sfa_component_config

* Fri Jan 15 2010 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-9
- sfa-config-tty now has the same features like plc-config-tty
- Contains code to support both urn and hrn
- Cleaned up request_hash related stuff
- SM, AM and Registry code is organized under respective managers
- Slice synchronization across federated aggregates
- some bugs are fixed

* Wed Jan 06 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-0.9-8
- checkpoint with fewer mentions of geni

* Tue Jan 05 2010 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-0.9-7
- checkpointing
- this is believed to pass the tests; among other things:
- reworked configuration based on the myplc config with xml skeleton (no more sfa_config)

* Mon Nov 16 2009 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-6
- This tag includes:
- - Sfatables
- - Preliminary version of hash based authentication
- - Initial code for Component Manager
- - Authority structure is moved to /var/lib/sfa/
- - some bug-fixes

* Fri Oct 09 2009 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-5
- Create_slice and get_resources methods are connected to sfatables.
- Other features include compatibility with RP, handling remote objects created as part of federation, preliminary version of sfatables, call tracability and logging.

* Wed Oct 07 2009 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-4
- Bug fix on update and remove_peer_object methods
- Compatibility with RP, preliminiary version of sfatables, call tracability and logging

* Mon Oct 05 2009 anil vengalil <avengali@sophia.inria.fr> - sfa-0.9-3
- Compatibility with RP, two additional methods to handle remote objects, call tracability and logging, PLCDB now has single table for sfa records, preliminary version of sfatables (still under development)

* Fri Sep 18 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-0.9-2
- compatibility with RefreshPeer
- incremental mechanism for importing PLC records into SFA tables
- unified single database (still inside the underlying PLC db postgresql server)
- includes/improves call traceability and logging features
- several bug fixes

* Thu Sep 17 2009 Baris Metin <tmetin@sophia.inria.fr>
- added libxslt-python dependency

* Thu Sep 10 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - sfa-0.9-1
- unified single SFA database in the PLC-DB
- upcalls from  PLCAPI to SFA methods
- SFA call traceability and logging features
- many bug fixes
- includes first/rough version of sfatables for policy implementation

* Thu Jul 23 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-6
- snapshot after the GEC5 demo
- should be the last tag set in the geniwrapper module, are we are now moving to the sfa module

* Wed Jul 15 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-5
- snapshot july 15 - has gone through superficial manual testing
- hopefully a good basis for gec5 demo
- multi-dir sfi client tested as well

* Wed Jul 08 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-4
- rename geniwrapper.spec into sfa.spec

* Wed Jul 08 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-3
- clean up in xmlrpc/soap, --protocol option to chose between both
- keyconvert packaged in /usr/bin, no /usr/share/keyconvert anymore
- hopefully more helpful context in case of crashes when importing
- bugfixes for using only /etc/sfa for site-dep files
- bugfixes in wsdl generation

* Mon Jul 06 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-2
- cleanup of the config area; no dependency to a PLC config anymore as sfa can be run in standalone
- config variables in sfa_config now start with SFA_ and not GENI_
- config.py can be loaded even with no config present

* Sun Jul 05 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.8-1
- first step for cleanup and reorganization
- mass-renaming from geni to sfa (some are still needed)
- sfa/trust implements the security architecture

* Wed Jul 01 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-7
- snapshot for reproducible builds

* Thu Jun 25 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-6
- snapshot for the convenience of alpha users

* Tue Jun 16 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-5
- build fix - keyconvert was getting installed in /usr/share/keyconvert/keyconvert

* Tue Jun 16 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-4
- ongoing work - snapshot for 4.3-rc9

* Wed Jun 03 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-3
- various fixes

* Sat May 30 2009 Thierry Parmentelat <thierry.parmentelat@sophia.inria.fr> - geniwrapper-0.2-2
- bugfixes - still a work in progress

* Mon May 18 2009 Baris Metin <tmetin@sophia.inria.fr>
- initial package


%define module_current_branch 0.2
