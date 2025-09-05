"""
Main driver class for PypeIt run

.. include common links, assuming primary doc root is up one directory
.. include:: ../include/links.rst

"""
from pathlib import Path
import time
import os
from datetime import datetime

# TODO: datetime.UTC is not defined in python 3.10.  Remove this when we decide
# to no longer support it.
try:
    __UTC__ = datetime.UTC
except AttributeError as e:
    from datetime import timezone
    __UTC__ = timezone.utc

from IPython import embed

import numpy as np

from astropy.io import fits

from pypeit import inputfiles
from pypeit.core import parse, wave, qa
from pypeit import spec2dobj
from pypeit import specobjs
from pypeit import msgs
from pypeit import calibrations
from pypeit.display import display
from pypeit import slittrace
from pypeit import utils
from pypeit.history import History
from pypeit.metadata import PypeItMetaData
from pypeit import state

from pypeit import pypeit_steps

from linetools import utils as ltu


class PypeIt:
    """
    This class runs the primary calibration and extraction in PypeIt

    .. todo::
        Fill in list of attributes!

    Args:
        pypeit_file (:obj:`str`):
            PypeIt filename.
        verbosity (:obj:`int`, optional):
            Verbosity level of system output.  Can be:

                - 0: No output
                - 1: Minimal output (default)
                - 2: All output

        overwrite (:obj:`bool`, optional):
            Flag to overwrite any existing files/directories.
        reuse_calibs (:obj:`bool`, optional):
            Reuse any pre-existing calibration files
        logname (:obj:`str`, optional):
            The name of an ascii log file with the details of the
            reduction.
        show: (:obj:`bool`, optional):
            Show reduction steps via plots (which will block further
            execution until clicked on) and outputs to ginga. Requires
            remote control ginga session via ``ginga --modules=RC,SlitWavelength &``
        redux_path (:obj:`str`, optional):
            Over-ride reduction path in PypeIt file (e.g. Notebook usage)
        calib_only: (:obj:`bool`, optional):
            Only generate the calibration files that you can

    Attributes:
        pypeit_file (:obj:`str`):
            Name of the pypeit file to read.  PypeIt files have a
            specific set of valid formats. A description can be found
            :ref:`pypeit_file`.
        fitstbl (:obj:`pypeit.metadata.PypeItMetaData`): holds the meta info

    """
    def __init__(self, pypeit_file, verbosity=2, overwrite=True, reuse_calibs=False, logname=None,
                 show=False, redux_path=None, calib_only=False):

        # Set up logging
        self.logname = logname
        self.verbosity = verbosity
        self.pypeit_file = pypeit_file

        # State
        self.run_state = state.RunPypeItState(pypeit_file=pypeit_file, 
                                              current_step='init',
                                              current_det=-1,
                                              current_calibID=-1)
        self.run_state = self.run_state.load()
        
        self.msgs_reset()
        
        # Load up PypeIt file
        self.pypeItFile = inputfiles.PypeItFile.from_file(pypeit_file)
        self.calib_only = calib_only

        # Build the spectrograph and the parameters
        self.spectrograph, self.par, config_specific_file = self.pypeItFile.get_pypeitpar()
        msgs.info(f'Loaded spectrograph {self.spectrograph.name}')
        msgs.info('Setting configuration-specific parameters using '
                  f'{os.path.split(config_specific_file)[1]}.')

        # Check the output paths are ready
        if redux_path is not None:
            self.par['rdx']['redux_path'] = redux_path

        # Write the full parameter set here
        # --------------------------------------------------------------
        par_file = pypeit_file.replace(
            '.pypeit', f"_UTC_{datetime.now(__UTC__).date()}.par")
        self.par.to_config(par_file, include_descr=False)

        # --------------------------------------------------------------
        # Build the meta data
        #   - Re-initilize based on the file data
        msgs.info('Compiling metadata')
        self.fitstbl = PypeItMetaData(self.spectrograph, self.par, 
                                      files=self.pypeItFile.filenames,
                                      usrdata=self.pypeItFile.data, 
                                      strict=True)
        #   - Interpret automated or user-provided data from the PypeIt
        #   file
        self.fitstbl.finalize_usr_build(
            self.pypeItFile.frametypes, 
            self.pypeItFile.setup_name)

        # Other Internals
        self.overwrite = overwrite

        # Currently the runtime argument determines the behavior for
        # reusing calibrations
        self.reuse_calibs = reuse_calibs
        self.show = show

        # Set paths
        self.calibrations_path = Path(self.par['rdx']['redux_path']) / self.par['calibrations']['calib_dir']

        # Check for calibrations
        if not self.calib_only:
            calibrations.check_for_calibs(self.par, self.fitstbl,
                                          raise_error=self.par['calibrations']['raise_chk_error'])

        # --------------------------------------------------------------
        #   - Write .calib file (For QA naming amongst other things)
        calib_file = pypeit_file.replace('.pypeit', '.calib')
        calibrations.Calibrations.association_summary(calib_file, self.fitstbl, self.spectrograph,
                                                      self.calibrations_path, overwrite=True)

        # Report paths
        msgs.info('Setting reduction path to {0}'.format(self.par['rdx']['redux_path']))
        msgs.info('Calibration frames saved to: {0}'.format(self.calibrations_path))
        msgs.info('Science data output to: {0}'.format(self.science_path))
        msgs.info('Quality assessment plots output to: {0}'.format(self.qa_path))

        # Init
        self.det = None
        self.tstart = None
        #self.basename = None
        self.obstime = None

    @property
    def science_path(self) -> Path:
        """Return the path to the science directory."""
        return Path(self.par['rdx']['redux_path']) / self.par['rdx']['scidir']

    @property
    def qa_path(self) -> str:
        """Return the path to the top-level QA directory."""
        return os.path.join(self.par['rdx']['redux_path'], self.par['rdx']['qadir'])

    def build_qa(self):
        """
        Generate QA wrappers
        """
        msgs.qa_path = self.qa_path
        qa.gen_qa_dir(self.qa_path)
        qa.gen_mf_html(self.pypeit_file, self.qa_path)
        qa.gen_exp_html()

    # TODO: This should go in a more relevant place
    def spec_output_file(self, frame:int, twod:bool=False) -> Path:
        """
        Return the path to the spectral output data file.
        
        Args:
            frame (:obj:`int`):
                Frame index from :attr:`fitstbl`.
            twod (:obj:`bool`), optional:
                Name for the 2D output file; 1D file otherwise.
        
        Returns:
            `Path`_: The path for the output file
        """
        return self.get_spec_file_name(self.science_path, self.fitstbl.construct_basename(frame),
                                       twod=twod)

    @staticmethod
    def get_spec_file_name(science_path:Path, basename:str, twod:bool=False) -> Path:
        """
        Get the spectrum filename

        Args:
            science_path (`Path`_):
                Path to the science files
            basename (:obj:`str`):
                Base name for this frame
            twod (:obj:`bool`), optional:
                Is this a 2D science frame?

        Returns:
            `Path`_: The spectrum filename
        """
        return science_path / f'spec{"2" if twod else "1"}d_{basename}.fits'

    def outfile_exists(self, frame:int) -> bool:
        """
        Check whether the 2D outfile of a given frame already exists

        Args:
            frame (:obj:`int`): Frame index from fitstbl

        Returns:
            :obj:`bool`: True if the 2d file exists, False if it does not exist
        """
        return self.spec_output_file(frame, twod=True).is_file()

    def get_std_outfile(self, standard_frames):
        """
        Return the spec1d file name for a reduced standard to use as a tracing
        crutch.

        The file is either constructed using the provided standard frame indices
        or it is directly pulled from the
        :class:`~pypeit.par.pypeitpar.FindObjPar` parameters in :attr:`par`.
        The latter takes precedence.  If more than one row is provided by
        ``standard_frames``, the first index is used.

        Args:
            standard_frames (array-like):
                Set of rows in :attr:`fitstbl` with standards.

        Returns:
            :obj:`str`: Full path to the standard spec1d output file to use.
        """
        # NOTE: I'm not sure if this is the best place to put this, but it does
        # isolate where the name of the standard-star spec1d file is defined.
        std_outfile = self.par['reduce']['findobj']['std_spec1d']
        if std_outfile is not None:
            if not self.par['reduce']['findobj']['use_std_trace']:
                msgs.error('If you provide a standard star spectrum for tracing, you must set use_std_trace=True')
            elif not Path(std_outfile).absolute().exists():
                msgs.error(f'Provided standard spec1d file does not exist: {std_outfile}')
            return std_outfile

        # TODO: Need to decide how to associate standards with
        # science frames in the case where there is more than one
        # standard associated with a given science frame.  Below, I
        # just use the first standard

        std_frame = None if (len(standard_frames) == 0 or not self.par['reduce']['findobj']['use_std_trace']) \
            else standard_frames[0]
        # Prepare to load up standard?
        if std_frame is not None:
            std_outfile = self.spec_output_file(std_frame) \
                            if isinstance(std_frame, (int,np.integer)) else None
        if std_outfile is not None and not std_outfile.is_file():
            msgs.error(f'Could not find standard file: {std_outfile}')
        return std_outfile

    def calib_all(self):
        """
        Process all calibration frames.

        Provides an avenue to reduce a dataset without (or omitting) any
        science/standard frames.
        """
        self.tstart = time.perf_counter()

        # Frame indices
        frame_indx = np.arange(len(self.fitstbl))
        for calib_ID in self.fitstbl.calib_groups:
            # Find all the frames in this calibration group
            in_grp = self.fitstbl.find_calib_group(calib_ID)
            if not any(in_grp):
                continue
            grp_frames = frame_indx[in_grp]

            # Find the detectors to reduce
            detectors = self.select_detectors(self.spectrograph, self.par['rdx']['detnum'],
                                              slitspatnum=self.par['rdx']['slitspatnum'])
            msgs.info(f'Detectors to work on: {detectors}')

            # Loop on Detectors
            for self.det in detectors:
                msgs.info(f'Working on detector {self.det}')

                self.caliBrate = self.calib_one(grp_frames, self.det, calib_ID)
                if not self.caliBrate.success:
                    msgs.warn(f'Calibrations for detector {self.det} were unsuccessful!  The step '
                              f'that failed was {self.caliBrate.failed_step}.  Continuing to next '
                              f'detector.')

        # Finish
        self.print_end_time()

    def reduce_all(self):
        """
        Main driver of the entire reduction

        Calibration and extraction via a series of calls to
        :func:`reduce_exposure`.

        """
        # Validate the parameter set
        self.par.validate_keys(required=['rdx', 'calibrations', 'scienceframe', 'reduce',
                                         'flexure'])
        self.tstart = time.perf_counter()

        # Find the standard frames
        is_standard = self.fitstbl.find_frames('standard')
        if np.any(is_standard):
            msgs.info(f'Found {np.sum(is_standard)} standard frames to reduce.')

        # Find the science frames
        is_science = self.fitstbl.find_frames('science')
        if np.any(is_science):
            msgs.info(f'Found {np.sum(is_science)} science frames to reduce.')

        # This will give an error to alert the user that no reduction will be
        # run if there are no science/standard frames and `run_pypeit` is run
        # without -c flag
        if not np.any(is_science) and not np.any(is_standard):
            msgs.error('No science/standard frames provided. Add them to your PypeIt file '
                       'if this is a standard run! Otherwise run calib_only reduction using -c flag')

        # Frame indices
        frame_indx = np.arange(len(self.fitstbl))

        # Standard Star(s) Loop
        # Iterate over each calibration group and reduce the standards
        for calib_ID in self.fitstbl.calib_groups:

            # Find all the frames in this calibration group
            in_grp = self.fitstbl.find_calib_group(calib_ID)

            if not np.any(is_standard & in_grp):
                continue

            # Find the indices of the standard frames in this calibration group:
            grp_standards = frame_indx[is_standard & in_grp]

            msgs.info(f'Found {len(grp_standards)} standard frames in calibration group '
                      f'{calib_ID}.')

            # Reduce all the standard frames, loop on unique comb_id
            u_combid_std = np.unique(self.fitstbl['comb_id'][grp_standards])
            for j, comb_id in enumerate(u_combid_std):
                frames = np.where(self.fitstbl['comb_id'] == comb_id)[0]
                # Find all frames whose comb_id matches the current frames
                # bkg_id (same as for science frames).
                bg_frames = np.where((self.fitstbl['comb_id'] == self.fitstbl['bkg_id'][frames][0])
                                     & (self.fitstbl['comb_id'] >= 0))[0]
                if not self.outfile_exists(frames[0]) or self.overwrite:
                    # Build history to document what contributed to the reduced
                    # exposure
                    history = History(self.fitstbl.frame_paths(frames[0]))
                    history.add_reduce(calib_ID, self.fitstbl, frames, bg_frames)
                    std_spec2d, std_sobjs = self.reduce_exposure(frames, calib_ID, bg_frames=bg_frames)
                    # TODO come up with sensible naming convention for save_exposure for combined files
                    self.save_exposure(frames[0], std_spec2d, std_sobjs, history)
                else:
                    msgs.info('Output file: {:s} already exists'.format(self.fitstbl.construct_basename(frames[0])) +
                              '. Set overwrite=True to recreate and overwrite.')

        # Science Frame(s) Loop
        # Iterate over each calibration group again and reduce the science frames
        for calib_ID in self.fitstbl.calib_groups:
            # Find all the frames in this calibration group
            in_grp = self.fitstbl.find_calib_group(calib_ID)

            if not np.any(is_science & in_grp):
                continue

            # Find the indices of the science frames in this calibration group:
            grp_science = frame_indx[is_science & in_grp]
            msgs.info(f'Found {len(grp_science)} science frames in calibration group {calib_ID}.')

            # Associate standards (previously reduced above) for this setup
            std_outfile = self.get_std_outfile(frame_indx[is_standard])
            # Loop on unique comb_id
            u_combid = np.unique(self.fitstbl['comb_id'][grp_science])
        
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
                frames = np.where(self.fitstbl['comb_id'] == comb_id)[0]
                # Find all frames whose comb_id matches the current frames bkg_id.
                bg_frames = np.where((self.fitstbl['comb_id'] == self.fitstbl['bkg_id'][frames][0])
                                     & (self.fitstbl['comb_id'] >= 0))[0]
                # JFH changed the syntax below to that above, which allows
                # frames to be used more than once as a background image. The
                # syntax below would require that we could somehow list multiple
                # numbers for the bkg_id which is impossible without a comma
                # separated list
#                bg_frames = np.where(self.fitstbl['bkg_id'] == comb_id)[0]
                if not self.outfile_exists(frames[0]) or self.overwrite:

                    # Build history to document what contributd to the reduced
                    # exposure
                    history = History(self.fitstbl.frame_paths(frames[0]))
                    history.add_reduce(calib_ID, self.fitstbl, frames, bg_frames)

                    # TODO -- Should we reset/regenerate self.slits.mask for a new exposure
                    sci_spec2d, sci_sobjs = self.reduce_exposure(
                        frames, calib_ID, bg_frames=bg_frames, 
                        std_outfile=std_outfile)

                    # TODO: come up with sensible naming convention for
                    # save_exposure for combined files
                    if len(sci_spec2d.detectors) > 0:
                        self.save_exposure(frames[0], sci_spec2d, sci_sobjs, history,
                                           skip_write_2d=self.par['scienceframe']['process']['skip_write_2d'])
                    else:
                        msgs.warn('No spec2d and spec1d saved to file because the '
                                  'calibration/reduction was not successful for all the detectors')
                else:
                    msgs.warn(f'Output file: {self.fitstbl.construct_basename(frames[0])} already '
                              'exists. Set overwrite=True to recreate and overwrite.')

            msgs.info(f'Finished calibration group {calib_ID}')

        # Finish
        self.print_end_time()

    @staticmethod
    def select_detectors(spectrograph, detnum, slitspatnum=None):
        """
        Get the set of detectors to be reduced.

        This is mostly a wrapper for
        :func:`~pypeit.spectrographs.spectrograph.Spectrograph.select_detectors`,
        except that it applies any limitations set by the
        :class:`~pypeit.par.pypeitpar.ReduxPar` parameters.

        Args:
            spectrograph (:class:`~pypeit.spectrographs.spectrograph.Spectrograph`):
                Spectrograph instance that defines the allowed
                detectors/mosaics.
            detnum (:obj:`int`, :obj:`tuple`):
                The detectors/mosaics to parse
            slitspatnum (:obj:`str`, optional):
                Used to restrict the reduction to a specified slit.  See
                :class:`~pypeit.par.pypeitpar.ReduxPar`.

        Returns:
            :obj:`list`: List of unique detectors or detector mosaics to be
            reduced.
        """
        return spectrograph.select_detectors(subset=detnum if slitspatnum is None else slitspatnum)

 

    def reduce_exposure(self, frames, calib_ID, bg_frames=None, std_outfile=None):
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
        if self.show:
            # TODO: Put this in a try/except block?
            display.clear_all(allow_new=True)

        has_bg = True if bg_frames is not None and len(bg_frames) > 0 else False
        # Is this an b/g subtraction reduction?
        if has_bg:
            self.bkg_redux = True
            # The default is to find_negative objects if the bg_frames are
            # classified as "science", and to not find_negative objects if the
            # bg_frames are classified as "sky". This can be explicitly
            # overridden if par['reduce']['findobj']['find_negative'] is set to
            # something other than the default of None.
            self.find_negative = (('science' in self.fitstbl['frametype'][bg_frames[0]]) |
                                  ('standard' in self.fitstbl['frametype'][bg_frames[0]])) \
                            if self.par['reduce']['findobj']['find_negative'] is None else \
                                self.par['reduce']['findobj']['find_negative']
        else:
            self.bkg_redux = False
            self.find_negative= False

        # Print status message
        msgs_string = 'Reducing target {:s}'.format(self.fitstbl['target'][frames[0]]) + msgs.newline()
        # TODO: Print these when the frames are actually combined,
        # backgrounds are used, etc?
        msgs_string += 'Combining frames:' + msgs.newline()
        for iframe in frames:
            msgs_string += '{0:s}'.format(self.fitstbl['filename'][iframe]) + msgs.newline()
        msgs.info(msgs_string)
        if has_bg:
            bg_msgs_string = ''
            for iframe in bg_frames:
                bg_msgs_string += '{0:s}'.format(self.fitstbl['filename'][iframe]) + msgs.newline()
            bg_msgs_string = msgs.newline() + 'Using background from frames:' + msgs.newline() + bg_msgs_string
            msgs.info(bg_msgs_string)

        # Find the detectors to reduce
        detectors = self.select_detectors(self.spectrograph, self.par['rdx']['detnum'],
                                          slitspatnum=self.par['rdx']['slitspatnum'])
        msgs.info(f'Detectors to work on: {detectors}')

        # #####################################
        # Calibrations
        for det in detectors:
            msgs.info(f'Calibrating detector {det}')
            # run/load calibration
            caliBrate = self.calib_one(frames, det, calib_ID)
            if not caliBrate.success:
                msgs.warn(f'Calibrations for detector {det} were unsuccessful!  The step '
                          f'that failed was {caliBrate.failed_step}.  Continuing by '
                          f'skipping this detector.')
                continue

        # #####################################
        # Proccess or load processed frames
        load_processed = True
        if load_processed:
            load, write = True, False
        else:
            load, write = False, True
        sciImg_dict, bkg_redux_sciimg_dict = pypeit_steps.process_frames(
                self.spectrograph, self.fitstbl, self.par, frames,
                   detectors, self.calibrations_path, 
                   bg_frames=bg_frames, 
                   load=load, write=write)

        # #####################################
        # Find objects + initial sky
        # TODO -- replace this kludge
        extras = dict(bkg_redux=self.bkg_redux,
                find_negative=self.find_negative,
                show=self.show)
        load_findobj = True
        if load_findobj:
            load, write = True, False
            all_specobjs_objfind = None
        else:
            load, write = False, True
        initial_sky_dict, all_specobjs_find = \
            pypeit_steps.findobj_on_exposure(sciImg_dict, self.spectrograph, 
                                self.fitstbl,
                                self.par, frames, detectors,
                                self.calibrations_path,
                                std_outfile=std_outfile,
                                extras=extras, 
                                load=load, write=write)
        #embed(header='576 of x_pypeit')

        # #####################################
        # slitmask stuff
        if self.par['reduce']['slitmask']['assign_obj']:
            frame0 = frames[0]
            calib_slits = pypeit_steps.adjust_for_slitmask(
                sciImg_dict, 
                self.spectrograph, 
                self.fitstbl, 
                self.par, 
                detectors,
                frame0, 
                self.fitstbl['binning'][frame0],
                all_specobjs_objfind)

        # #####################################
        # Extract
        all_spec2d, all_specobjs_extract = pypeit_steps.extract_exposure(
            sciImg_dict, bkg_redux_sciimg_dict,
            self.spectrograph, self.fitstbl, 
            self.par, frames, self.calibrations_path, 
            detectors,
            all_specobjs_find,
            initial_sky_dict)

        return all_spec2d, all_specobjs_extract

    def calib_one(self, frames, det, calib_ID, stop_at_step:str=None):
        """
        Run Calibration for a single exposure/detector pair

        Args:
            frames (:obj:`list`):
                List of frames (rows) to calibrate
                Only used to idetify the setup and calibration group
            det (:obj:`int`):
                Detector number (1-indexed)
            stop_at_step (:obj:`str`, optional):
                Run only up to this calibration step.
                

        Returns:
            caliBrate (:class:`pypeit.calibrations.Calibrations`)

        """

        msgs.info(f'Building/loading calibrations for detector {det}')
        # Instantiate Calibrations class
        user_slits = slittrace.merge_user_slit(self.par['rdx']['slitspatnum'],
                                               self.par['rdx']['maskIDs'])
        caliBrate = calibrations.Calibrations.get_instance(
            self.fitstbl, self.par['calibrations'], self.spectrograph,
            self.calibrations_path, qadir=self.qa_path,
            reuse_calibs=self.reuse_calibs, show=self.show, user_slits=user_slits,
            chk_version=self.par['rdx']['chk_version'],
            state=self.run_state)


        # Check
        if stop_at_step is not None and stop_at_step not in caliBrate.steps:
            msgs.error(f"Requested stop_at_step={stop_at_step} is not a valid calibration step.\n Allowed steps are: {caliBrate.steps}")
            
        # These need to be separate to accomodate COADD2D
        caliBrate.set_config(frames[0], det, self.par['calibrations'])
        caliBrate.calib_ID = calib_ID

        # Run
        caliBrate.run_the_steps(stop_at_step=stop_at_step)

        #embed(header='742 of pypeit')

        return caliBrate

    def save_exposure(self, frame:int, all_spec2d:spec2dobj.AllSpec2DObj,
                      all_specobjs:specobjs.SpecObjs, history:History=None,
                      skip_write_2d:bool=False):
        """
        Save the outputs from extraction for a given exposure

        Args:
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
        # TODO: Need some checks here that the exposure has been reduced?
        obstime  = self.fitstbl.construct_obstime(frame)
        basename = self.fitstbl.construct_basename(frame, obstime=obstime)

        # Determine the headers
        row_fitstbl = self.fitstbl[frame]
        # Need raw file header information
        rawfile = self.fitstbl.frame_paths(frame)
        head2d = fits.getheader(rawfile, ext=self.spectrograph.primary_hdrext)

        # Check for the directory
        if not self.science_path.is_dir():
            self.science_path.mkdir()

        # NOTE: There are some gymnastics here to keep from altering
        # self.par['rdx']['detnum'].  I.e., I can't just set update_det =
        # self.par['rdx']['detnum'] because that can alter the latter if I don't
        # deepcopy it...
        if self.par['rdx']['detnum'] is None:
            update_det = None
        elif isinstance(self.par['rdx']['detnum'], list):
            update_det = [self.spectrograph.allowed_mosaics.index(d)+1 
                            if isinstance(d, tuple) else d for d in self.par['rdx']['detnum']]
        else:
            update_det = self.par['rdx']['detnum']

        subheader = self.spectrograph.subheader_for_spec(row_fitstbl, head2d)
        # 1D spectra
        if all_specobjs.nobj > 0 and not self.par['reduce']['extraction']['skip_extraction']:
            # Spectra
            outfile1d = self.science_path / f'spec1d_{basename}.fits'
            # TODO
            #embed(header='deal with the following for maskIDs;  713 of pypeit')
            all_specobjs.write_to_fits(subheader, outfile1d,
                                       update_det=update_det,
                                       slitspatnum=self.par['rdx']['slitspatnum'],
                                       history=history)
            # Info
            outfiletxt = self.science_path / f'spec1d_{basename}.txt'
            # TODO: Note we re-read in the specobjs from disk to deal with situations where
            # only a single detector is run in a second pass but in the same reduction directory.
            # This was to address Issue #1116 in PR #1154. Slightly inefficient, but only other
            # option is to re-work write_info to also "append"
            sobjs = specobjs.SpecObjs.from_fitsfile(outfile1d, chk_version=False)
            sobjs.write_info(outfiletxt, self.spectrograph.pypeline)
            #all_specobjs.write_info(outfiletxt, self.spectrograph.pypeline)

        if skip_write_2d:
            return

        # 2D spectra
        outfile2d = self.science_path / f'spec2d_{basename}.fits'
        # Build header
        pri_hdr = all_spec2d.build_primary_hdr(head2d, self.spectrograph,
                                               redux_path=self.par['rdx']['redux_path'],
                                               calib_dir=self.calibrations_path,
                                               subheader=subheader,
                                               history=history)

        # Write
        all_spec2d.write_to_fits(outfile2d, pri_hdr=pri_hdr,
                                 update_det=update_det,
                                 slitspatnum=self.par['rdx']['slitspatnum'])

    def msgs_reset(self):
        """
        Reset the msgs object
        """

        # Reset the global logger
        msgs.reset(log=self.logname, verbosity=self.verbosity)
        msgs.pypeit_file = self.pypeit_file

    def print_end_time(self):
        """
        Print the elapsed time
        """
        # Capture the end time and print it to user
        msgs.info(utils.get_time_string(time.perf_counter()-self.tstart))

    ## TODO: Move this to fitstbl?
    #def show_science(self):
    #    """
    #    Simple print of science frames
    #    """
    #    indx = self.fitstbl.find_frames('science')
    #    print(self.fitstbl[['target','ra','dec','exptime','dispname']][indx])

    def __repr__(self):
        # Generate sets string
        return '<{:s}: pypeit_file={}>'.format(self.__class__.__name__, self.pypeit_file)