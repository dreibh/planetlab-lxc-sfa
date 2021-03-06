#!/usr/bin/env python3



"""
Installation script for the sfa module
"""

# as fas as pushing onto pypi, I have been using this page
# http://peterdowns.com/posts/first-time-with-pypi.html
# for setting up the whole business

import sys, os, os.path
from glob import glob
import shutil
from distutils.core import setup

# check for the correct version of python
major, minor = sys.version_info [0:2]
if major <= 2:
    print ("Sorry, this version of SFA package requires python3")
    exit(1)


# while cleaning up we might not have this..
try:
    from sfa.util.version import version_tag
except:
    version_tag='cleaningup'

scripts = glob("clientbin/*.py") + [
    'config/sfa-config-tty',
    'config/sfa-config',
    'sfa/server/sfa-start.py',
    'systemd/sfa-setup.sh',
    'sfatables/sfatables',
    'keyconvert/keyconvert.py',
]

packages = [
    'sfa',
    'sfa/trust',
    'sfa/storage',
    'sfa/util',
    'sfa/server',
    'sfa/methods',
    'sfa/generic',
    'sfa/managers',
    'sfa/importer',
    'sfa/rspecs',
    'sfa/rspecs/elements',
    'sfa/rspecs/elements/versions',
    'sfa/rspecs/versions',
    'sfa/client',
    'sfa/planetlab',
    'sfa/dummy',
    'sfa/iotlab',
    'sfatables',
    'sfatables/commands',
    'sfatables/processors',
    ]

data_files = [
    ('/etc/sfa/',
     [  'config/aggregates.xml',
        'config/registries.xml',
        'config/default_config.xml',
        'config/api_versions.xml',
        'config/sfi_config',
        'config/topology',
        'sfa/managers/pl/pl.rng',
        'sfa/trust/credential.xsd',
        'sfa/trust/top.xsd',
        'sfa/trust/sig.xsd',
        'sfa/trust/xml.xsd',
        'sfa/trust/protogeni-rspec-common.xsd',
    ]),
    ('/etc/sfatables/matches/', glob('sfatables/matches/*.xml')),
    ('/etc/sfatables/targets/', glob('sfatables/targets/*.xml')),
    ('/usr/share/sfa/migrations', glob('sfa/storage/migrations/*.*') ),
    ('/usr/share/sfa/migrations/versions', glob('sfa/storage/migrations/versions/*') ),
    ('/usr/share/sfa/examples/', glob('sfa/examples/*' ) + [ 'cron.d/sfa.cron' ] ),
]

# use /lib/systemd instead of /usr/lib/systemd
# the latter would work on fedora only, the former
# will work on both fedora and ubuntu
services = ['sfa-db', 'sfa-aggregate', 'sfa-registry']
data_files.append(
    ('/lib/systemd/system',
     ['systemd/{}.service'.format(service)
      for service in services]))


# sfatables processors
processor_files = [f for f in glob('sfatables/processors/*')
                   if os.path.isfile(f)]
data_files.append(('/etc/sfatables/processors/', processor_files))
processor_subdirs = [d for d in glob('sfatables/processors/*')
                     if os.path.isdir(d)]
for d in processor_subdirs:
    etc_dir = os.path.join("/etc/sfatables/processors", os.path.basename(d))
    d_files = [f for f in glob(d + '/*') if os.path.isfile(f)]
    data_files.append((etc_dir, processor_files))


if sys.argv[1] in ['uninstall', 'remove', 'delete', 'clean']:
    python_path = sys.path
    site_packages_path = [ os.path.join(p, 'sfa') for p in python_path if p.endswith('site-packages')]
    site_packages_path += [ os.path.join(p, 'sfatables') for p in python_path if p.endswith('site-packages')]
    remove_dirs = ['/etc/sfa/', '/etc/sfatables'] + site_packages_path
    remove_bins = [ '/usr/bin/' + os.path.basename(bin) for bin in scripts ]
    remove_files = (remove_bins
                    + ["/lib/systemd/system/{}".format(x)
                       for x in services])

    # remove files
    def feedback (file, msg):
        print ("removing", file, "...", msg)
    for filepath in remove_files:
        try:
            os.remove(filepath)
            feedback(filepath, "success")
        except:
            feedback(filepath, "failed")
    # remove directories
    for directory in remove_dirs:
        try:
            shutil.rmtree(directory)
            feedback (directory, "success")
        except:
            feedback (directory, "failed")
else:
    # avoid repeating what's in the specfile already
    try:
        with open("LICENSE.txt") as l:
            license = l.read()
    except:
        license = "Could not open file LICENSE.txt"
    try:
        with open("index.html") as r:
            long_description = r.read()
    except:
        long_description = "Unable to read index.html"

    setup(
        name             = 'sfa',
        packages         = packages,
        data_files       = data_files,
        version          = version_tag,
        keywords         = ['federation', 'testbeds', 'SFA', 'SfaWrap'],
        url              = "http://svn.planet-lab.org/wiki/SFATutorial",
        author           = "Thierry Parmentelat, Tony Mack, Scott Baker",
        author_email     = "thierry.parmentelat@inria.fr, tmack@princeton.cs.edu, smbaker@gmail.com",
        download_url     = "http://build.onelab.eu/sfa/{v}/sfa-{v}.tar.gz".format(v=version_tag),
        description      = "SFA Wrapper with drivers for PlanetLab and IotLab and others",
        license          = license,
        long_description = long_description,
        scripts          = scripts,
)
