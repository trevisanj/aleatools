#!/usr/bin/env python
# Adds the GNU GPL header to files

import glob
import os.path
import argparse


S = \
"""This file is part of {0}.

{0} is free software: you can redistribute it and/or modify
it under the terms of the GNU General Public License as published by
the Free Software Foundation, either version 3 of the License, or
(at your option) any later version.

Foobar is distributed in the hope that it will be useful,
but WITHOUT ANY WARRANTY; without even the implied warranty of
MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
GNU General Public License for more details.

You should have received a copy of the GNU General Public License
along with {0}.  If not, see <http://www.gnu.org/licenses/>.
"""



if __name__ == "__main__":

    parser = argparse.ArgumentParser(description='Add GPL header to files.')
    parser.add_argument('-c', type=str, help='Comment character(s)', required=True)
    parser.add_argument('-n', type=str, help='Program name', required=True)
    parser.add_argument('what', metavar='files', type=str, nargs='+',
                       help='Files spec with wildcards')

    args = parser.parse_args()

    S = '\n'.join([args.c+' '+x for x in S.split('\n')])

    i = 0
    dirName = "added%04d" % i
    while os.path.isdir(dirName):
        i += 1
        dirName = "added%04d" % i
    print "Files will be saved in directory `%s`" % dirName
    os.mkdir(dirName)

    for wild in args.what:
        print "+"
        print "+ Processing ", wild, '...'
        a = glob.glob(wild)
        print "+ Number of files: ", len(a)
        for fn in a:
            print "+++ Processing file", fn, "...",
            h0 = open(fn, 'r')
            s0 = h0.read()
            h0.close()
            if not 'under the terms of the GNU' in s0:
                h1 = open(os.path.join(dirName, fn), 'w')
                h1.write(S.format(args.n))
                h1.write(s0)
                h1.close()
                print 'yes'
            else:
                print 'no'
