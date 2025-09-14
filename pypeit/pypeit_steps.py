import os
from pathlib import Path
import numpy as np
import copy

from astropy.table import Table

from pypeit import msgs
from pypeit.calibframe import CalibFrame
from pypeit.images import buildimage
from pypeit import specobjs
from pypeit import find_objects
from pypeit import extraction
from pypeit.core import parse
from pypeit.manual_extract import ManualExtractionObj
from pypeit import spec2dobj
from pypeit.core import wave

from pypeit import slittrace
from pypeit import calibrations

from linetools import utils as ltu

from IPython import embed

def get_sci_metadata(spectrograph, fitstbl, frame, det):
    """
    Grab the meta data for a given science frame and specific detector

    Args:
        frame (int): Frame index
        det (int): Detector index

    Returns:
        5 objects are returned::
            - str: Object type;  science or standard
            - str: Setup/configuration string
            - `astropy.time.Time`_: Time of observation
            - str: Basename of the frame
            - str: Binning of the detector

    """

    # Set binning, obstime, basename, and objtype
    binning = fitstbl['binning'][frame]
    obstime  = fitstbl.construct_obstime(frame)
    basename = fitstbl.construct_basename(frame, obstime=obstime)
    types  = fitstbl['frametype'][frame].split(',')
    if 'science' in types:
        objtype_out = 'science'
    elif 'standard' in types:
        objtype_out = 'standard'
    else:
        msgs.error('get_sci_metadata() should only be run on standard or science frames.  '
                    f'Types of this frame are: {types}')
    calib_key = CalibFrame.construct_calib_key(fitstbl['setup'][frame],
                                                fitstbl['calib'][frame],
                                                spectrograph.get_det_name(det))
    return objtype_out, calib_key, obstime, basename, binning

def calib_one(spectrograph, fitstbl, par, det, calib_ID, calibrations_path:str, 
              reuse_calibs:bool=True,
              qa_path:str=None, show:bool=False, run_state:dict=None,
              stop_at_step:str=None):
    """
    Run Calibration for a single detector, calib_ID pair

    Args:
        det (:obj:`int`):
            Detector number (1-indexed)
        stop_at_step (:obj:`str`, optional):
            Run only up to this calibration step.

    Returns:
        caliBrate (:class:`pypeit.calibrations.Calibrations`)

    """
    if qa_path is None:
        qa_path = os.path.join(par['rdx']['redux_path'], par['rdx']['qadir'])

    # Handle frames
    in_grp = fitstbl.find_calib_group(calib_ID)
    frame_indx = np.arange(len(fitstbl))
    grp_frames = frame_indx[in_grp]

    # Instantiate Calibrations class
    user_slits = slittrace.merge_user_slit(par['rdx']['slitspatnum'],
                                            par['rdx']['maskIDs'])
    msgs.info(f'Building/loading calibrations for detector {det}')
    caliBrate = calibrations.Calibrations.get_instance(
        fitstbl, par['calibrations'], spectrograph, calibrations_path, 
        calib_ID, grp_frames[0], det,
        qadir=qa_path,
        reuse_calibs=reuse_calibs, show=show, user_slits=user_slits,
        chk_version=par['rdx']['chk_version'],
        state=run_state)

    # Check
    if stop_at_step is not None and stop_at_step not in caliBrate.steps:
        msgs.error(f"Requested stop_at_step={stop_at_step} is not a valid calibration step.\n Allowed steps are: {caliBrate.steps}")
        
    # Run
    caliBrate.run_the_steps(stop_at_step=stop_at_step)

    return caliBrate


def process_one_det(spectrograph, fitstbl, caliBrate, par, frames:list, 
                det, bg_frames:list=None): 
    """
    Process one set of files

    Returns
    -------
    sciImg : :class:`~pypeit.images.pypeitimage.PypeItImage`
        Science image
    bkg_redux_sciimg : :class:`~pypeit.images.pypeitimage.PypeItImage`
        Science image before background subtraction
        if self.bkg_redux is True, otherwise None.
        It's used to generate a global sky model without bkg subtraction.
    """
    # Grab some meta-data needed for the reduction from the fitstbl
    objtype, setup, obstime, basename, binning \
            = get_sci_metadata(spectrograph, fitstbl, frames[0], det)

    msgs.info("Image processing begins for {} on det={}".format(basename, det))

    # Is this a standard star?
    std_redux = objtype == 'standard'
    frame_par = par['calibrations']['standardframe'] \
                    if std_redux else par['scienceframe']

    # Build Science image
    sci_files = fitstbl.frame_paths(frames)
    sciImg = buildimage.buildimage_fromlist(
        spectrograph, det, frame_par,
        sci_files, bias=caliBrate.msbias, bpm=caliBrate.msbpm,
        dark=caliBrate.msdark,
        scattlight=caliBrate.msscattlight,
        flatimages=caliBrate.flatimages,
        slits=caliBrate.slits,  # For flexure correction
        ignore_saturation=False)

    # get no bkg subtracted sciImg to generate a global sky model without bkg subtraction.
    # it's a dictionary with only `image` and `ivar` keys if bkg_redux=False, otherwise it's None
    bkg_redux_sciimg = None

    # Background Image?
    if bg_frames is not None and len(bg_frames) > 0:
        # get no bkg subtracted sciImg
        bkg_redux_sciimg = sciImg
        # Build the background image
        bg_file_list = fitstbl.frame_paths(bg_frames)
        # TODO I think we should create a separate self.par['bkgframe'] parameter set to hold the image
        # processing parameters for the background frames.  This would allow the user to specify different
        # parameters for the background frames than for the science frames.  
        bgimg = buildimage.buildimage_fromlist(spectrograph, det, frame_par, bg_file_list,
                                                bpm=caliBrate.msbpm,
                                                bias=caliBrate.msbias,
                                                dark=caliBrate.msdark,
                                                scattlight=caliBrate.msscattlight,
                                                flatimages=caliBrate.flatimages,
                                                slits=caliBrate.slits,
                                                ignore_saturation=False)

        # NOTE: If the spatial flexure exists for sciImg, the subtraction
        # function propagates that to the subtracted image, ignoring any
        # spatial flexure determined for the background image.
        sciImg = bkg_redux_sciimg.sub(bgimg)

    '''
    # Save intermediate files
    if science_path is not None:
        # sciImg
        outfile_sci = science_path / f'sciImg_{basename}.fits'
        sciImg.to_file(outfile_sci, overwrite=True)
        if bkg_redux_sciimg is not None:
            # bkg_redux_sciimg
            outfile_bkg = science_path / f'bkg_{basename}.fits'
            bkg_redux_sciimg.to_file(outfile_bkg, overwrite=True)
    '''

    # Return
    return sciImg, bkg_redux_sciimg

def findobj_on_det(sciImg, spectrograph, fitstbl, par, frames:list, calib_ID:str,
                        det, calibrations_path:str, std_outfile:str=None, 
                        show:bool=False,
                        extras=None):

    # Grab some meta-data needed for the reduction from the fitstbl
    objtype, setup, obstime, basename, binning \
            = get_sci_metadata(spectrograph, fitstbl, frames[0], det)

    # Is this a standard star?
    std_redux = objtype == 'standard'
    if std_redux is False and std_outfile is not None:
        std_trace = specobjs.get_std_trace(spectrograph.get_det_name(det), 
                                        std_outfile)
    else:
        std_trace = None
    msgs.info("Object finding begins for {} on det={}".format(basename, det))

    # Load the image?
    caliBrate = load_calibrations_for_frame(
        spectrograph, fitstbl, par, frames[0], det, calib_ID, calibrations_path)

    msgs.info(f'Reducing detector {det}')

    # Instantiate Reduce object
    # Required for pypeline specific object
    # At instantiaton, the fullmask in self.sciImg is modified
    objFind = instantiate_objfind(sciImg, spectrograph, fitstbl,
                                  par, frames, det, caliBrate,
                                  extras['bkg_redux'],
                                  extras['find_negative'], show=show)
    # Do it
    #embed(header='187 of pypeit_steps.py')
    initial_sky, sobjs_obj = objFind.run(std_trace=std_trace, 
                                         show_peaks=show)

    return initial_sky, sobjs_obj, objFind


def load_calibrations_for_frame(spectrograph, fitstbl, par, frame, det,
        calib_ID, calibrations_path:str):

    # Instantiate Calibrations class
    user_slits = slittrace.merge_user_slit(par['rdx']['slitspatnum'],
                                            par['rdx']['maskIDs'])
    caliBrate = calibrations.Calibrations.get_instance(
        fitstbl, par['calibrations'], spectrograph,
        calibrations_path, 
        calib_ID, frame, det,
        reuse_calibs=True, user_slits=user_slits,
        chk_version=par['rdx']['chk_version'])
    #caliBrate.set_config(frame, det, par['calibrations'])
    caliBrate.run_the_steps(reload_only=True)

    return caliBrate


def load_skyregions(initial_slits=False, scifile=None, frame=None):
    """
    Generate or load sky regions, if defined by the user.

    Sky regions are defined by the internal provided parameters; see
    ``user_regions`` in :class:`~pypeit.par.pypeitpar.SkySubPar`.  If
    included in the pypeit file like so,

    .. code-block:: ini

        [reduce]
            [[skysub]]
                user_regions = :25,75:

    The first and last 25% of all slits are used as sky.  If the user has
    used the ``pypeit_skysub_regions`` GUI to generate a sky mask for a
    given frame, this can be searched for and loaded by setting the
    parameter to ``user``:

    .. code-block:: ini

        [reduce]
            [[skysub]]
                user_regions = user

    Parameters
    ----------
    initial_slits : :obj:`bool`, optional
        Flag to use the initial slits before any tweaking based on the
        slit-illumination profile; see
        :func:`~pypeit.slittrace.SlitTraceSet.select_edges`.
    scifile : :obj:`str`, optional
        The file name used to define the user-based sky regions.  Only used
        if ``user_regions = user``.
    frame : :obj:`int`, optional
        The index of the frame used to construct the calibration key.  Only
        used if ``user_regions = user``.
    spat_flexure : :obj:`float`, None, optional
        The spatial flexure (measured in pixels) of the science frame relative to the trace frame.

    Returns
    -------
    skymask : `numpy.ndarray`_
        A boolean array used to select sky pixels; i.e., True is a pixel
        that corresponds to a sky region.  If the ``user_regions`` parameter
        is not set (or an empty string), the returned value is None.
    """
    if par['reduce']['skysub']['user_regions'] in [None, '']:
        return None

    # Flexure
    spat_flexure = None
    # use the flexure correction in the "shift" column
    manual_flexure = self.fitstbl[frames[0]]['shift']
    if (self.objtype == 'science' and self.par['scienceframe']['process']['spat_flexure_correct']) or \
            (self.objtype == 'standard' and self.par['calibrations']['standardframe']['process']['spat_flexure_correct']) or \
                manual_flexure:
        if (manual_flexure or manual_flexure == 0) and not (np.issubdtype(self.fitstbl[frames[0]]["shift"], np.integer)):
            msgs.info(f'Implementing manual flexure of {manual_flexure}')
            spat_flexure = np.float64(manual_flexure)
            sciImg.spat_flexure = spat_flexure
        else:
            msgs.info(f'Using auto-computed flexure')
            spat_flexure = sciImg.spat_flexure
    msgs.info(f'Flexure being used is: {spat_flexure}')
    # Build the initial sky mask
    initial_skymask = self.load_skyregions(initial_slits=self.spectrograph.pypeline != 'SlicerIFU',
                                            scifile=sciImg.files[0], frame=frames[0], spat_flexure=spat_flexure)

    # Deal with manual extraction
    row = self.fitstbl[frames[0]]
    manual_obj = ManualExtractionObj.by_fitstbl_input(
        row['filename'], row['manual'], self.spectrograph) if len(row['manual'].strip()) > 0 else None


    # First priority given to user_regions first
    if self.par['reduce']['skysub']['user_regions'] == 'user':
        # Build the file name
        calib_key = CalibFrame.construct_calib_key(
                            self.fitstbl['setup'][frame],
                            CalibFrame.ingest_calib_id(self.fitstbl['calib'][frame]),
                            self.spectrograph.get_det_name(self.det))
        regfile = buildimage.SkyRegions.construct_file_name(calib_key,
                                                            calib_dir=self.calibrations_path,
                                                            basename=io.remove_suffix(scifile))
        regfile = Path(regfile).absolute()
        if not regfile.exists():
            msgs.error(f'Unable to find SkyRegions file: {regfile} . Create a SkyRegions '
                        'frame using pypeit_skysub_regions, or change the user_regions to '
                        'the percentage format.  See documentation.')
        msgs.info(f'Loading SkyRegions file: {regfile}')
        return buildimage.SkyRegions.from_file(regfile).image.astype(bool)

    skyregtxt = self.par['reduce']['skysub']['user_regions']
    if isinstance(skyregtxt, list):
        skyregtxt = ",".join(skyregtxt)
    msgs.info(f'Generating skysub mask based on the user defined regions: {skyregtxt}')
    # NOTE : Do not include spatial flexure here!
    #        It is included when generating the mask in the return statement below
    slits_left, slits_right, _ \
        = self.caliBrate.slits.select_edges(initial=initial_slits, flexure=None)

    maxslitlength = np.max(slits_right-slits_left)
    # Get the regions
    status, regions = skysub.read_userregions(skyregtxt, self.caliBrate.slits.nslits, maxslitlength)
    if status == 1:
        msgs.error("Unknown error in sky regions definition. Please check the value:" + msgs.newline() + skyregtxt)
    elif status == 2:
        msgs.error("Sky regions definition must contain a percentage range, and therefore must contain a ':'")
    # Generate and return image
    return skysub.generate_mask(self.spectrograph.pypeline, regions, self.caliBrate.slits,
                                slits_left, slits_right, spat_flexure=spat_flexure)


def adjust_for_slitmask(sciImg_dict, spectrograph, fitstbl, par, detectors,
                        frame0, binning, all_specobjs_objfind):
    # get object positions from slitmask design and slitmask offsets for all the detectors
    spat_flexure = np.array([ss.spat_flexure for ss in sciImg_dict])
    # Grab platescale with binning
    bin_spec, bin_spat = parse.parse_binning(binning)
    platescale = np.array([ss.detector.platescale*bin_spat for ss in sciImg_dict])
    # get the dither offset if available and if desired
    dither_off = None
    if par['reduce']['slitmask']['use_dither_offset']:
        if 'dithoff' in fitstbl.keys():
            dither_off = fitstbl['dithoff'][frame0]

    calib_slits = slittrace.get_maskdef_objpos_offset_alldets(
        all_specobjs_objfind, calib_slits, spat_flexure, platescale,
        par['calibrations']['slitedges']['det_buffer'],
        par['reduce']['slitmask'], dither_off=dither_off)
    # determine if slitmask offsets exist and compute an average offsets over all the detectors
    calib_slits = slittrace.average_maskdef_offset(
        calib_slits, platescale[0], spectrograph.list_detectors(mosaic='MSC' in calib_slits[0].detname))
    # slitmask design matching and add undetected objects
    all_specobjs_objfind = slittrace.assign_addobjs_alldets(
        all_specobjs_objfind, calib_slits, spat_flexure, platescale,
        par['reduce']['slitmask'], par['reduce']['findobj']['find_fwhm'])

def extract_det(spectrograph, fitstbl, par, 
                frames, det, caliBrate, sciImg, bkg_redux_sciimg, 
                initial_sky, sobjs_obj, 
                bkg_redux:bool=False,
                find_negative:bool=False,
                show:bool=False):
    """
    Extract Objects in a single exposure/detector pair

    sci_ID and det need to have been set internally prior to calling this method

    Args:
        frames (:obj:`list`):
            List of frames to extract; stacked if more than one
            is provided
        det (:obj:`int`):
            Detector number (1-indexed)
        sciImg (:class:`~pypeit.images.pypeitimage.PypeItImage`):
            Data container that holds a single image from a
            single detector and its related images (e.g. ivar, mask)
        bkg_redux_sciimg (:class:`~pypeit.images.pypeitimage.PypeItImage`, optional):
            Data container that holds a single image from a
            single detector and its related images (e.g. ivar, mask)
            before background subtraction if self.bkg_redux is True,
            otherwise None. It's used to generate a global sky
            model without bkg subtraction.
        objFind : :class:`~pypeit.find_objects.FindObjects`
            Object finding object
        initial_sky (`numpy.ndarray`_):
            Initial global sky model
        sobjs_obj (:class:`pypeit.specobjs.SpecObjs`):
            List of objects found during `run_objfind`

    Returns:
        tuple: Returns six `numpy.ndarray`_ objects and a
        :class:`pypeit.specobjs.SpecObjs` object with the
        extracted spectra from this exposure/detector pair. The
        six `numpy.ndarray`_ objects are (1) the science image,
        (2) its inverse variance, (3) the sky model, (4) the
        object model, (5) the model inverse variance, and (6) the
        mask.
    """
    # Grab some meta-data needed for the reduction from the fitstbl
    #self.objtype, self.setup, self.obstime, self.basename, self.binning \
    #        = self.get_sci_metadata(frames[0], det)
    objtype, setup, obstime, basename, binning \
            = get_sci_metadata(spectrograph, fitstbl, frames[0], det)
    # Is this a standard star?
    std_redux = 'standard' in objtype

    # Instantiate a new objFind object
    objFind = instantiate_objfind(sciImg, spectrograph, fitstbl,
                                  par, frames, det, caliBrate,
                                  bkg_redux, 
                                  find_negative)

    ## TODO JFH I think all of this about determining the final global sky should be moved out of this method
    ## and preferably into the FindObjects class. I see why we are doing it like this since for multislit we need
    # to find all of the objects first using slitmask meta data,  but this comes at the expense of a much more complicated
    # control structure.
    # TODO -- Can we do this now?  Probably not..

    # Update the global sky
    skymask = None
    if 'standard' in objtype or \
            par['reduce']['findobj']['skip_skysub'] or \
            par['reduce']['findobj']['skip_final_global'] or \
            par['reduce']['skysub']['user_regions'] is not None:
        final_global_sky = initial_sky
    else:
        # Update the skymask
        skymask = objFind.create_skymask(sobjs_obj)
        final_global_sky = objFind.global_skysub(previous_sky=initial_sky,
                                                    skymask=skymask, show=show,
                                                    reinit_bpm=False)
    # get the bkg_redux_global_sky
    bkg_redux_global_sky = None
    if bkg_redux:
        skymask = objFind.create_skymask(sobjs_obj) if skymask is None else skymask
        # DO NOT reinit_bpm, nor update_crmask
        bkg_redux_global_sky = objFind.global_skysub(skymask=skymask, bkg_redux_sciimg=bkg_redux_sciimg,
                                                    reinit_bpm=False, update_crmask=False, show=show)

    # TODO -- worry about this
    scaleImg = objFind.scaleimg

    # Each spec2d file includes the slits object with unique flagging
    #  for extraction failures.  So we make a copy here before those flags
    #  are modified.
    maskdef_designtab = caliBrate.slits.maskdef_designtab
    slits = copy.deepcopy(caliBrate.slits)
    slits.maskdef_designtab = None

    # update here slits.mask since global_skysub modify reduce_bpm and we need to propagate it into extraction
    flagged_slits = np.where(objFind.reduce_bpm)[0]
    if len(flagged_slits) > 0:
        slits.mask[flagged_slits] = \
            slits.bitmask.turn_on(slits.mask[flagged_slits], 'BADSKYSUB')

    if not par['reduce']['extraction']['skip_extraction']:
        msgs.info(f"Extraction begins for {basename} on det={det}")
        # Instantiate Reduce object
        # Required for pipeline specific object
        # At instantiation, the fullmask in self.sciImg is modified
        # TODO Are we repeating steps in the init for FindObjects and Extract??
        exTract = extraction.Extract.get_instance(
            sciImg, slits, sobjs_obj, spectrograph,
            par, objtype, global_sky=final_global_sky, 
            bkg_redux_global_sky=bkg_redux_global_sky,
            waveTilts=caliBrate.wavetilts, wv_calib=caliBrate.wv_calib, 
            flatimages=caliBrate.flatimages,
            bkg_redux=bkg_redux, 
            return_negative=par['reduce']['extraction']['return_negative'],
            std_redux=std_redux, basename=basename, show=show)
        #embed(header='465 of pypeit_steps.py')
        # Perform the extraction
        skymodel, bkg_redux_skymodel, objmodel, ivarmodel, outmask, sobjs, waveImg,\
            tilts, slits = exTract.run()
        slitgpm = np.logical_not(exTract.extract_bpm)
        slitshift = exTract.slitshift
    else:
        msgs.info(f"Extraction skipped for {basename} on det={det}")
        # TODO
        # If IFU, need to redo global sky sub for waveimg (this is a HACK)
        # TODO
        # Deal with slitshift too, for IFU

        # Since the extraction was not performed, fill the arrays with the best available information
        skymodel, bkg_redux_skymodel, objmodel, ivarmodel, outmask, sobjs, waveImg, tilts = \
            final_global_sky, \
            bkg_redux_global_sky, \
            np.zeros_like(objFind.sciImg.image), \
            np.copy(objFind.sciImg.ivar), \
            objFind.sciImg.fullmask, \
            sobjs_obj, \
            objFind.waveimg, \
            objFind.tilts
        slitgpm = (slits.mask == 0)
        slitshift = objFind.slitshift
        # If waveImg has not yet been created, make it now
        if waveImg is None:
            waveImg = caliBrate.wv_calib.build_waveimg(tilts, slits, spat_flexure=objFind.spat_flexure_shift)

    # Apply a reference frame correction to each object and the waveimg
    vel_corr, waveImg = refframe_correct(spectrograph, par, slits, 
                                              fitstbl["ra"][frames[0]], 
                                              fitstbl["dec"][frames[0]],
                                              obstime, slitgpm=slitgpm, 
                                              waveimg=waveImg, sobjs=sobjs)

    # TODO -- Do this upstream
    # Tack on wavelength RMS
    for sobj in sobjs:
        iwv = np.where(caliBrate.wv_calib.spat_ids == sobj.SLITID)[0][0]
        sobj.WAVE_RMS =caliBrate.wv_calib.wv_fits[iwv].rms

    # Construct table of spectral flexure
    spec_flex_table = Table()
    spec_flex_table['spat_id'] = slits.spat_id
    spec_flex_table['sci_spec_flexure'] = slitshift

    # Construct the Spec2DObj
    spec2DObj = spec2dobj.Spec2DObj(sciimg=sciImg.image,
                                    ivarraw=sciImg.ivar,
                                    skymodel=skymodel,
                                    bkg_redux_skymodel=bkg_redux_skymodel,
                                    objmodel=objmodel,
                                    ivarmodel=ivarmodel,
                                    scaleimg=scaleImg,
                                    waveimg=waveImg,
                                    bpmmask=outmask,
                                    detector=sciImg.detector,
                                    sci_spat_flexure=sciImg.spat_flexure,
                                    sci_spec_flexure=spec_flex_table,
                                    vel_corr=vel_corr,
                                    vel_type=par['calibrations']['wavelengths']['refframe'],
                                    tilts=tilts,
                                    slits=slits,
                                    wavesol=caliBrate.wv_calib.wave_diagnostics(print_diag=False),
                                    maskdef_designtab=maskdef_designtab)
    spec2DObj.process_steps = sciImg.process_steps

    spec2DObj.calibs = calibrations.Calibrations.get_association(
                                fitstbl, spectrograph, 
                                caliBrate.calib_dir, #calibrations_path,
                                fitstbl[frames[0]]['setup'],
                                fitstbl.find_frame_calib_groups(frames[0])[0], det,
                                must_exist=True, proc_only=True)

    # QA
    spec2DObj.gen_qa()

    # Return
    return spec2DObj, sobjs

def instantiate_objfind(sciImg, spectrograph, fitstbl, par, frames, det,
                        caliBrate, bkg_redux, find_negative, 
                        show:bool=False):
    objtype, setup, obstime, basename, binning \
            = get_sci_metadata(spectrograph, fitstbl, frames[0], det)
    std_redux = objtype == 'standard'

    # Deal with manual extraction
    row = fitstbl[frames[0]]
    manual_obj = ManualExtractionObj.by_fitstbl_input(
        row['filename'], row['manual'], spectrograph) if len(row['manual'].strip()) > 0 else None

    # TODO - Move this into FindObjects class
    if par['reduce']['skysub']['user_regions'] in [None, '']:
        initial_skymask = None
    else:
        # Build the initial sky mask
        initial_skymask = load_skyregions(
            initial_slits=spectrograph.pypeline != 'SlicerIFU',
            scifile=sciImg.files[0], frame=frames[0])

    objFind = find_objects.FindObjects.get_instance(
        sciImg, caliBrate.slits,
        spectrograph, par, objtype,
        wv_calib=caliBrate.wv_calib,
        waveTilts=caliBrate.wavetilts,
        initial_skymask=initial_skymask,
        bkg_redux=bkg_redux,
        manual=manual_obj,
        find_negative=find_negative,
        std_redux=std_redux,
        basename=basename,
        show=show)

    return objFind


# TODO :: Should this be moved outside of this class?
def refframe_correct(spectrograph, par, slits, ra, dec, obstime, slitgpm=None, 
                     waveimg=None, sobjs=None):
    """ Correct the calibrated wavelength to the user-supplied reference frame

    Args:
        slits (:class:`~pypeit.slittrace.SlitTraceSet`):
            Slit trace set object
        ra (float, str):
            Right Ascension
        dec (float, str):
            Declination
        obstime (`astropy.time.Time`_):
            Observation time
        slitgpm (`numpy.ndarray`_, None, optional):
            1D boolean array indicating the good slits (True). If None, the gpm will be taken from slits
        waveimg (`numpy.ndarray`_, optional)
            Two-dimensional image specifying the wavelength of each pixel
        sobjs (:class:`~pypeit.specobjs.SpecObjs`, None, optional):
            Spectrally extracted objects

    """
    if slitgpm is None:
        slitgpm = (slits.mask == 0)
    # Correct Telescope's motion
    refframe = par['calibrations']['wavelengths']['refframe']
    vel_corr = 0.0
    if refframe in ['heliocentric', 'barycentric'] \
            and par['calibrations']['wavelengths']['reference'] != 'pixel':
        msgs.info("Performing a {0} correction".format(par['calibrations']['wavelengths']['refframe']))
        # Calculate correction
        radec = ltu.radec_to_coord((ra, dec))
        vel, vel_corr = wave.geomotion_correct(radec, obstime,
                                                spectrograph.telescope['longitude'],
                                                spectrograph.telescope['latitude'],
                                                spectrograph.telescope['elevation'],
                                                refframe)
        # Apply correction to objects
        msgs.info('Applying {0} correction = {1:0.5f} km/s'.format(refframe, vel))
        if (sobjs is not None) and (sobjs.nobj != 0):
            # Loop on slits to apply
            gd_slitord = slits.slitord_id[slitgpm]
            for slitord in gd_slitord:
                indx = sobjs.slitorder_indices(slitord)
                this_specobjs = sobjs[indx]
                # Loop on objects
                for specobj in this_specobjs:
                    if specobj is None:
                        continue
                    specobj.apply_helio(vel_corr, refframe)

        # Apply correction to wavelength image
        if waveimg is not None:
            waveimg *= vel_corr
    else:
        msgs.info('A wavelength reference frame correction will not be performed.')

    # Return the value of the correction and the corrected wavelength image
    return vel_corr, waveimg


