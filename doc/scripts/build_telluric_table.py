
from importlib import resources
import os
import subprocess

from IPython import embed
import numpy

from pypeit.utils import string_table


def tellgrid_table(root, ofile):

    os.environ['TZ'] = 'UTC'
    result = subprocess.run(
        [
            'aws', '--endpoint', 'https://s3-west.nrp-nautilus.io', 's3', 'ls',
            f's3://pypeit/telluric/atm_grids/{root}', '--human-readable'
        ], capture_output=True, text=True)
    data = [l.split() for l in result.stdout.split('\n')[:-1]]
    data = [['File', 'Size', 'Last Modified (UTC)']] + [
        [d[4], ' '.join(d[2:4]), ' '.join(d[:2])] for d in data
    ]
    lines = string_table(numpy.atleast_1d(data), delimeter='rst')
    with open(ofile, 'w') as f:
        f.write(lines)


def main():
    output_root = resources.files('pypeit').parent / 'doc' / 'include'
    root = 'TelFit'
    ofile = output_root / f'{root}_files.rst'
    tellgrid_table(root, ofile)
    root = 'TellPCA'
    ofile = output_root / f'{root}_files.rst'
    tellgrid_table(root, ofile)


if __name__ == '__main__':
    main()
