"""
Create an FITS file with rectified 2D spectra for all slits/orders.

.. include common links, assuming primary doc root is up one directory
.. include:: ../include/links.rst
"""

import numpy as np
from pathlib import Path

import matplotlib.pyplot as plt

from pypeit.scripts import scriptbase
from pypeit import spec2dobj, specobjs, msgs
from pypeit.core import coadd
from pypeit.core.wavecal import wvutils
from pypeit.core.moment import moment1d
from astropy.io import fits
from astropy.wcs import WCS

from IPython import embed


spec2file = 'Science/spec2d_d0225_0054-16045h_DEIMOS_20190225T145727.158.fits'
detname = None


class Rectify2DSpec(scriptbase.ScriptBase):

    @classmethod
    def get_parser(cls, width=None):
        parser = super().get_parser(description='Create an FITS file with rectified '
                                                '2D spectra for all slits/orders.', width=width)

        parser.add_argument('files', type = str, nargs='*', help = 'PypeIt spec2d file(s)')
        parser.add_argument('--no_rot', default=False, action='store_true',
                            help='Do not rotate the rectified image to have wavelength '
                                 'on the x-axis.')
        parser.add_argument('--try_old', default=False, action='store_true',
                            help='Attempt to load old datamodel versions.  A crash may ensue..')
        return parser

    @staticmethod
    def main(args):

        chk_version = not args.try_old

        for spec2file in args.files:
            msgs.info(f'Processing file: {spec2file}')
            # Get list of detectors
            hdr = fits.getheader(spec2file)
            detnames = hdr['HIERARCH ALLSPEC2D_DETS'].split(',')

            # Empty primary HDU
            hdu_list = [fits.PrimaryHDU()]

            for detname in detnames:
                msgs.info(f'DETECTOR: {detname}')
                spec2d = spec2dobj.Spec2DObj.from_file(spec2file, detname, chk_version=chk_version)
                pad = 10  # pixels to pad on each side
                slitmask = spec2d.slits.slit_img(pad=pad, flexure=spec2d.sci_spat_flexure)
                slit_ids = spec2d.slits.spat_id

                # get the wave grid
                # Do we have the spec1d file?
                spec1dfile = spec2file.replace('spec2d', 'spec1d')
                if Path(spec1dfile).is_file():
                    sobjs = specobjs.SpecObjs.from_fitsfile(spec1dfile, chk_version=False)
                    on_det = sobjs.DET == detname
                    waves, gpms = [], []
                    for sobj in sobjs[on_det]:
                        # we use the BOX extraction here for simplicity
                        if sobj.has_box_ext() and np.any(sobj.BOX_MASK):
                            waves.append(sobj.BOX_WAVE)
                            gpms.append(sobj.BOX_MASK)
                else:
                    # extract the wave and gpm from the spec2d object directly (taken from coadd2d)
                    waves, gpms = [], []
                    slits_left, slits_right, _ = spec2d.slits.select_edges()
                    row = np.arange(slits_left.shape[0])
                    box_radius = 3 # pixels
                    # Loop on the slits
                    for kk, spat_id in enumerate(slit_ids):
                        mask = slitmask == spat_id
                        # Create apertures at 5%, 50%, and 95% of the slit width to cover full range of wavelengths
                        # on this slit
                        trace_spat = slits_left[:, kk][:, np.newaxis] + np.outer((slits_right[:, kk] - slits_left[:, kk]),
                                                                                 [0.05, 0.5, 0.95])
                        box_denom = moment1d(spec2d.waveimg * mask > 0.0, trace_spat, 2 * box_radius, row=row)[0]
                        wave_box = moment1d(spec2d.waveimg * mask, trace_spat, 2 * box_radius,
                                            row=row)[0] / (box_denom + (box_denom == 0.0))
                        gpm_box = box_denom > 0.
                        waves += [wave for (wave, gpm) in zip(wave_box.T, gpm_box.T) if np.any(gpm)]
                        gpms += [(wave > 0.) & gpm for (wave, gpm) in zip(wave_box.T, gpm_box.T) if np.any(gpm)]


                if len(waves) == 0:
                    msgs.warn(f'There is a problem with the wavelengths on det {detname}. '
                              f'The RECTIFIED 2D spectral image will not be created.')
                    continue
                wmax, wmin = np.ceil(spec2d.waveimg[spec2d.waveimg>0].max()), np.floor(spec2d.waveimg[spec2d.waveimg>0].min())
                wave_grid, wave_grid_mid, dsamp = wvutils.get_wave_grid(waves=waves, gpms=gpms,
                                                                        wave_grid_min=wmin, wave_grid_max=wmax)

                imgrect_list = []
                for slitidx, slit_id in enumerate(slit_ids):
                    this_mask = (slitmask == slit_id)
                    slit_cen = spec2d.slits.center[:,slitidx]
                    mask = spec2d.bpmmask.mask == 0

                    imgrect_dict = coadd.compute_coadd2d([slit_cen], [spec2d.sciimg],
                                                         [spec2d.ivarmodel],[spec2d.skymodel],
                                                         [mask],[this_mask],
                                                         [spec2d.waveimg], wave_grid, single_frame=True)
                    imgrect_list.append(imgrect_dict)


                # Get dimensions for each slit
                nspat_vec = np.array([cdict['nspat'] for cdict in imgrect_list])

                nspec_rect = len(wave_grid)
                nspat_rect = int(np.sum(nspat_vec) + (spec2d.slits.nslits + 1) * pad)

                # Initialize output array
                image_rect = np.zeros((nspec_rect, nspat_rect))
                ivar_rect = np.zeros((nspec_rect, nspat_rect))
                mask_rect = (np.zeros((nspec_rect, nspat_rect), dtype=bool))
                waveimg_rect = np.zeros((nspec_rect, nspat_rect))

                # Loop over slits and rectify each one
                spat_left = pad
                for islit, imgrect_dict in enumerate(imgrect_list):
                    spat_righ = spat_left + nspat_vec[islit]
                    ispat = slice(spat_left, spat_righ)

                    # Get wavelength array for this slit
                    wave_slit = imgrect_dict['wave_mid']
                    nspec_slit = len(wave_slit)

                    # Interpolate onto a common wavelength grid
                    for ispat_slit in range(nspat_vec[islit]):
                        # Get data for this spatial pixel
                        flux = imgrect_dict['imgminsky'][:nspec_slit, ispat_slit]
                        ivar = imgrect_dict['sciivar'][:nspec_slit, ispat_slit]

                        # Interpolate onto a common wavelength grid
                        flux_interp = np.interp(wave_grid, wave_slit, flux,
                                               left=0., right=0.)
                        ivar_interp = np.interp(wave_grid, wave_slit, ivar,
                                                left=0., right=0.)
                        # Determine a valid wavelength range for this slit
                        valid = (wave_grid >= wave_slit.min()) & \
                                (wave_grid <= wave_slit.max())

                        # Assign to output arrays
                        image_rect[:, spat_left + ispat_slit] = flux_interp
                        ivar_rect[:, spat_left + ispat_slit] = ivar_interp
                        mask_rect[:, spat_left + ispat_slit] = np.logical_not(valid)

                    # Create a wavelength image for this slit
                    waveimg_rect[:, ispat] = np.repeat(wave_grid[:, np.newaxis],
                                                      nspat_vec[islit], axis=1)

                    spat_left = spat_righ + pad

                # Rotate if desired
                if not args.no_rot:
                    image_rect = np.rot90(image_rect)
                    # Create HDU with WCS header
                    hdu = fits.ImageHDU(image_rect, name=detname)
                    hdu.header['CTYPE1'] = 'LAMBDA   '
                    hdu.header['CUNIT1'] = 'Angstrom'
                    hdu.header['CDELT1'] = dsamp
                    hdu.header['CRPIX1'] = 0
                    hdu.header['CRVAL1'] = wave_grid[0]
                    hdu.header['CTYPE2'] = 'LINEAR  '
                    hdu.header['CUNIT2'] = 'pixel'
                    hdu.header['CDELT2'] = 1.
                    hdu.header['CRPIX2'] = 0
                    hdu.header['CRVAL2'] = 0.
                else:
                    # Create HDU with WCS header
                    hdu = fits.ImageHDU(image_rect, name=detname)
                    hdu.header['CTYPE1'] = 'LINEAR  '
                    hdu.header['CUNIT1'] = 'pixel'
                    hdu.header['CDELT1'] = 1.
                    hdu.header['CRPIX1'] = 0
                    hdu.header['CRVAL1'] = 0.
                    hdu.header['CTYPE2'] = 'LAMBDA   '
                    hdu.header['CUNIT2'] = 'Angstrom'
                    hdu.header['CDELT2'] = dsamp
                    hdu.header['CRPIX2'] = 0
                    hdu.header['CRVAL2'] = wave_grid[0]
                # Add other keywords
                hdu.header['NSPEC'] = nspec_rect
                hdu.header['NSPAT'] = nspat_rect
                hdu.header['WAVEMIN'] = wave_grid[0]
                hdu.header['WAVEMAX'] = wave_grid[-1]
                hdu.header['DETNAME'] = detname
                hdu.header['PIPELINE'] = hdr['PIPELINE']
                hdu.header['PYPELINE'] = hdr['PYPELINE']
                hdu.header['PYP_SPEC'] = hdr['PYP_SPEC']

                hdu_list.append(hdu)

            # Write to file
            out_file = spec2file.replace('spec2d', 'rectified_spec2d')
            hdulist = fits.HDUList(hdu_list)
            hdulist.writeto(out_file, overwrite=True)
            print(f'Rectified images saved to {out_file}')