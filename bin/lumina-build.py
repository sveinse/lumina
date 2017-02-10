#!/usr/bin/env python

import os
import re
import argparse

description = '''
A build helper tool for the Lumina builds
'''

# Path our base
base = os.path.realpath(os.path.join(os.path.split(
        os.path.abspath(__file__))[0], '..'))

RE_VERSION=re.compile(r'(.*)(^\s*__version__\s*=\s*[\'"])([0-9.]+)([\'"].*)$', re.M|re.S|re.I)


def get_version(fname):
    with open(fname, 'r') as f:
        verraw = f.read()

    m = RE_VERSION.search(verraw)
    if not m:
        raise Exception("%s: Does not seem to containt a VERSION" %(fname,))
    return m.group(3)


def set_version(fname, version):
    with open(fname, 'r') as f:
        verraw = f.read()

    newver = RE_VERSION.sub(r'\g<1>\g<2>%s\g<4>' %(version), verraw)

    with open(fname, 'w') as f:
        f.write(newver)


#
# == COMMAND HANDLERS
#

def cmd_version(args):
    fname = os.path.join(base, args.file)
    print get_version(fname)


def cmd_newversion(args):
    fname = os.path.join(base, args.file)
    version = get_version(fname)

    print "Setting version '%s' in '%s' (Old version: '%s')" %(args.version, args.file, version)
    set_version(fname, args.version)


def cmd_parse(args):

    fname = os.path.join(base, args.file)

    # -- Read the file into memory
    lines = []
    with open(fname, 'r') as f:
        lines = f.readlines()

    # -- Get all the replacement names
    pardict = {}
    for line in lines:
        pardict.update({k: None for k in re.findall(r'{{[\w]+}}', line)})

    # -- Get all the parameters from the environment
    #    NOTE! This is a potential huge security hole
    import subprocess
    for k in pardict:
        envvar = 'cmd_' + k[2:-2]
        if envvar not in os.environ:
            raise Exception("Environment variable '%s' does not exist" %(envvar))

        cmd = os.environ[envvar]
        exe = subprocess.Popen(cmd, shell=True, stdout=subprocess.PIPE)
        out = exe.stdout.read()
        errcode = exe.wait()
        if errcode:
            raise Exception("Command '%s' failed with error code %s" %(cmd, errcode))
        out = out.strip('\n')

        pardict[k] = out

    # -- Parse the output text
    out = ''
    for line in lines:
        rawline = line
        extra = []

        # O(N^2) -- not especially efficient
        for param in pardict:
            if param in line:

                newtext = pardict[param]
                if '\n' not in newtext:
                    line = line.replace(param, newtext)
                else:
                    # When the replacement text consists of multiple line
                    # replace the first line, and repeat the same line
                    # as many times needed for the replacement string. Note
                    # that other parameters will not be replaced on the
                    # repeated lines.
                    for i, ntline in enumerate(newtext.split('\n')):
                        if i == 0:
                            line = line.replace(param, ntline)
                        else:
                            extra.append(rawline.replace(param, ntline))

        out += line
        if extra:
            out += ''.join(extra)

    print out,



#
# == MAIN
#

# == Parse args
parser = argparse.ArgumentParser(description=description)
cmdpar = parser.add_subparsers(title='command', help='Command to execute')

# == version
verpar = cmdpar.add_parser('version')
verpar.add_argument('file', metavar='FILENAME', help='Input file to read version from')
verpar.set_defaults(func=cmd_version)

# == newversion
newverpar = cmdpar.add_parser('newversion')
newverpar.add_argument('file', metavar='FILENAME', help='Input file to set version to')
newverpar.add_argument('version', metavar="VERSION", help='New version to set')
newverpar.set_defaults(func=cmd_newversion)

# == changelog
parsepar = cmdpar.add_parser('parse')
parsepar.add_argument('file', metavar='FILENAME', help='Input file to parse')
parsepar.set_defaults(func=cmd_parse)

# == Parse and execute
opts = parser.parse_args()
opts.func(opts)
