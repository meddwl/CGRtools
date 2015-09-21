#!/usr/bin/env python
# -*- coding: utf-8 -*-
#
#  Copyright 2014 Ramil Nugmanov <stsouko@live.ru>
#  This file is part of CGR tools.
#
#  CGR tools is free software; you can redistribute it and/or modify
#  it under the terms of the GNU Affero General Public License as published by
#  the Free Software Foundation; either version 3 of the License, or
#  (at your option) any later version.
#
#  This program is distributed in the hope that it will be useful,
#  but WITHOUT ANY WARRANTY; without even the implied warranty of
#  MERCHANTABILITY or FITNESS FOR A PARTICULAR PURPOSE.  See the
#  GNU Affero General Public License for more details.
#
#  You should have received a copy of the GNU Affero General Public License
#  along with this program; if not, write to the Free Software
#  Foundation, Inc., 51 Franklin Street, Fifth Floor, Boston,
#  MA 02110-1301, USA.
#
import sys
import traceback
from CGRtools.RDFread import RDFread
from CGRtools.SDFwrite import SDFwrite
from CGRtools.CGRcore import CGRcore


def condenser_core(args):
    options = vars(args)
    inputdata = RDFread(args.input)
    outputdata = SDFwrite(**options)

    con = CGRcore(**options)
    err = 0
    num = -1
    for num, data in enumerate(inputdata.readdata()):
        if num % 100 == 0:
            print("reaction: %d" % (num + 1), file=sys.stderr)
        try:
            a = con.getFCGR(data)
            outputdata.writedata(a)
        except Exception:
            err += 1
            print('reaction %d consist errors: %s' % (num + 1, traceback.format_exc()), file=sys.stderr)
    print('%d from %d reactions condensed' % (num + 1 - err, num + 1), file=sys.stderr)
