#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (C) 2009 Derrick Moser <derrick_moser@yahoo.com>
#
# This program is free software; you can redistribute it and/or modify it under
# the terms of the GNU General Public License as published by the Free Software
# Foundation; either version 2 of the licence, or (at your option) any later
# version.
#
# This program is distributed in the hope that it will be useful, but WITHOUT
# ANY WARRANTY; without even the implied warranty of MERCHANTABILITY or FITNESS
# FOR A PARTICULAR PURPOSE.  See the GNU General Public License for more
# details.
#
# You should have received a copy of the GNU General Public License along with
# this program.  You may also obtain a copy of the GNU General Public License
# from the Free Software Foundation by visiting their web site
# (http://www.fsf.org/) or by writing to the Free Software Foundation, Inc.,
# 51 Franklin St, Fifth Floor, Boston, MA  02110-1301  USA

import glob
import os
import stat
import sys

app_path = sys.argv[0]

# print a message to stderr
def logError(s):
    sys.stderr.write('%s: %s\n' % (app_path, s))

# this install script should not be used on Windows
if os.name == 'nt':
    logError('Wrong platform.  Use scripts from the "windows-installer" directory instead.')
    sys.exit(1)

# reset the umask so files we create will have the expected permissions
os.umask(stat.S_IWGRP | stat.S_IWOTH)

# option defaults
options = { 'destdir': '/', 'prefix': '/usr/local/', 'sysconfdir': '/etc/', 'python-interpreter': '/usr/bin/env python' }
install = True
files_only = False

# process --help option
if len(sys.argv) == 2 and sys.argv[1] == '--help':
    print """Usage: %s [OPTION...]

Install or remove Diffuse.

Options:
  --help
     print this help text and quit

  --remove
     remove the program

  --destdir=PATH
     path to the installation's root directory
     default: %s

  --prefix=PATH
     common installation prefix for files
     default: %s

  --sysconfdir=PATH
     directory for installing read-only single-machine data
     default: %s

  --python-interpreter=PATH
     command for python interpreter
     default: %s

  --files-only
     only install/remove files; skip the post install/removal tasks""" % (app_path, options['destdir'], options['prefix'], options['sysconfdir'], options['python-interpreter'])
    sys.exit(0)
 
# returns the list of components used in a path
def components(s):
    return [ p for p in s.split(os.sep) if p != '' ]

# returns a relative path from 'src' to 'dst'
def relpath(src, dst):
    s1, s2, i = components(src), components(dst), 0
    while i < len(s1) and i < len(s2) and s1[i] == s2[i]:
        i += 1
    s = [ os.pardir ] * (len(s1) - i)
    s.extend(s2[i:])
    return os.sep.join(s)

# apply a set of text substitution rules on a string
def replace(s, rules, i=0):
    if i < len(rules):
        k, v = rules[i]
        a = s.split(k)
        for j in range(len(a)):
            a[j] = replace(a[j], rules, i + 1)
        s = v.join(a)
    return s

# install/remove sets of files
def processFiles(install, target, dst, src, template):
    for k, v in template.items():
        fn, dn = os.path.basename(k), os.path.dirname(k)
        srcdir, dstdir = os.path.join(src, dn), target
        dstdir = target
        for s in components(os.path.join(dst, dn)):
            dstdir = os.path.join(dstdir, s)
            # create sub-directories as needed
            if install and not os.path.isdir(dstdir):
                os.mkdir(dstdir)
        for s in glob.glob(os.path.join(srcdir, fn)):
            d = os.path.join(dstdir, os.path.basename(s))
            if install:
                # install file
                f = open(s, 'rb')
                c = f.read()
                f.close()
                if v is not None:
                    c = replace(c, v)
                print 'Installing %s' % (d, )
                f = open(d, 'wb')
                f.write(c)
                f.close()
                if k == 'bin/diffuse':
                    # turn on the execute bits
                    os.chmod(d, 0755)
            else:
                # remove file
                try:
                    os.unlink(d)
                except OSError:
                    logError('Error removing "%s".' % (d, ))

# parse command line arguments
for arg in sys.argv[1:]:
    if arg == '--remove':
        install = False
    elif arg == '--files-only':
        files_only = True
    else:
        for opt in options.keys():
            key = '--%s=' % (opt, )
            if arg.startswith(key):
                options[opt] = arg[len(key):]
                break
        else:
            logError('Unknown option "%s".' % (arg, ))
            sys.exit(1)

# validate inputs
for opt in 'prefix', 'sysconfdir':
    p = options[opt]
    c = components(p)
    if os.pardir in c or os.curdir in c:
        logError('Bad value for option "%s".' % (opt, ))
        sys.exit(1)
    c.insert(0, '')
    c.append('')
    options[opt] = os.sep.join(c)

destdir = options['destdir']
prefix = options['prefix']
sysconfdir = options['sysconfdir']
python = options['python-interpreter']

# tell the user what we are about to do
if install:
    stage = 'install'
else:
    stage = 'removal'
print '''Performing %s with:
    destdir=%s
    prefix=%s
    sysconfdir=%s
    python-interpreter=%s''' % (stage, destdir, prefix, sysconfdir, python)

# install files to prefix
processFiles(install, destdir, prefix, 'src/usr', {
        'bin/diffuse': [ ("'../../etc/diffuserc'", repr(relpath(os.path.join(prefix, 'bin'), os.path.join(sysconfdir, 'diffuserc')))), ('/usr/bin/env python', python) ],
        'share/applications/diffuse.desktop': None,
        'share/diffuse/syntax/*.syntax': None,
        'share/gnome/help/diffuse/C/diffuse.xml': [ ('/usr/', prefix), ('/etc/', sysconfdir) ],
        'share/man/man1/diffuse.1': [ ('/usr/', prefix), ('/etc/', sysconfdir) ],
        'share/omf/diffuse/diffuse-C.omf': [ ('/usr/', prefix) ],
        'share/pixmaps/diffuse.png': None
    })

# install files to sysconfdir
processFiles(install, destdir, sysconfdir, 'src/etc', { 'diffuserc': [ ('../usr', relpath(sysconfdir, prefix)) ] })

if not install:
    # remove directories we own
    for s in [ 'share/omf/diffuse', 'share/gnome/help/diffuse/C', 'share/gnome/help/diffuse', 'share/diffuse/syntax', 'share/diffuse' ]:
        d = os.path.join(destdir, os.path.join(prefix, s)[1:])
        try:
            os.rmdir(d)
        except OSError:
            logError('Error removing "%s".' % (d, ))

# do post install/removal tasks
if not files_only:
    print 'Performing post %s tasks.' % (stage, )

    if install:
        cmds = [ 'update-desktop-database',
                 'scrollkeeper-update -q -o %s' % (os.path.join(destdir, os.path.join(prefix, 'share/omf/diffuse')[1:])) ]
    else:
        cmds = [ 'update-desktop-database',
                 'scrollkeeper-update -q' ]
    for c in cmds:
        print c
        os.system(c)