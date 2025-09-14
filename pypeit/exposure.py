import numpy as np

from astropy.io import fits

from pypeit import msgs

from pypeit import outputfiles
from pypeit.images import pypeitimage
from pypeit.display import display
from pypeit.history import History
from pypeit import specobjs
from pypeit import spec2dobj
from pypeit import calibrations

from pypeit import pypeit_steps

def process_exposure(spectrograph, fitstbl, par, frames:list, calib_ID:str,
                   detectors:list, calibrations_path:str,
                   bg_frames:list=None, 
                   load:bool=False, write:bool=False):

    # dict of sciImg
    sciImg_dict = {}
    # list of bkg_redux_sciimg
    bkg_redux_sciimg_dict = {}

    # Loop on the detectors
    for det in detectors:
        # Filenames
        _, _, _, basename, binning \
            = pypeit_steps.get_sci_metadata(spectrograph, fitstbl, frames[0], det)
        sci_filename = outputfiles.intermediate_filename('sciImg', basename, 
                                        spectrograph.get_det_name(det))
        bkg_filename = outputfiles.intermediate_filename('bkgImg', basename, 
                                                spectrograph.get_det_name(det))
        # Load?
        if load:
            msgs.info(f'Loading images for detector {det}')
            sciImg = pypeitimage.PypeItImage.from_file(sci_filename)
            if bg_frames is not None and len(bg_frames) > 0:
                bkg_redux_sciimg = pypeitimage.PypeItImage.from_file(bkg_filename)
            else:
                bkg_redux_sciimg = None
            sciImg_dict[det] = sciImg
            bkg_redux_sciimg_dict[det] = bkg_redux_sciimg
            continue

        msgs.info(f'Reducing detector {det}')
        # run/load calibration
        caliBrate = pypeit_steps.load_calibrations_for_frame(
            spectrograph, fitstbl, par, frames[0], det, calib_ID, calibrations_path)
        if not caliBrate.success:
            msgs.error(f'Calibrations for detector {det} were unsuccessful!  The step '
                        f'that failed was {caliBrate.failed_step}.')  
            continue

        # Process
        sciImg, bkg_redux_sciimg = pypeit_steps.process_one_det(
            spectrograph, fitstbl, caliBrate,
            par, frames, det, bg_frames=bg_frames)

        # List em up
        sciImg_dict[det] = sciImg
        bkg_redux_sciimg_dict[det] = bkg_redux_sciimg

        # Write them?
        if write:
            # Generate the folder?
            if not sci_filename.parent.is_dir():
                sci_filename.parent.mkdir()
            # Write sciImg
            sciImg.to_file(sci_filename, overwrite=True)
            msgs.info(f'Wrote intermediate science image to {sci_filename}')
            # bkg_redux_sciimg?
            if bkg_redux_sciimg is not None:
                bkg_redux_sciimg.to_file(bkg_filename, overwrite=True)
                msgs.info(f'Wrote intermediate background image to {bkg_filename}')


    # Return
    return sciImg_dict, bkg_redux_sciimg_dict

def findobj_on_exposure(sciImg_dict:dict, spectrograph, 
                        fitstbl, par, frames:list, 
                        detectors:list, calib_ID:str, calibrations_path:str, 
                        std_outfile:str=None,
                        load:bool=False, write:bool=False,
                        extras=None):
    
    # Output
    initial_sky_dict = {}

    # container for specobjs during first loop (objfind)
    all_specobjs_objfind = specobjs.SpecObjs()

    # Loop on the detectors
    for det in detectors:
        _, _, _, basename, binning \
            = pypeit_steps.get_sci_metadata(spectrograph, fitstbl, frames[0], det)
        initsky_filename = outputfiles.intermediate_filename('initSky', basename, 
                                        spectrograph.get_det_name(det))

        # Load?
        if load:
            msgs.info(f'Loading initial sky for detector {det}')
            tmp = pypeitimage.PypeItImage.from_file(initsky_filename)
            initial_sky_dict[det] = tmp.image
            continue

        # Grab the science image
        sciImg = sciImg_dict[det]

        # Run
        initial_sky, sobjs_obj, _ = \
            pypeit_steps.findobj_on_det(sciImg, spectrograph, fitstbl, par, frames, 
                           calib_ID, det, 
                           calibrations_path, 
                           std_outfile=std_outfile, extras=extras)

        # Store em
        initial_sky_dict[det] = initial_sky
        if len(sobjs_obj)>0:
            all_specobjs_objfind.add_sobj(sobjs_obj)

        # Write?
        if write:
            init_pypeit = pypeitimage.PypeItImage(initial_sky)
            if not initsky_filename.parent.is_dir():
                initsky_filename.parent.mkdir()
            init_pypeit.to_file(initsky_filename, overwrite=True)

    # Spec1D
    spec1d_filename = outputfiles.intermediate_filename('spec1d', basename, 'all')
    if load:
        all_specobjs_objfind = specobjs.SpecObjs.from_fitsfile(spec1d_filename)
    elif write: 
        all_specobjs_objfind.write_to_fits({}, spec1d_filename)

    # Return
    return initial_sky_dict, all_specobjs_objfind

def extract_exposure(sciImg_dict, bkg_redux_sciimg_dict,
                     spectrograph, fitstbl, par, frames,
                     detectors, calib_ID:str, calibrations_path, 
                     all_specobjs_objfind,
                     initial_sky_dict, 
                     bkg_redux:bool=False,
                     find_negative:bool=False,
                     calib_slits:list=None):

    # Container for all the Spec2DObj
    all_spec2d = spec2dobj.AllSpec2DObj()
    all_spec2d['meta']['bkg_redux'] = bkg_redux
    all_spec2d['meta']['find_negative'] = find_negative
    # container for specobjs during second loop (extraction)
    all_specobjs_extract = specobjs.SpecObjs()

    # Extract
    for i,det in enumerate(detectors):
        # Load calibrations
        caliBrate = load_calibrations_for_frame(
            spectrograph, fitstbl, par, frames[0], det, calib_ID, calibrations_path)
        if calib_slits is not None:
            caliBrate.slits = calib_slits[i]

        detname = sciImg_dict[det].detector.name

        # TODO: pass back the background frame, pass in background
        # files as an argument. extract one takes a file list as an
        # argument and instantiates science within
        if all_specobjs_objfind.nobj > 0:
            all_specobjs_on_det = all_specobjs_objfind[all_specobjs_objfind.DET == detname]
        else:
            all_specobjs_on_det = all_specobjs_objfind

        # Extract
        all_spec2d[detname], tmp_sobjs = pypeit_steps.extract_det(
            spectrograph, fitstbl, par, frames, det,
            caliBrate, sciImg_dict[det],
            bkg_redux_sciimg_dict[det],
            initial_sky_dict[det],
            all_specobjs_on_det,
            bkg_redux=bkg_redux,
            find_negative=find_negative)

        # Hold em
        if tmp_sobjs.nobj > 0:
            all_specobjs_extract.add_sobj(tmp_sobjs)

        # Add calibration associations to the SpecObjs object
        all_specobjs_extract.calibs = calibrations.Calibrations.get_association(
                                fitstbl, spectrograph, calibrations_path,
                                fitstbl[frames[0]]['setup'],
                                fitstbl.find_frame_calib_groups(frames[0])[0], det,
                                must_exist=True, proc_only=True)

    # Return
    return all_spec2d, all_specobjs_extract
def reduce_calibID(spectrograph, par, fitstbl, calib_ID:str, 
                   calibrations_path:str,
                   reduce_standard:bool=False, overwrite:bool=False,
                   show:bool=False,
                   run_state=None,
                   reuse_calibs:bool=True):

    if reduce_standard:
        is_this = fitstbl.find_frames('standard')
        rtype = 'standard'
    else:
        is_this = fitstbl.find_frames('science')
        rtype = 'science'

    # Frame indices
    frame_indx = np.arange(len(fitstbl))

    # Find all the frames in this calibration group
    in_grp = fitstbl.find_calib_group(calib_ID)

    if not np.any(is_this & in_grp):
        return

    # Find the indices of the science frames in this calibration group:
    grp_this = frame_indx[is_this & in_grp]
    msgs.info(f'Found {len(grp_this)} {rtype} frames in calibration group {calib_ID}.')

    # Associate standards (previously reduced above) for this setup
    if not reduce_standard:
        is_standard = fitstbl.find_frames('standard')
        std_outfile = outputfiles.get_std_outfile(fitstbl, par, frame_indx[is_standard])
    else:
        std_outfile = None

    # Loop on unique comb_id
    u_combid = np.unique(fitstbl['comb_id'][grp_this])

    for j, comb_id in enumerate(u_combid):
        # TODO: This was causing problems when multiple science frames
        # were provided to quicklook and the user chose *not* to stack
        # the frames.  But this means it now won't skip processing the
        # B-A pair when the background image(s) are defined.  Punting
        # for now...
#                # Quicklook mode?
#                if self.par['rdx']['quicklook'] and j > 0:
#                    msgs.warn('PypeIt executed in quicklook mode.  Only reducing science frames '
#                              'in the first combination group!')
#                    break
        #
        frames = np.where(fitstbl['comb_id'] == comb_id)[0]
        # Find all frames whose comb_id matches the current frames bkg_id.
        bg_frames = np.where((fitstbl['comb_id'] == fitstbl['bkg_id'][frames][0])
                                & (fitstbl['comb_id'] >= 0))[0]
        # JFH changed the syntax below to that above, which allows
        # frames to be used more than once as a background image. The
        # syntax below would require that we could somehow list multiple
        # numbers for the bkg_id which is impossible without a comma
        # separated list
#                bg_frames = np.where(self.fitstbl['bkg_id'] == comb_id)[0]

        outfile2d = outputfiles.spec_output_file(fitstbl, par,
                                            frames[0], twod=True)
        if not outfile2d.is_file() or overwrite:

            # Build history to document what contributd to the reduced
            # exposure
            history = History(fitstbl.frame_paths(frames[0]))
            history.add_reduce(calib_ID, fitstbl, frames, bg_frames)

            # TODO -- Should we reset/regenerate self.slits.mask for a new exposure
            #sci_spec2d, sci_sobjs = self.reduce_exposure(
            #    frames, calib_ID, bg_frames=bg_frames, 
            #    std_outfile=std_outfile)

            this_spec2d, this_sobjs = reduce_exposure(
                spectrograph, fitstbl, par, frames, calib_ID, 
                calibrations_path, bg_frames=bg_frames,
                reuse_calibs=reuse_calibs, run_state=run_state,
                show=show,
                std_outfile=std_outfile)

            # TODO: come up with sensible naming convention for
            # save_exposure for combined files
            if len(this_spec2d.detectors) > 0:
                #self.save_exposure(frames[0], sci_spec2d, sci_sobjs, history,
                #                   skip_write_2d=self.par['scienceframe']['process']['skip_write_2d'])
                save_exposure(spectrograph,
                                    fitstbl, par, frames[0], 
                                    this_spec2d, this_sobjs, calibrations_path,
                                    history=history,
                                    skip_write_2d=par['scienceframe']['process']['skip_write_2d'])
            else:
                msgs.warn('No spec2d and spec1d saved to file because the '
                            'calibration/reduction was not successful for all the detectors')
        else:
            msgs.warn(f'Output file: {fitstbl.construct_basename(frames[0])} already '
                        'exists. Set overwrite=True to recreate and overwrite.')

def reduce_exposure(spectrograph, fitstbl, par, frames, calib_ID, 
                    calibrations_path:str, bg_frames=None, 
                    reuse_calibs:bool=True,
                    run_state:dict=None, std_outfile=None,
                    show:bool=False):
    """
    Reduce a single exposure

    Args:
        frames (:obj:`list`):
            List of 0-indexed rows in :attr:`fitstbl` with the frames to
            reduce.
        bg_frames (:obj:`list`, optional):
            List of frame indices for the background.
        std_outfile (:obj:`str`, optional):
            File with a previously reduced standard spectrum from
            PypeIt.

    Returns:
        dict: The dictionary containing the primary outputs of
        extraction.

    """

    # if show is set, clear the ginga channels at the start of each new sci_ID
    if show:
        # TODO: Put this in a try/except block?
        display.clear_all(allow_new=True)

    has_bg = True if bg_frames is not None and len(bg_frames) > 0 else False
    # Is this an b/g subtraction reduction?
    if has_bg:
        bkg_redux = True
        # The default is to find_negative objects if the bg_frames are
        # classified as "science", and to not find_negative objects if the
        # bg_frames are classified as "sky". This can be explicitly
        # overridden if par['reduce']['findobj']['find_negative'] is set to
        # something other than the default of None.
        find_negative = (('science' in fitstbl['frametype'][bg_frames[0]]) |
                                ('standard' in fitstbl['frametype'][bg_frames[0]])) \
                        if par['reduce']['findobj']['find_negative'] is None else \
                            par['reduce']['findobj']['find_negative']
    else:
        bkg_redux = False
        find_negative= False

    # Print status message
    msgs_string = 'Reducing target {:s}'.format(fitstbl['target'][frames[0]]) + msgs.newline()
    # TODO: Print these when the frames are actually combined,
    # backgrounds are used, etc?
    msgs_string += 'Combining frames:' + msgs.newline()
    for iframe in frames:
        msgs_string += '{0:s}'.format(fitstbl['filename'][iframe]) + msgs.newline()
    msgs.info(msgs_string)
    if has_bg:
        bg_msgs_string = ''
        for iframe in bg_frames:
            bg_msgs_string += '{0:s}'.format(fitstbl['filename'][iframe]) + msgs.newline()
        bg_msgs_string = msgs.newline() + 'Using background from frames:' + msgs.newline() + bg_msgs_string
        msgs.info(bg_msgs_string)

    # Find the detectors to reduce
    detectors = spectrograph.select_detectors(subset=par['rdx']['detnum'] if par['rdx']['slitspatnum'] is None 
                                              else par['rdx']['slitspatnum'])
    #detectors = select_detectors(self.spectrograph, self.par['rdx']['detnum'],
    #                                    slitspatnum=self.par['rdx']['slitspatnum'])
    msgs.info(f'Detectors to work on: {detectors}')

    # #####################################
    # Calibrations
    for det in detectors:
        msgs.info(f'Calibrating detector {det}')
        # run/load calibration
        #caliBrate = calib_one(frames, det, calib_ID)
        caliBrate =  pypeit_steps.calib_one(spectrograph, fitstbl, par, det, calib_ID, calibrations_path,
              show=show, run_state=run_state, reuse_calibs=reuse_calibs)
        if not caliBrate.success:
            msgs.warn(f'Calibrations for detector {det} were unsuccessful!  The step '
                        f'that failed was {caliBrate.failed_step}.  Continuing by '
                        f'skipping this detector.')
            continue

    # #####################################
    # Proccess or load processed frames
    load_processed = False
    if load_processed:
        load, write = True, False
    else:
        load, write = False, True
    sciImg_dict, bkg_redux_sciimg_dict = process_exposure(
            spectrograph, fitstbl, par, frames, calib_ID,
                detectors, calibrations_path, 
                bg_frames=bg_frames, 
                load=load, write=write)

    # #####################################
    # Find objects + initial sky
    # TODO -- replace this kludge
    extras = dict(bkg_redux=bkg_redux, find_negative=find_negative, show=show)
    load_findobj = False
    if load_findobj:
        load, write = True, False
        all_specobjs_objfind = None
    else:
        load, write = False, True
    initial_sky_dict, all_specobjs_find = \
        findobj_on_exposure(sciImg_dict, spectrograph, 
                            fitstbl,
                            par, frames, detectors,
                            calib_ID, calibrations_path,
                            std_outfile=std_outfile,
                            extras=extras, 
                            load=load, write=write)
    #embed(header='576 of x_pypeit')

    # #####################################
    # slitmask stuff
    if par['reduce']['slitmask']['assign_obj']:
        frame0 = frames[0]
        calib_slits = adjust_for_slitmask(
            sciImg_dict, 
            spectrograph, 
            fitstbl, 
            par, 
            detectors,
            frame0, 
            fitstbl['binning'][frame0],
            all_specobjs_objfind)

    # #####################################
    # Extract
    all_spec2d, all_specobjs_extract = extract_exposure(
        sciImg_dict, bkg_redux_sciimg_dict,
        spectrograph, fitstbl, 
        par, frames, 
        detectors, calib_ID,
        calibrations_path, 
        all_specobjs_find,
        initial_sky_dict, 
        bkg_redux=bkg_redux,
        find_negative=find_negative)

    # Return
    return all_spec2d, all_specobjs_extract

def save_exposure(spectrograph, fitstbl, par, 
                  frame:int, all_spec2d:spec2dobj.AllSpec2DObj,
                  all_specobjs:specobjs.SpecObjs, 
                  calibrations_path:str,
                  history:History=None,
                  skip_write_2d:bool=False):
    """
    Save the outputs from extraction for a given exposure

    Args:
        science_path (:class:`pathlib.Path`):
            Path to the science directory where the output files
            will be written. 
        frame (:obj:`int`):
            0-indexed row in the metadata table with the frame
            that has been reduced.
        all_spec2d(:class:`~pypeit.spec2dobj.AllSpec2DObj`):
            The 2D reduced spectrum objects.
        all_specobjs (:class:`~pypeit.specobjs.SpecObjs`):
            The 1D spectral extraction objects.
        history (:class:`~pypeit.history.History`), optional:
            History entries to be added to fits header
        skip_write_2d (:obj:`bool`), optional:
            Skip writing the 2D spectrum to disk
    """
    # Check for the Science/ directory
    science_path = outputfiles(par)
    if not science_path.is_dir():
        science_path.mkdir()

    # Determine the headers
    row_fitstbl = fitstbl[frame]
    # Need raw file header information
    rawfile = fitstbl.frame_paths(frame)
    head2d = fits.getheader(rawfile, ext=spectrograph.primary_hdrext)


    # NOTE: There are some gymnastics here to keep from altering
    # self.par['rdx']['detnum'].  I.e., I can't just set update_det =
    # self.par['rdx']['detnum'] because that can alter the latter if I don't
    # deepcopy it...
    if par['rdx']['detnum'] is None:
        update_det = None
    elif isinstance(par['rdx']['detnum'], list):
        update_det = [spectrograph.allowed_mosaics.index(d)+1 
                        if isinstance(d, tuple) else d for d in par['rdx']['detnum']]
    else:
        update_det = par['rdx']['detnum']

    subheader = spectrograph.subheader_for_spec(row_fitstbl, head2d)
    # 1D spectra
    if all_specobjs.nobj > 0 and not par['reduce']['extraction']['skip_extraction']:
        # Spectra
        #outfile1d = science_path / f'spec1d_{basename}.fits'
        outfile1d = outputfiles.spec_output_file(fitstbl, par, frame)
        # TODO
        #embed(header='deal with the following for maskIDs;  713 of pypeit')
        all_specobjs.write_to_fits(subheader, outfile1d,
                                    update_det=update_det,
                                    slitspatnum=par['rdx']['slitspatnum'],
                                    history=history)
        # Info
        outfiletxt = outputfiles.spec_output_file(fitstbl, par,
                                            frame, txt=True)
        # TODO: Note we re-read in the specobjs from disk to deal with situations where
        # only a single detector is run in a second pass but in the same reduction directory.
        # This was to address Issue #1116 in PR #1154. Slightly inefficient, but only other
        # option is to re-work write_info to also "append"
        sobjs = specobjs.SpecObjs.from_fitsfile(outfile1d, chk_version=False)
        sobjs.write_info(outfiletxt, spectrograph.pypeline)
        #all_specobjs.write_info(outfiletxt, self.spectrograph.pypeline)

    if skip_write_2d:
        return

    # 2D spectra
    outfile2d = outputfiles.spec_output_file(fitstbl, par, frame, twod=True)

    # Build header
    pri_hdr = all_spec2d.build_primary_hdr(head2d, spectrograph,
                                            redux_path=par['rdx']['redux_path'],
                                            calib_dir=calibrations_path,
                                            subheader=subheader,
                                            history=history)

    # Write
    all_spec2d.write_to_fits(outfile2d, pri_hdr=pri_hdr,
                                update_det=update_det,
                                slitspatnum=par['rdx']['slitspatnum'])