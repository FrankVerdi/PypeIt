"""
Module for P200/NGPS specific methods.

.. include:: ../include/links.rst
"""
from typing import List, Optional

import numpy as np

from astropy.io import fits
from astropy import units as u
from astropy.time import Time

from pypeit import msgs
from pypeit import io
from pypeit import telescopes
from pypeit.core import framematch
from pypeit.spectrographs import spectrograph
from pypeit.core import parse
from pypeit.images import detector_container


class P200NGPSSpectrograph(spectrograph.Spectrograph):
    """
    Base class to handle P200/NGPS common code shared by all four channels.
    """
    ndet = 1
    telescope = telescopes.P200TelescopePar()
    camera = 'NGPS_X'  # Must include camera

    def init_meta(self):
        """
        Define how metadata are derived from the spectrograph files.

        That is, this associates the PypeIt-specific metadata keywords
        with the instrument-specific header cards using :attr:`meta`.
        """
        self.meta = {}
        # Required (core)
        self.meta['ra'] = dict(ext=0, card='TELRA', required_ftypes=['science', 'standard'])
        self.meta['dec'] = dict(ext=0, card='TELDEC', required_ftypes=['science', 'standard'])
        self.meta['target'] = dict(ext=0, card='NAME', compound=True, required_ftypes=['science', 'standard'])

        self.meta['dispname'] = dict(card=None, compound=True, default='VPH')
        self.meta['decker'] = dict(ext=0, card='SLITW', rtol=1e-2)
        self.meta['binning'] = dict(card=None, compound=True)

        self.meta['mjd'] = dict(ext=0, card='MJD')
        self.meta['exptime'] = dict(ext=0, card='SHUTTIME')  # SHUTTIME more accurate than EXPTIME
        self.meta['airmass'] = dict(ext=0, card='AIRMASS', required_ftypes=['science', 'standard'])

        # Extras for config and frametyping
        self.meta['dichroic'] = dict(card=None, compound=True)
        self.meta['dispangle'] = dict(card=None, rtol=1e-2, compound=True)
        self.meta['slitwid'] = dict(ext=0, card='SLITW', rtol=1e-2)
        self.meta['idname'] = dict(ext=0, card='IMGTYPE')
        self.meta['instrument'] = dict(ext=0, card='INSTRUME')

        # Lamps
        self.meta['lampstat01'] = dict(ext=0, card='LAMPBLUC')  # Blue Xe
        self.meta['lampstat02'] = dict(ext=0, card='LAMPFEAR')  # FeAr
        self.meta['lampstat03'] = dict(ext=0, card='LAMPREDC')  # Red Continuum
        self.meta['lampstat04'] = dict(ext=0, card='LAMPTHAR')  # ThAr

    def configuration_keys(self):
        """
        Return the metadata keys that define a unique instrument
        configuration.

        This list is used by :class:`~pypeit.metadata.PypeItMetaData` to
        identify the unique configurations among the list of frames read
        for a given reduction.

        Returns:
            :obj:`list`: List of keywords of data pulled from file headers
            and used to constuct the :class:`~pypeit.metadata.PypeItMetaData`
            object
        """
        return ['binning']
    
    



    def raw_header_cards(self):
        """
        Return additional raw header cards to be propagated in
        downstream output files for configuration identification.

        The list of raw data FITS keywords should be those used to populate
        the :meth:`~pypeit.spectrographs.spectrograph.Spectrograph.configuration_keys`
        or are used in :meth:`~pypeit.spectrographs.spectrograph.Spectrograph.config_specific_par`
        for a particular spectrograph, if different from the name of the
        PypeIt metadata keyword.

        This list is used by :meth:`~pypeit.spectrographs.spectrograph.Spectrograph.subheader_for_spec`
        to include additional FITS keywords in downstream output files.

        Returns:
            :obj:`list`: List of keywords from the raw data files that should
            be propagated in output files.
        """
        return ['GRATING', 'ANGLE', 'APERTURE']

    def pypeit_file_keys(self):
        """
        Define the list of keys to be output into a standard PypeIt file.

        Returns:
            :obj:`list`: The list of keywords in the relevant
            :class:`~pypeit.metadata.PypeItMetaData` instance to print to the
            :ref:`pypeit_file`.
        """
        return super().pypeit_file_keys()

    def check_frame_type(self, ftype, fitstbl, exprng=None):
        """
        Check for frames of the provided type.

        Args:
            ftype (:obj:`str`):
                Type of frame to check. Must be a valid frame type; see
                frame-type :ref:`frame_type_defs`.
            fitstbl (`astropy.table.Table`_):
                The table with the metadata for one or more frames to check.
            exprng (:obj:`list`, optional):
                Range in the allowed exposure time for a frame of type
                ``ftype``. See
                :func:`pypeit.core.framematch.check_frame_exptime`.

        Returns:
            `numpy.ndarray`_: Boolean array with the flags selecting the
            exposures in ``fitstbl`` that are ``ftype`` type frames.
        """
        good_exp = framematch.check_frame_exptime(fitstbl['exptime'], exprng)

        if ftype in ['science', 'standard']:
            return good_exp & (fitstbl['idname'] == 'SCI')

        if ftype == 'bias':
            return good_exp & (fitstbl['idname'] == 'BIAS')

        if ftype in ['pixelflat', 'trace', 'illumflat']:
            return ((good_exp & (fitstbl['idname'] == 'DOMEFLAT'))
                    | (good_exp & (fitstbl['idname'] == 'CONT')))

        if ftype in ['pinhole', 'dark']:
            return np.zeros(len(fitstbl), dtype=bool)

        if ftype in ['arc', 'tilt']:
            return good_exp & (fitstbl['idname'] == 'THAR')

        
        msgs.warn('Cannot determine if frames are of type {0}.'.format(ftype))
        return np.zeros(len(fitstbl), dtype=bool)


# ---------------------------------------------------------------------------
# G channel  –  FITS extension 1  (EXTNAME='G')
# Shape: (610, 1404)
# Orientation: specaxis=1 
# Overscan: BIASSEC=[1:31,1:610]
# Data: DATASEC=[32:1402,1:610]
# ---------------------------------------------------------------------------

class P200NGPSSpectrograph_g(P200NGPSSpectrograph):
    """
    Child to handle P200/NGPS g-Channel (blue/green) specific code
    """
    name = 'p200_ngps_g'
    camera = 'NGPS_g'
    header_name = 'NGPS_g'
    supported = True
    comment = 'g-Channel; FITS ext 1'

    # FITS extension index for this channel.
    _FITS_EXT = 1

    def get_rawimage(self, raw_file, det):
        """
        Read raw spectrograph image files and return data and relevant
        metadata needed for image processing.
        """
        return super().get_rawimage(raw_file, det=self._FITS_EXT,
                                    sec_includes_binning=True)

    def compound_meta(self, headarr: list[fits.Header], meta_key: str):
        """
        Methods to generate metadata requiring interpretation of the header
        data, instead of simply reading the value of a header card.

        Args:
            headarr (:obj:`list`):
                List of `astropy.io.fits.Header`_ objects.
            meta_key (:obj:`str`):
                Metadata keyword to construct.

        Returns:
            object: Metadata value read from the header(s).
        """
        retval = super().compound_meta(headarr, meta_key)
        if retval is not None:
            return retval

        if meta_key == 'mjd':
            return Time(headarr[0]['UTSHUT']).mjd
        elif meta_key == 'dispangle':
            return 0
        elif meta_key == 'binning':
            binspat = headarr[self._FITS_EXT]['BINSPAT']
            binspec = headarr[self._FITS_EXT]['BINSPEC']
            return parse.binning2string(binspec, binspat)
        elif meta_key == 'target':
            if 'TARGET' in headarr[0]:
                return headarr[0]['TARGET']
            else:
                return headarr[0]['IMGTYPE']
        elif meta_key == 'dichroic':
            return None
        else:
            raise PypeItError(f"Not ready for this compound meta: {meta_key}")

    def get_detector_par(self, det: int, hdu: fits.HDUList | None = None):
        """
        Return metadata for the selected detector.

        Args:
            det (:obj:`int`):
                1-indexed detector number.
            hdu (`astropy.io.fits.HDUList`_, optional):
                The open fits file with the raw image of interest.  If not
                provided, frame-dependent parameters are set to a default.

        Returns:
            :class:`~pypeit.images.detector_container.DetectorContainer`:
            Object with the detector metadata.
        """
        if hdu is None:
            binning = '1,1'
            datasec = None
            oscansec = None
        else:
            binning = self.get_meta_value(self.get_headarr(hdu), 'binning')
            # DATASEC=[32:1402,1:610] -> Python [1:610, 32:1402]
            datasec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['DATASEC']))
            # BIASSEC=[1:31,1:610] -> Python [1:610, 1:31]
            oscansec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['BIASSEC']))

        detector_dict = dict(
            binning         = binning,
            det             = 1,
            dataext         = self._FITS_EXT,
            specaxis        = 1,
            specflip        = False,
            spatflip        = False,
            platescale      = 0.5,     # arcsec/pix
            darkcurr        = 0.0,     # e-/pixel/hour
            saturation      = 65000.,
            nonlinear       = 40./45.,
            mincounts       = -1e10,
            numamplifiers   = 1,
            gain            = np.atleast_1d(2.8),  
            ronoise         = np.atleast_1d(8.5),
            datasec         = datasec,
            oscansec        = oscansec,
        )
        return detector_container.DetectorContainer(**detector_dict)

    @classmethod
    def default_pypeit_par(cls):
        """
        Return the default parameters to use for this instrument.

        Returns:
            :class:`~pypeit.par.pypeitpar.PypeItPar`: Parameters required by
            all of PypeIt methods.
        """
        par = super().default_pypeit_par()

        par['calibrations']['slitedges']['sync_predict'] = 'nearest'
        par['calibrations']['slitedges']['edge_thresh'] = 50.
        par['calibrations']['slitedges']['minimum_slit_length'] = 100
        par['calibrations']['slitedges']['min_edge_side_sep'] = 1.0

        par['scienceframe']['process']['combine'] = 'median'
        par['calibrations']['standardframe']['process']['combine'] = 'median'

        par['scienceframe']['process']['use_overscan'] = True
        par['scienceframe']['process']['sigclip'] = 4.0
        par['scienceframe']['process']['objlim'] = 5.0

        par['calibrations']['bpm_usebias'] = False

        par['calibrations']['pixelflatframe']['process']['combine'] = 'median'

        par['calibrations']['wavelengths']['lamps'] = ['ThAr']
        par['calibrations']['wavelengths']['method'] = 'full_template'
        par['calibrations']['wavelengths']['reid_arxiv'] = 'wvarxiv_p200_ngps_g_20260424T0006.fits'
        par['calibrations']['wavelengths']['rms_thresh_frac_fwhm'] = 1.0

        par['sensfunc']['algorithm'] = 'UVIS'

        par['calibrations']['biasframe']['exprng'] = [None, 0.001]
        par['calibrations']['arcframe']['exprng'] = [None, 120]
        par['calibrations']['standardframe']['exprng'] = [None, 120]
        par['scienceframe']['exprng'] = [90, None]

        return par


# ---------------------------------------------------------------------------
# I channel  –  FITS extension 2  (EXTNAME='I')
# Shape: (610, 1404) 
# Orientation: specaxis=1 
# Overscan: BIASSEC=[1:31,1:610]
# Data: DATASEC=[32:1402,1:610]
# ---------------------------------------------------------------------------

class P200NGPSSpectrograph_i(P200NGPSSpectrograph):
    """
    Child to handle P200/NGPS i-Channel specific code
    """
    name = 'p200_ngps_i'
    camera = 'NGPS_i'
    header_name = 'NGPS_i'
    supported = True
    comment = 'i-Channel; FITS ext 2'

    _FITS_EXT = 2

    def get_rawimage(self, raw_file, det):
        """
        Read raw spectrograph image files and return data and relevant
        metadata needed for image processing.

        Raw i-channel data are stored in FITS extension :attr:`_FITS_EXT`.
        """
        return super().get_rawimage(raw_file, det=self._FITS_EXT,
                                    sec_includes_binning=True)

    def compound_meta(self, headarr: list[fits.Header], meta_key: str):
        """
        Methods to generate metadata requiring interpretation of the header
        data, instead of simply reading the value of a header card.

        Args:
            headarr (:obj:`list`):
                List of `astropy.io.fits.Header`_ objects.
            meta_key (:obj:`str`):
                Metadata keyword to construct.

        Returns:
            object: Metadata value read from the header(s).
        """
        retval = super().compound_meta(headarr, meta_key)
        if retval is not None:
            return retval

        if meta_key == 'mjd':
            return Time(headarr[0]['UTSHUT']).mjd
        elif meta_key == 'dispangle':
            return 0
        elif meta_key == 'binning':
            binspat = headarr[self._FITS_EXT]['BINSPAT']
            binspec = headarr[self._FITS_EXT]['BINSPEC']
            return parse.binning2string(binspec, binspat)
        elif meta_key == 'target':
            if 'TARGET' in headarr[0]:
                return headarr[0]['TARGET']
            else:
                return headarr[0]['IMGTYPE']
        elif meta_key == 'dichroic':
            return None
        else:
            raise PypeItError(f"Not ready for this compound meta: {meta_key}")

    def get_detector_par(self, det: int, hdu: fits.HDUList | None = None):
        """
        Return metadata for the selected detector.

        Args:
            det (:obj:`int`):
                1-indexed detector number.
            hdu (`astropy.io.fits.HDUList`_, optional):
                The open fits file with the raw image of interest.  If not
                provided, frame-dependent parameters are set to a default.

        Returns:
            :class:`~pypeit.images.detector_container.DetectorContainer`:
            Object with the detector metadata.
        """
        if hdu is None:
            binning = '1,1'
            datasec = None
            oscansec = None
        else:
            binning = self.get_meta_value(self.get_headarr(hdu), 'binning')
            datasec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['DATASEC']))
            oscansec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['BIASSEC']))

        detector_dict = dict(
            binning         = binning,
            det             = 1,
            dataext         = self._FITS_EXT,
            specaxis        = 1,
            specflip        = False,
            spatflip        = False,
            platescale      = 0.5,     # arcsec/pix
            darkcurr        = 0.0,     # e-/pixel/hour
            saturation      = 65000.,
            nonlinear       = 40./45.,
            mincounts       = -1e10,
            numamplifiers   = 1,
            gain            = np.atleast_1d(2.8),
            ronoise         = np.atleast_1d(8.5),
            datasec         = datasec,
            oscansec        = oscansec,
        )
        return detector_container.DetectorContainer(**detector_dict)

    @classmethod
    def default_pypeit_par(cls):
        """
        Return the default parameters to use for this instrument.

        Returns:
            :class:`~pypeit.par.pypeitpar.PypeItPar`: Parameters required by
            all of PypeIt methods.
        """
        par = super().default_pypeit_par()

        par['calibrations']['slitedges']['sync_predict'] = 'nearest'
        par['calibrations']['slitedges']['edge_thresh'] = 50.
        par['calibrations']['slitedges']['minimum_slit_length'] = 100
        par['calibrations']['slitedges']['min_edge_side_sep'] = 1.0

        par['scienceframe']['process']['combine'] = 'median'
        par['calibrations']['standardframe']['process']['combine'] = 'median'

        par['scienceframe']['process']['use_overscan'] = True
        par['scienceframe']['process']['sigclip'] = 4.0
        par['scienceframe']['process']['objlim'] = 5.0

        par['calibrations']['bpm_usebias'] = False

        par['calibrations']['pixelflatframe']['process']['combine'] = 'median'

        par['calibrations']['wavelengths']['lamps'] = ['ThAr']
        par['calibrations']['wavelengths']['method'] = 'full_template'
        par['calibrations']['wavelengths']['reid_arxiv'] = 'wvarxiv_p200_ngps_20250131T1354.fits'  # I Channel Template
        par['calibrations']['wavelengths']['rms_thresh_frac_fwhm'] = 1.0

        par['sensfunc']['algorithm'] = 'UVIS'

        par['calibrations']['biasframe']['exprng'] = [None, 0.001]
        par['calibrations']['arcframe']['exprng'] = [None, 120]
        par['calibrations']['standardframe']['exprng'] = [None, 120]
        par['scienceframe']['exprng'] = [90, None]

        return par


# ---------------------------------------------------------------------------
# R channel  –  FITS extension 3  (EXTNAME='R')
# Shape: (610, 1404)
# Orientation: specaxis=1
# Overscan: BIASSEC=[1:31,1:610]
# Data: DATASEC=[32:1402,1:610]
# ---------------------------------------------------------------------------

class P200NGPSSpectrograph_r(P200NGPSSpectrograph):
    """
    Child to handle P200/NGPS r-Channel specific code
    """
    name = 'p200_ngps_r'
    camera = 'NGPS_r'
    header_name = 'NGPS_r'
    supported = True
    comment = 'r-Channel; FITS ext 3'

    _FITS_EXT = 3

    def get_rawimage(self, raw_file, det):
        """
        Read raw spectrograph image files and return data and relevant
        metadata needed for image processing.

        Raw r-channel data are stored in FITS extension :attr:`_FITS_EXT`.
        """
        return super().get_rawimage(raw_file, det=self._FITS_EXT,
                                    sec_includes_binning=True)

    def compound_meta(self, headarr: list[fits.Header], meta_key: str):
        """
        Methods to generate metadata requiring interpretation of the header
        data, instead of simply reading the value of a header card.

        Args:
            headarr (:obj:`list`):
                List of `astropy.io.fits.Header`_ objects.
            meta_key (:obj:`str`):
                Metadata keyword to construct.

        Returns:
            object: Metadata value read from the header(s).
        """
        retval = super().compound_meta(headarr, meta_key)
        if retval is not None:
            return retval

        if meta_key == 'mjd':
            return Time(headarr[0]['UTSHUT']).mjd
        elif meta_key == 'dispangle':
            return 0
        elif meta_key == 'binning':
            binspat = headarr[self._FITS_EXT]['BINSPAT']
            binspec = headarr[self._FITS_EXT]['BINSPEC']
            return parse.binning2string(binspec, binspat)
        elif meta_key == 'target':
            if 'TARGET' in headarr[0]:
                return headarr[0]['TARGET']
            else:
                return headarr[0]['IMGTYPE']
        elif meta_key == 'dichroic':
            return None
        else:
            raise PypeItError(f"Not ready for this compound meta: {meta_key}")

    def get_detector_par(self, det: int, hdu: fits.HDUList | None = None):
        """
        Return metadata for the selected detector.

        Args:
            det (:obj:`int`):
                1-indexed detector number.
            hdu (`astropy.io.fits.HDUList`_, optional):
                The open fits file with the raw image of interest.  If not
                provided, frame-dependent parameters are set to a default.

        Returns:
            :class:`~pypeit.images.detector_container.DetectorContainer`:
            Object with the detector metadata.
        """
        if hdu is None:
            binning = '1,1'
            datasec = None
            oscansec = None
        else:
            binning = self.get_meta_value(self.get_headarr(hdu), 'binning')
            datasec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['DATASEC']))
            oscansec = np.atleast_1d(
                parse.flip_fits_slice(hdu[self._FITS_EXT].header['BIASSEC']))

        detector_dict = dict(
            binning         = binning,
            det             = 1,
            dataext         = self._FITS_EXT,
            specaxis        = 1,
            specflip        = False,
            spatflip        = False,
            platescale      = 0.5,     # arcsec/pix
            darkcurr        = 0.0,     # e-/pixel/hour
            saturation      = 65000.,
            nonlinear       = 40./45.,
            mincounts       = -1e10,
            numamplifiers   = 1,
            gain            = np.atleast_1d(2.8),
            ronoise         = np.atleast_1d(8.5),
            datasec         = datasec,
            oscansec        = oscansec,
        )
        return detector_container.DetectorContainer(**detector_dict)

    @classmethod
    def default_pypeit_par(cls):
        """
        Return the default parameters to use for this instrument.

        Returns:
            :class:`~pypeit.par.pypeitpar.PypeItPar`: Parameters required by
            all of PypeIt methods.
        """
        par = super().default_pypeit_par()

        par['calibrations']['slitedges']['sync_predict'] = 'nearest'
        par['calibrations']['slitedges']['edge_thresh'] = 50.
        par['calibrations']['slitedges']['minimum_slit_length'] = 100
        par['calibrations']['slitedges']['min_edge_side_sep'] = 1.0

        par['scienceframe']['process']['combine'] = 'median'
        par['calibrations']['standardframe']['process']['combine'] = 'median'

        par['scienceframe']['process']['use_overscan'] = True
        par['scienceframe']['process']['sigclip'] = 4.0
        par['scienceframe']['process']['objlim'] = 5.0

        par['calibrations']['bpm_usebias'] = True

        par['calibrations']['pixelflatframe']['process']['combine'] = 'median'

        par['calibrations']['wavelengths']['lamps'] = ['ThAr']
        par['calibrations']['wavelengths']['method'] = 'full_template'
        par['calibrations']['wavelengths']['reid_arxiv'] = 'wvarxiv_p200_ngps_20250131T1227.fits'  # R Channel Template
        par['calibrations']['wavelengths']['rms_thresh_frac_fwhm'] = 1.0

        par['sensfunc']['algorithm'] = 'UVIS'

        par['calibrations']['biasframe']['exprng'] = [None, 0.001]
        par['calibrations']['arcframe']['exprng'] = [None, 120]
        par['calibrations']['standardframe']['exprng'] = [None, 120]
        par['scienceframe']['exprng'] = [90, None]

        return par



# ---------------------------------------------------------------------------
# U channel  –  FITS extension 4  (EXTNAME='U')
# Raw image shape: (1433, 1099)
#
# Overscan geometry (row-strip, not column-strip):
#   SKIPROWS=2
#   OS_ROWS=33 
#   BIASSEC=[1:-2,3:1433]
#   DATASEC=[-1:1097,3:1433]
# ---------------------------------------------------------------------------

class P200NGPSSpectrograph_u(P200NGPSSpectrograph):
    """
    Child to handle P200/NGPS u-Channel (near-UV) specific code.
    """
    name = 'p200_ngps_u'
    camera = 'NGPS_u'
    header_name = 'NGPS_u'
    supported = True
    comment = 'u-Channel; FITS ext 4'

    # FITS extension index for this channel (verified from raw headers).
    _FITS_EXT = 4

    def get_rawimage(self, raw_file, det):
        """
        Read raw spectrograph image files and return data and relevant
        metadata needed for image processing.

        Raw u-channel data are stored in FITS extension :attr:`_FITS_EXT`.
        The ``DATASEC``/``BIASSEC`` strings are already in binned-pixel
        coordinates (``sec_includes_binning=True``).
        """
        return super().get_rawimage(raw_file, det=self._FITS_EXT,
                                    sec_includes_binning=True)

    def compound_meta(self, headarr: list[fits.Header], meta_key: str):
        """
        Methods to generate metadata requiring interpretation of the header
        data, instead of simply reading the value of a header card.

        Args:
            headarr (:obj:`list`):
                List of `astropy.io.fits.Header`_ objects.
            meta_key (:obj:`str`):
                Metadata keyword to construct.

        Returns:
            object: Metadata value read from the header(s).
        """
        retval = super().compound_meta(headarr, meta_key)
        if retval is not None:
            return retval

        if meta_key == 'mjd':
            return Time(headarr[0]['UTSHUT']).mjd
        elif meta_key == 'dispangle':
            return 0
        elif meta_key == 'binning':
            # BINSPEC / BINSPAT retain their standard meaning (spectral /
            # spatial binning factor) regardless of the physical CCD rotation.
            binspat = headarr[self._FITS_EXT]['BINSPAT']
            binspec = headarr[self._FITS_EXT]['BINSPEC']
            return parse.binning2string(binspec, binspat)
        elif meta_key == 'target':
            if 'TARGET' in headarr[0]:
                return headarr[0]['TARGET']
            else:
                return headarr[0]['IMGTYPE']
        elif meta_key == 'dichroic':
            return None
        else:
            raise PypeItError(f"Not ready for this compound meta: {meta_key}")

    def get_detector_par(self, det: int, hdu: fits.HDUList | None = None):
        """
        Return metadata for the selected detector.

        Args:
            det (:obj:`int`):
                1-indexed detector number.
            hdu (`astropy.io.fits.HDUList`_, optional):
                The open fits file with the raw image of interest.  If not
                provided, frame-dependent parameters are set to a default.

        Returns:
            :class:`~pypeit.images.detector_container.DetectorContainer`:
            Object with the detector metadata.
        """
        if hdu is None:
            binning = '1,1'
            datasec = None
            oscansec = None
        else:
            binning = self.get_meta_value(self.get_headarr(hdu), 'binning')
            hdr = hdu[self._FITS_EXT].header
            naxis1 = hdr['NAXIS1'] 
            naxis2 = hdr['NAXIS2']  
            skiprows = hdr['SKIPROWS']
            os_rows = hdr['OS_ROWS']
 
            osc_row_start = skiprows + 1
            osc_row_end   = skiprows + os_rows
            oscansec = np.atleast_1d(f'[{osc_row_start}:{osc_row_end},1:{naxis1}]')
 
            data_row_start = skiprows + os_rows + 1
            datasec = np.atleast_1d(f'[{data_row_start}:{naxis2},1:{naxis1}]')
 
        detector_dict = dict(
            binning         = binning,
            det             = 1,
            dataext         = self._FITS_EXT,
            specaxis        = 0,
            specflip        = False,
            spatflip        = False,
            platescale      = 0.5,     # arcsec/pix
            darkcurr        = 0.0,     # e-/pixel/hour
            saturation      = 65000.,
            nonlinear       = 40./45.,
            mincounts       = -1e10,
            numamplifiers   = 1,
            gain            = np.atleast_1d(2.8),
            ronoise         = np.atleast_1d(8.5),  
            datasec         = datasec,
            oscansec        = oscansec,
        )
        return detector_container.DetectorContainer(**detector_dict)

    @classmethod
    def default_pypeit_par(cls):
        """
        Return the default parameters to use for this instrument.

        Returns:
            :class:`~pypeit.par.pypeitpar.PypeItPar`: Parameters required by
            all of PypeIt methods.
        """
        par = super().default_pypeit_par()

        par['calibrations']['slitedges']['sync_predict'] = 'nearest'
        par['calibrations']['slitedges']['edge_thresh'] = 50.
        par['calibrations']['slitedges']['minimum_slit_length'] = 100 
        par['calibrations']['slitedges']['det_min_spec_length'] = 0.1
        par['calibrations']['slitedges']['fit_min_spec_length'] = 0.1
        par['calibrations']['slitedges']['min_edge_side_sep'] = 1.0

        par['scienceframe']['process']['combine'] = 'median'
        par['calibrations']['standardframe']['process']['combine'] = 'median'

        par['scienceframe']['process']['use_overscan'] = True
        par['scienceframe']['process']['sigclip'] = 4.0
        par['scienceframe']['process']['objlim'] = 5.0

        par['calibrations']['bpm_usebias'] = False

        par['calibrations']['pixelflatframe']['process']['combine'] = 'median'

        par['calibrations']['wavelengths']['lamps'] = ['ThAr']
        par['calibrations']['wavelengths']['method'] = 'full_template'
        par['calibrations']['wavelengths']['reid_arxiv'] = 'wvarxiv_p200_ngps_u_20260423T2352.fits' # New Wavelength Solution
        par['calibrations']['wavelengths']['rms_thresh_frac_fwhm'] = 1.0

        par['sensfunc']['algorithm'] = 'UVIS'

        par['calibrations']['biasframe']['exprng'] = [None, 0.001]
        par['calibrations']['arcframe']['exprng'] = [None, 120]
        par['calibrations']['standardframe']['exprng'] = [None, 120]
        par['scienceframe']['exprng'] = [90, None]

        return par