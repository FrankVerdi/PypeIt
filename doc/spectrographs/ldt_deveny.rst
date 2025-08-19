**********
LDT DeVeny
**********

Overview
========

This file summarizes several instrument specific
items for the LDT/DeVeny spectrograph.


EMI Pickup Noise
++++++++++++++++

See the `LDT Observer Tools package documentation
<https://lowellobservatory.github.io/LDTObserverTools/scrub_deveny_pickup.html>`_
for information about the EMI pickup noise seen in the DeVeny detector since
approximately 2019.



Using PypeIt with the LDT/DeVeny Spectrograph
=============================================

The LDT/DeVeny configuration parameters described herein are included
with PypeIt v1.15.0 and later, [3]_ and the released package may be
installed via your favorite method. Complete instructions are available
in the :ref:`installation instructions <installing>`, but brief outlines
are provided here.

Once you have installed the package, test to be sure the main driver
script runs. Go to a directory outside of the PypeIt directory (*e.g.*,
your home directory) and run the main executable:

::

        cd
        run_pypeit -h

This should fail if any of the required dependencies are not satisfied.
See the :ref:`installation instructions <installing>` for troubleshooting.

Setting Up and Running a PypeIt Reduction
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

This section details how to use PypeIt with DeVeny data. It is
paraphrased from the PypeIt documentation. See the :ref:`cookbook`
for complete and detailed instructions.

.. note::

    Before you get too far, it is important to understand that PypeIt
    reorients all 2D image data (from any spectrograph) so that the spectral
    axis is vertical with increasing wavelength corresponding to increasing
    pixel number. In the case of DeVeny data, this amounts to a 90º CW
    rotation of the images with respect to the original files. Don't Panic!

At the :ref:`bottom of this page <deveny_workflow>` there is a “cheat sheet”
of common DeVeny PypeIt
workflows


Planning Your Observations for Reduction with PypeIt
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Because PypeIt is an automated data reduction pipeline with minimal
opportunity to interact with the reduction in progress, pre-telescope
planning is required to obtain the proper calibration frames. While most
observing programs will already collect all of the frames necessary for
smooth operation of the pipeline, several items bear pointing out:

-  Bias frames are used to remove fixed-pattern noise in the data, and
   also used to generate the default bad pixel mask for reductions. [4]_

-  Dome flats are used for the dual purposes of removing pixel-to-pixel
   variations in sensitivity, and tracing the edges of the slit (which
   can vary from grating to grating, and will be more apparent following
   the future installation of the decker). Dome flats (or, optionally,
   sky flats) also may be used for correcting for the variable illumination
   function along the slit (generally < 1% variation), **but this feature
   must be explicitly turned on during reduction**.

-  Wavelength calibration is the piece most likely to cause headaches
   for any spectroscopy program. The user needs to decide which
   combination of lamps will provide suitable calibration for their program.
   PypeIt performs an unclipped mean combine of specified arc frames into a
   single calibration file. As of v1.13.0, the default DeVeny parameters allow
   for combination of frames taken with individual lamps (separate Hg- and
   Ar-only frames), as well as multilamp frames. If you plan to combine
   single-lamp arc frames, see :ref:`wavecalib` for needed parameter
   modifications.

   The selected slit width also plays into how well PypeIt matches the
   calibration spectrum with the corresponding line lists. While it is
   sometimes possible to attempt calibration on arc frames taken with a
   wide slit opening (:math:`\gtrsim 2\arcsec`), for best results use
   arc spectra taken with an optimal slit width (§\ `[set1] <#set1>`__)
   to ensure matching by the automated algorithms.

   Additionally, because of the spectral-direction flexure of the DeVeny
   camera (Appendix `2 <#sec:deal_flexure>`__), **do not attempt** to
   combine comparison arc frames from different telescope positions. The
   shift in line positions between positions will create a hot-mess
   calibration frame and the wavelength calibration will fail. PypeIt’s
   flexure-correction algorithm (see §\ `1.6.1 <#sec:pype_flex>`__) uses
   night-sky lines to adjust the wavelength calibration for individual
   science frames, so the use of *in situ* arcs may not be necessary. It
   is, however, possible to correlate individual science frames with
   individual arc images, and this is discussed under Advanced Usage
   (§\ `1.6.2 <#pype:groups>`__) – if you go this route, we suggest you
   also compare it with the single-pointing arcs and PypeIt’s flexure
   correction and let LDT staff know how well they do.

   As of v1.41.1, complete wavelength templates using the Hg, Cd, and Ar
   lamps are available for the 150g/mm (DV1), 300g/mm (DV2, DV3),
   500g/mm (DV5), 600g/mm (DV6, DV7), and 1200g/mm (DV9) gratings.
   PypeIt will automatically match calibration spectra from these
   gratings against the appropriate template using its method. For the
   other two gratings (DV4 and DV8), PypeIt attempts to identify the
   lines in the spectrum *ex nihilo* using its method.

-  All 9 in-service gratings have been tested with PypeIt and
   appropriate grating-specific parameters have been included in the
   v1.15.0 release. If you have issues with the pipeline crashing or
   incorrect reduction of your data, please contact LDT staff for
   troubleshooting.

-  *To ensure your calibrations will work with PypeIt*, test the
   pipeline on a preexisting data set whose calibration frames were
   taken in the same way you expect to take them. If this testing is
   done ahead of time, it will save much frustration later. It is also
   possible to run the pipeline on-the-fly on your observing night to
   ensure you have collected a workable calibration set.



Organize the Data to be Reduced
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Download a single night’s data from / to your reduction machine, as
described in §\ `[sec:data] <#sec:data>`__. The easiest method is using
secure copy (), but feel free to use whatever method you prefer. [5]_

Be sure your data directory includes bias, flat field, and arc lamp
comparison frames taken using the same grating, tilt, and rear filter
settings as your science data. Focus frames may be present or deleted –
PypeIt will ignore them. You should have:

-  Bias frames (to remove fixed-pattern noise from the data)

-  Dome Flat frames (to remove pixel-to-pixel sensitivity variations)

-  Comparison Arc frames (for wavelength calibration)

-  Science frames (the whole point)

Optionally, depending on the science requirements of your program, you
may also include:

-  Spectrophotometric Standard Star frames (for flux calibration)

-  Sky Flat frames (to correct for variations in illumination along the
   slit, seldom required, see §\ `2.2 <#sec:spatial_flexure>`__)

This raw data directory is the root of the directory tree PypeIt uses
for organizing the processing files and processed data (see
§\ `1.8 <#sec:pype_filestructure>`__ for an example). Make sure it is on
a local drive (rather than network storage) for speed and efficiency,
since PypeIt reads and writes files frequently during the reduction
process.

 

.. _pypeit_setup:

Setup
~~~~~

All PypeIt command-line scripts () have online help available using the
option.

 

Running PypeIt on a set of data is controlled by a PypeIt Reduction File
that details what the software should do to each file along the way to
producing reduced and calibrated data. The package provides a script
that reads through the FITS headers in the raw directory to generate the
reduction file (and directory tree) based on what it finds. PypeIt
determines unique instrument configurations, and sorts data in
preparation for the data reduction.

For DeVeny data, instrument configurations are defined by unique
combinations of the grating (FITS keyword ), grating tilt angle (), rear
order-blocking filter (), and CCD binning (). PypeIt maps the various
DeVeny FITS keywords onto a set of internal metadata keys for
processing. The relevant PypeIt metadata keys for DeVeny configurations
(which you will see in your reduction files) are:

::

       Metadata Key   FITS Header
       ------------   -----------
           dispname       GRATING
            cenwave       GRANGLE
            filter1      FILTREAR
            binning        CCDSUM

The PypeIt metadata key is the computed central wavelength of the
spectrum in Angstroms, derived from the grating and tilt angle (running
the calculation of §\ `[set2] <#set2>`__ backwards), and rounded to the
nearest 5Å.

 

The script will automatically associate your data files with specific
Frame Types (used internally for different calibration steps) and
collect groups of images by unique instrument configurations. The
step-by-step procedure for using is:

#. **First Execution**

   You will run the script twice. The first run will produce the setup
   files that should be inspected to ensure the code has properly
   divvied up the FITS files into the proper configuration(s). For most
   DeVeny programs (a single grating tilt and rear filter used with the
   installed grating), should find a single instrument configuration.

   Run the script the first time thuswise:

   where the required command-line option sets the spectrograph
   configuration parameters.

   This execution of searches for all files within the raw data
   directory. [6]_

    

#. **Inspect the Outputs**

   The call above creates the subdirectory populated with three files:

   : Observing log, generated from the FITS headers.

   : Shows unique configurations and associated image frames.

   : The auto-generated calibration association file.  

   **file**:

   This file should somewhat resemble your own time-ordered observing
   log for this set of data, with the relevant FITS keywords mapped to
   their PypeIt metadata keys. This is a good time to ensure that all
   the files you expect to see are in fact present.

   Any collimator focus frames (which you should have identified with
   FITS header keyword , see Fig. `[fig:loui] <#fig:loui>`__ #4) will
   have a listed as in this file and are commented out. If there are
   non-focus frames with listed, this indicates the FITS keyword was not
   correctly set. You may either modify the affected FITS headers using
   your preferred method [7]_, or simply note the affected frames and
   later edit the relevant PypeIt Reduction File(s)
   (§\ `1.3.4 <#subsec:edit>`__) with the correct frame type. If you
   modify any FITS headers directly, re-run step #1 above, and reexamine
   the output file.

    

   **file**:

   The file is divided into sections enumerating the unique instrument
   configurations and the list of frames associated therewith. Each
   unique configuration is given a capital letter identifier (A, B, C,
   D…).

   Below are example headers from a file for LDT/DeVeny data taken with
   two different order-blocking filters on the same night:

   ::

           ##########################################################
           Setup A
                dispname: DV1 (150/5000)
                 cenwave: 7220.0
                 filter1: Clear
                 binning: 1,1

   ::

           ##########################################################
           Setup B
                dispname: DV1 (150/5000)
                 cenwave: 7220.0
                 filter1: OG570
                 binning: 1,1

   This file contains two configurations, and , and the “setup blocks”
   (shown above) describe the instrument configurations based on the
   relevant metadata. Each “setup block” is followed by a table listing
   the files and relevant metadata for all files matched to that
   instrument configuration (not shown – very wide table).

   PypeIt does not use the file to guide reductions, but it is provided
   as a means for the user to assess the automated setup identification
   and file sorting. You may recognize that you are missing calibrations
   or you may be surprised to see more configurations than you were
   expecting. If, at the start of your observing session, you did not
   select the grating or rear filter in the LOUI before taking exposures
   (§\ `[sec:ccd] <#sec:ccd>`__.\ `[ccd6] <#ccd6>`__), those frames will
   have listed in the associated header field. In this case, you will
   likely have spurious instrument configurations – go back and edit the
   FITS headers with the proper values and rerun step #1 above.

   Importantly, you should use the file to decide which configuration(s)
   you wish to reduce. Any changes made to this file, however, are not
   recognized by PypeIt. All user-level edits to the frame-typing,
   association of frames with given configurations, etc., must be done
   via the PypeIt Reduction File (§\ `1.3.4 <#subsec:edit>`__).

   **file**:

   A more recent addition to the collection of setup files, the file
   enumerates all of the PypeIt frametypes found, the calibration files
   associated therewith, and the raw data frames combined to produce
   them. This version of the calibration association file is
   informational only, but it may be helpful for thinking about grouping
   frames into separate calibration groups, if necessary
   (see §\ `1.6.2 <#pype:groups>`__).

#. **Second execution**

   Provided you are happy with the file, you are ready to write the file
   for one or more setups. Executing the script a second time with the
   option will **c**\ reate one or more sub-folders and populate each
   with a PypeIt Reduction File. Some example uses of the option are:

   : This will create one folder/file for configuration

   : This will create a folder/file for each of two configurations ( and
   )

   : This will create folders/files for all identified configurations in
   the file

   An example execution that only produces the PypeIt Reduction File for
   the configuration is:

   This will generate a subfolder containing two files: the base PypeIt
   Reduction File , and its calibration association file .

 

.. _`subsec:edit`:

Edit Your PypeIt File
~~~~~~~~~~~~~~~~~~~~~

The PypeIt Reduction File dictates how the pipeline is executed for your
raw data files. The filename is expected to end with and it has a very
specific format (discussed below). While the file is automatically
generated by the script, it can (and should) be edited by the user to
ensure the reduction happens as expected.

Each unique instrument configuration will have its own PypeIt Reduction
File. In the case of DeVeny, this means different rear filters, grating
tilt angles, binning schemes, or even different gratings used on
different nights. This section describes the file format and the edits a
user may wish to make.

File Format
^^^^^^^^^^^

Here is an example edited PypeIt reduction file:

.. container:: tiny

   ::

      # Auto-generated PypeIt input file using PypeIt version: 1.15.0
      # UTC 2023-10-29T15:08:59.760

      # User-defined execution parameters
      [rdx]
          spectrograph = ldt_deveny
      [baseprocess]
          use_illumflat = True
      [reduce]
          [[findobj]]
              maxnumber_sci = 1

      # Setup
      setup read
      Setup A:
        binning: 1,1
        cenwave: 5195.0
        dispname: DV2 (300/4000)
        filter1: CLEAR
      setup end

      # Data block
      data read
       path /home/observer/data/20210522a
                filename |       frametype |       ra |     dec |      target |         mjd | airmass | exptime | cenwave |filter1 | slitwid | lampstat01 | calib
      20210522.0057.fits |        arc,tilt | 235.9293 | 36.8143 | HgCdAr Arcs |  59356.1319 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 | Cd, Ar, Hg |     0
      20210522.0058.fits |        arc,tilt | 236.0506 | 36.8141 | HgCdAr Arcs |  59356.1322 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 | Cd, Ar, Hg |     0
      20210522.0001.fits |            bias | 149.0345 | 34.9193 |        Bias |  59356.0855 |     1.0 |     0.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0002.fits |            bias | 149.0345 | 34.9193 |        Bias |  59356.0857 |     1.0 |     0.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0003.fits |            bias | 149.0345 | 34.9193 |        Bias |  59356.0858 |     1.0 |     0.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0004.fits |            bias | 149.0345 | 34.9193 |        Bias |  59356.0859 |     1.0 |     0.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0005.fits |            bias | 149.0345 | 34.9193 |        Bias |  59356.0000 |     1.0 |     0.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0032.fits |       illumflat | 144.8190 | 61.4406 |    Sky Flat |  59356.1068 |    1.15 |     8.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0033.fits |       illumflat | 144.8860 | 61.4407 |    Sky Flat |  59356.1070 |    1.15 |     8.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0034.fits |       illumflat | 144.9531 | 61.4407 |    Sky Flat |  59356.1072 |    1.15 |     8.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0035.fits |       illumflat | 145.0201 | 61.4408 |    Sky Flat |  59356.1073 |    1.15 |     8.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0036.fits |       illumflat | 145.0872 | 61.4409 |    Sky Flat |  59356.1075 |    1.15 |     8.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0022.fits | pixelflat,trace | 223.4301 | 36.8472 |   Dome Flat |  59356.0973 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0023.fits | pixelflat,trace | 223.6225 | 36.8469 |   Dome Flat |  59356.0978 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0024.fits | pixelflat,trace | 223.7396 | 36.8468 |   Dome Flat |  59356.0981 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0025.fits | pixelflat,trace | 223.8651 | 36.8466 |   Dome Flat |  59356.0984 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0026.fits | pixelflat,trace | 223.9822 | 36.8464 |   Dome Flat |  59356.0980 |    1.49 |    20.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0078.fits |         science | 210.8212 | 28.6579 | PG 1401+289 |  59356.2038 |    1.01 |   300.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0079.fits |         science | 211.4163 | 28.5236 |    FSBHB 30 |  59356.2106 |    1.01 |   300.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0080.fits |         science | 211.3735 | 28.5425 |    FSBHB 71 |  59356.2150 |    1.01 |   300.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0081.fits |         science | 242.9356 | 12.0713 |  IC 4593 PN |  59356.2222 |    1.28 |   300.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0082.fits |         science | 242.9356 | 12.0713 |  IC 4593 PN |  59356.2266 |    1.26 |    60.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      20210522.0083.fits |         science | 237.9995 | 32.9484 |  BD+33 2642 |  59356.2365 |    1.07 |   300.0 |  5195.0 |  CLEAR |     1.1 |        off |     0
      data end

Several columns (, , , and ) have been removed from the actual file and
coordinates have been truncated for clarity of printing the file here.

 

There are three sections to the file that tell PypeIt how to reduce the
data.

.. _`p:param`:

*Parameter Block*
^^^^^^^^^^^^^^^^^

At the top of the file is the parameter block that allows the user to
customize the data reduction process. Parameter categories are
surrounded by square braces, and the parameters themselves are set with
equal signs. Indenting is not required by PypeIt, but is done here for
visual ease. For the example file above, the first two lines shown:

.. container:: small

      ::

         \PYG{k}{[rdx]}
         \PYG{+w}{   }\PYG{n+na}{spectrograph}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{ldt\PYGZus{}deveny}

are automatically generated by . The parameter is the only one required,
and tells PypeIt which spectrograph configuration parameters to use.

The next lines in the parameter block override PypeIt and
instrument-specific default configurations. The DeVeny-specific
modifications to default PypeIt parameters are already included in the
class (`listed
here <https://pypeit.readthedocs.io/en/release/pypeit_par.html#ldt-deveny-ldt-deveny>`__)
and loaded using the specification above – it is not necessary to
reproduce them in the parameter block of your file. What do go here are
changes away from the *DeVeny default configuration* you wish to use for
reducing a particular data set. For instance, the next five lines in the
example file above:

.. container:: small

      ::

         \PYG{k}{[baseprocess]}
         \PYG{+w}{   }\PYG{n+na}{use\PYGZus{}illumflat}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{True}
         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[findobj]]}
         \PYG{+w}{      }\PYG{n+na}{maxnumber\PYGZus{}sci}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{1}

specify that PypeIt should use the files to correct for illumination
variations along the slit and it should only find and extract the one
brightest object in each science frame. See
§\ `2.2 <#sec:spatial_flexure>`__ for a discussion of the former, but
the latter is helpful if you know you have only one object whose
spectrum you care about in each frame and prevents spurious objects from
ending up in your output 1D spectra files.

A discussion of typical parameter changes that may apply to DeVeny data
is given in §\ `1.5 <#sec:special>`__, and an exhaustive discussion of
all parameters may be found in the PypeIt Documentation: `PypeIt
Parameters <https://pypeit.readthedocs.io/en/release/pypeit_par.html>`__.

Setup Block
^^^^^^^^^^^

The next block, beginning with the line , describes the instrument
configuration. There should only be one setup shown (), and the
parameters provided show the salient metadata for that instrument
configuration. You should not edit any of this; it is informational and
required.

Data Block
^^^^^^^^^^

The largest section of the PypeIt Reduction File is the data block.
Beginning with the line , this section includes the path to the raw data
files and a table describing the files associated with this setup. The
data block is a fixed-format table written by the underlying table
object used by . The symbols need not align but the number per row must
be equal. Users should always generate the PypeIt reduction file using
the script to ensure all data are present as expected, but edits will
often be necessary to deal with edge cases or other situations
unanticipated by the automated routine.

The PypeIt Reduction File is the ultimate authority in terms of how the
data are reduced. As such, you should understand how edits to this file
work because these edits will override anything derived from the FITS
headers! It is common to edit this table in the manners described below.

-  **Add/Remove a File**: You may add or remove files from the data
   block to process the desired files. To add a file, the only safe move
   is to copy in a line from the file generated by
   (§\ `1.3.3 <#pypeit_setup>`__). It needs to be formatted just like
   the others. To remove a file, you may either delete the line or
   comment it out by pre-pending a .

   Here is yet another reminder to not include bad calibration frames in
   the reduction (frames that you do not want to use, frames with
   incorrectly identified types, or frames that could not be
   automatically classified and have a type). Check them now and remove
   them if they are bad.

   A major reason to add files to the Data Block is the presence of two
   different setups for a given data set (two different grating angles),
   but all of the bias frames ended up in one of the setups (based on
   the keyword). PypeIt is getting better at including setup-independent
   files in all configurations, but it is important to double-check. If
   needed, simply copy the bias lines from one file to the other, in
   this instance, so that both setups have access to the bias frames.
   The ordering of table rows in the PypeIt Reduction File does not
   matter, so don’t worry about adding lines in the “proper” location.

-  **Check** : The most common edit for a given data file is its Frame
   Type(s). For DeVeny reduction, you need at least one file with each
   of the following Frame Types (see also
   §\ `1.3.2 <#pype:organize>`__):

   -  : Bias frames (removing fixed-pattern noise)

   -  : Flat fielding (removing pixel-to-pixel sensitivity variations)
      and edge tracing

   -  : Two-dimensional wavelength calibration (colorizing the
      black-and-white spectrum)

   -  : Science exposure (answering the grand questions of the universe)

   Remove / comment out all images with a of , or correct the value.
   PypeIt will NOT run if any of the uncommented frames have under .

   As shown in the example PypeIt reduction file, a given image can have
   multiple frame types – enter the types as a comma-separated list
   without spaces.

-  **Check Names**: Because PypeIt uses the name (encoded in the FITS
   keyword, entered in the DeVeny LOUI) as part of the reduced data
   filename, this column must include only legal characters for your
   filesystem. In general, forward slash () is always disallowed (sorry,
   comet observers), but others may be a concern on your particular
   filesystem. Additionally, parentheses or other characters in names
   may cause issues if such characters are not escaped in shell
   environments.

   In general, names should only include alphanumeric characters,
   spaces, dashes, plus signs, underscores, and periods. Editing the
   name in the PypeIt Reduction File (and not in the actual FITS file
   itself) is sufficient for the limitations mentioned here.

-  **Adjust Groupings**: It is possible to group frames into two or more
   calibration groups that do not share the complete set of raw
   calibration frames. Most often this is used for arc frames taken at
   different telescope positions, but can be used for flats and biases,
   as well. Calibration groups have non-negative integer values, and any
   given calibration frame may belong to more than one calibration
   group, if desired. To specify multiple calibration groups, use a
   comma-separated list () for specific groups or to indicate the frame
   should be used for all calibration groups.

   Care must be exercised in grouping arc frames for wavelength
   calibration. Given the large shifts along the spectral axis of the
   DeVeny CCD caused by flexure (:math:`\sim\pm10` pixels), some
   observers who prefer to take *in situ* arcs at the location of each
   object rather than rely upon PypeIt’s flexure correction based on
   night sky lines (see Appendix `2 <#sec:deal_flexure>`__ and
   §\ `1.6.1 <#sec:pype_flex>`__ for a discussion of flexure
   corrections). The ensemble of *in situ* arcs should definitely
   **not** be grouped together for PypeIt wavelength calibration, as the
   flexure-induced shifts between frames can produce an unusable mess of
   multiple, shifted lines. The safe move here is to assign each set of
   frames at a given pointing (zenith, object A, standard C, etc.) to a
   unique calibration group.

   For further details see Advanced Usage
   (§\ `[sec:pype_advanced] <#sec:pype_advanced>`__).

 

Run the Reduction
~~~~~~~~~~~~~~~~~

PypeIt is designed (and currently only able) to do end-to-end
reductions, resulting in a fully processed 2D spectral image and
extracted 1D spectra (if objects were found) from each science frames.
Once you have completed the setup steps above, you are just about ready
to run the pipeline.

In the directory containing your edited PypeIt Reduction File (), check
for folders left over from previous runs of the pipeline (if
applicable). In particular, be sure to remove any calibration files from
the folder that are stale or old versions.

When you upgrade PypeIt versions, changes to the underlying data models
(which are largely not backwards compatible) may cause errors if you try
to use calibration files processed with an earlier version. The safe
move is to completely reprocess all data currently being used when
PypeIt is upgraded, including recreating all calibrations.

 

.. _section-1:

The main script to execute the PypeIt reduction is . A typical run of
PypeIt is initiated from a subdirectory created with with a command
like:

 

 

The code launches, reads the PypeIt Reduction File, initiates a few
internals, and then proceeds to generate a logorrheic stream of messages
in the terminal window. For the most part, it is safe to ignore the
flood of messages – much of what is there remains from the initial
construction and debugging of PypeIt. If the code should crash before
completing the reduction, the last several lines of output can yield
insight into what happened.

There are two standard options to this script that you should consider
using:

-  or : Using this flag will over-write any existing reduced data in the
   directory. It is recommended that this flag be used in most cases. In
   the event that you only want to re-reduce a few particular science
   frames (and not everything else), remove those particular and output
   files from the directory and without the option.

-  or : This flag tells PypeIt to only run on the calibration files,
   producing the directory and associated quality assurance () files.
   When first running PypeIt or preparing to reduce a large data set,
   this option will allow you to inspect the various calibration files
   (and in particular the wavelength solution) before sinking a lot of
   time into reducing your science frames.

The next section describes the outputs produced by .

 

Primary Output Files and Post-Processing Scripts
------------------------------------------------

.. _`pype:calibrations`:

Examine the Calibration Files
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

As PypeIt begins churning through your reduction, it will create and
write to disk calibration frames in the subfolder of the, directory (see
§\ `1.8 <#sec:pype_filestructure>`__). Additional Quality Assurance
files will be written to the subfolder for some types of Calibration
frames. It is important to take the time to inspect these calibration
outputs as they are generated – preferably by using the option to , or
alternatively while waiting for your science frames to reduce.

The naming convention for Calibration frames is a bit cumbersome, but
follows a regular pattern,

 

 

This is a bias Calibration frame from setup , calibration group ,
detector . The setup is that from the Setup Block of the PypeIt
Reduction File. The group will correspond to what is in the column of
the PypeIt Reduction File – this will be unless you have defined groups
otherwise. As DeVeny has but one detector, the filenames will always end
with . While the list of constituent files that went into any given
Calibration frame is included in its FITS header, PypeIt also overwrites
the file in the same directory as the file that explicitly lists all
input files used to create each Calibration frame.

Here is a brief description of the Calibration frames produced (in the
order in which they are created):

-  **Bias** image () – Processed combined bias frame used to remove
   fixed-pattern noise from all other images. The result is not unlike
   Figure `[fig:bias] <#fig:bias>`__.

-  **Edges** file () – Collection of images and FITS bintables
   describing the slit traces. While this file is primarily of interest
   for multislit or echelle spectrographs (DeVeny has but one slit and
   no cross-disperser, after all), it is instructive to quickly peek at
   this file to ensure the code correctly identified the slit (and not
   some artifact at the edge of the CCD):

   ::

      $ pypeit_chk_edges Calibrations/Edges_A_0_DET01.fits.gz

   This command will launch a GUI viewer to display the combined trace
   image along with a sobel-filtered version used to identify
   illumination discontinuities in the spatial direction (see
   Fig. `1 <#fig:pype_chk_edges>`__). For DeVeny data, it should
   identify a single, wide slit with a (spatial ID) approximately half
   the spatial extent of the CCD image (mid-200s for spatially unbinned
   data). The exact number will vary from grating to grating due to
   differing small roll angles about the dispersion axis when the
   gratings were installed in their cells.

   .. figure:: figs/pypeit_chk_edges_DV2.png
      :alt: Example of output from the script for data taken with the
      DV2 grating. The magenta and green lines in the center panels mark
      the left and right edges of the detected slit. The CCD is about 2
      wide, so at least one edge of the 2 slit should be visible.
      :name: fig:pype_chk_edges
      :width: 7in

      Example of output from the script for data taken with the DV2
      grating. The magenta and green lines in the center panels mark the
      left and right edges of the detected slit. The CCD is about 2
      wide, so at least one edge of the 2 slit should be visible.

-  **Slits** file () – This file contains the distilled internal
   information on the traced slit edges, derived from the file and
   organized in FITS bintables. The best way to assess these data is in
   the GUI. Once again, there should only be one slit.

-  **Arc** image () – Processed combined arc spectral image, where the
   frames are combined using an unclipped mean combine algorithm. The
   result will look like Figure `[fig:DV2_arcs] <#fig:DV2_arcs>`__,
   except rotated as noted previously. Closely examine this image in a
   tool like to ensure it will be suitable for generating a wavelength
   solution. If not, try editing the calibration group information in
   the PypeIt Reduction File to include only a subset of the arc frames
   taken at the same telescope position and rerunning .

-  **Tilt Image** () – Image used to trace the tilting of spectral lines
   across the slit traces to produce an accurate 2D wavelength solution
   for the detector. For the case of DeVeny (single slit trace on the
   sole detector), this is identical to the image.

-   **WaveCalib** output () – Contains the 1D wavelength solution for
   this setup. Inspect the wavelength solution using the script. This is
   an example output from the data described in the PypeIt Reduction
   File of §\ `1.3.4 <#subsec:edit>`__ (DV2 grating,
   :math:`\theta_{\rm grangle} = 22.54\degr`,
   :math:`\lambda_c = 5195`\ Å):

   .. container:: footnotesize

      ::

         $ pypeit_chk_wavecalib Calibrations/WaveCalib_A_0_DET01.fits

          N. SpatID minWave Wave_cen maxWave dWave Nlin     IDs_Wave_range    IDs_Wave_cov(%) mesured_fwhm  RMS
         --- ------ ------- -------- ------- ----- ---- --------------------- --------------- ------------ -----
           0    276  2924.1   5151.2  7385.8 2.173   19  3132.752 -  7274.940            92.8          4.8 0.141

   The central wavelength and wavelength range should be close to what
   you set (see Table `[tab:grangle] <#tab:grangle>`__ for examples),
   and the dispersion () should be close to the value listed in
   Table `[tab:gratings] <#tab:gratings>`__. Note that the listed here
   should match that from .

   As an additional check on the wavelength calibration, or if the
   values from do not line align with expectations, there is a GUI tool
   (Fig. `2 <#fig:pype_show_wvcalib>`__) that displays the
   wavelength-calibrated arc spectrum for comparison with the line
   identification plots in Figs. `[fig:refarcs1] <#fig:refarcs1>`__ -
   `[fig:refarcs5] <#fig:refarcs5>`__. This script requires the to
   display the spectrum, and is run via:

   .. figure:: figs/pypeit_show_wvcalib.png
      :alt: Example of output from the script for the data described
      taken with the DV2 grating. The spectrum should align with the
      line identification plots in
      Figs. `[fig:refarcs1] <#fig:refarcs1>`__ -
      `[fig:refarcs5] <#fig:refarcs5>`__.
      :name: fig:pype_show_wvcalib
      :width: 4.5in

      Example of output from the script for the data described taken
      with the DV2 grating. The spectrum should align with the line
      identification plots in Figs. `[fig:refarcs1] <#fig:refarcs1>`__ -
      `[fig:refarcs5] <#fig:refarcs5>`__.

-  **Tilts** output () – Contains the 2D mapping of the slit to lines of
   constant wavelength. The quality of this step is shown in the images
   of the directory (see
   Fig. `[fig:master_tilts] <#fig:master_tilts>`__), and should rarely
   need much scrutiny for DeVeny data if you have strong arc lines and a
   good wavelength solution.

-  **Flat** images () – Processed combined dome flat fields for removing
   pixel-to-pixel sensitivity variations. PypeIt fits a basis spline ()
   to the spectral direction to remove the structure in the flat lamp
   spectra, and should yield a normalized image with all values close to
   1. Examine the normalized flat field frame using the utility and
   compare with examples from
   Figure `[fig:pype_flats] <#fig:pype_flats>`__.

   The example normalized shown in
   Figure `[fig:pype_goodflat] <#fig:pype_goodflat>`__ from the DV1
   grating illustrates a successful reduction of this frame. The fact
   that the “salt and pepper” random variations increase at the red
   (left) and blue ends of the spectrum is simply the result of very low
   count rates at the extreme ends of the DeVeny’s spectral range.

   The not-so-good example in
   Figure `[fig:pype_badflat] <#fig:pype_badflat>`__ is from a set of
   DV6 data (:math:`\lambda_c = 4000`\ Å) where the flux from the usual
   top-ring (CLST) lamps dropped to zero near the middle of the CCD, and
   PypeIt had a difficult time properly fitting a function to the
   spectrum. This may be an example of when to use the Photo Flood lamps
   (see §\ `[sec:lamps] <#sec:lamps>`__) for flat fielding to produce
   sufficient flux across the detector.

   The GUI launched with also shows the 2D wavelength solution derived
   from when you mouse over the various images. This is a good guide for
   determining whether artifacts seen in the flats are caused by low
   signal at extreme wavelengths.

 

Examine the Science Spectra
~~~~~~~~~~~~~~~~~~~~~~~~~~~

As PypeIt runs (unless the flag is invoked), it will begin generating 2D
and 1D spectra outputs in the folder for each science frame in the
PypeIt Reduction File. Feel free to examine the files as they are
created, even while the code continues to process the other raw frames.

The frames shown in Figures `3 <#fig:pype_spec2d>`__,
`4 <#fig:pype_spec1d>`__,
`[fig:pype_manual_extract] <#fig:pype_manual_extract>`__, and
`[fig:pype_fluxcal] <#fig:pype_fluxcal>`__ were processed with the
DeVeny EMI pickup noise scrubber prior to PypeIt processing (see
Appendix `[app:deveny_pickup] <#app:deveny_pickup>`__).

-  **Examine the 2D spectral images**: During the data-reduction
   process, PypeIt will create a reduced 2D spectral image product for
   each science frame prior to the extraction of 1D spectra. These
   products are stored in multi-extension FITS files with names like:

   where the filename model is:

   You may examine this image product in a tool like , but PypeIt also
   provides a command-line script for viewing the 2D image (with
   overlays of the slit and any objects extracted) in a RC
   (remote-control) viewer. [8]_ It should be called from the working
   directory (the directory you were in when you called ). For instance:

   .. figure:: figs/pypeit_spec2d.png
      :alt: Example of the PypeIt reduced 2D spectrum for the scrubbed
      frame mentioned in the text, displayed in the viewer launched from
      . *Top Left*: the calibrated science image, *top right*:
      sky-subtracted and masked image along the slit bounds (magenta and
      green lines), *bottom left*: the sky-subtracted image divided by
      the pixel-by-pixel uncertainty to yield a residual map including
      the object, *bottom right* the same residual map but with the
      object subtracted. Note that two objects have been identified and
      extracted (orange traces and labels).
      :name: fig:pype_spec2d
      :height: 3in

      Example of the PypeIt reduced 2D spectrum for the scrubbed frame
      mentioned in the text, displayed in the viewer launched from .
      *Top Left*: the calibrated science image, *top right*:
      sky-subtracted and masked image along the slit bounds (magenta and
      green lines), *bottom left*: the sky-subtracted image divided by
      the pixel-by-pixel uncertainty to yield a residual map including
      the object, *bottom right* the same residual map but with the
      object subtracted. Note that two objects have been identified and
      extracted (orange traces and labels).

   This opens 4 tabs in the display (see Fig. `3 <#fig:pype_spec2d>`__),
   one for each of the following:

   -  Procesed image ()

   -  Sky subtracted image ()

   -  Sky residual image (), which is divided by the uncertainty

   -  Full residual image (), which is minus the object model, divided
      by uncertainty

   Magenta/green lines indicate slit edges, as in
   Figure `1 <#fig:pype_chk_edges>`__. Orange and light blue lines (if
   present) indicate traces for automatically detected objects and
   manually extracted objects, respectively. As you mouse around, the
   green coordinates shown at the bottom indicate the pixel number and
   the wavelength. If there are spurious low-signal objects identified
   or PyepIt did not identify your object of interest, you may re-run
   the reduction with adjusted object-finding parameters (see
   §\ `1.5.2 <#pype:find_object>`__).

   Each extracted object is named by its spatial position on the reduced
   image [], slit position on the reduced image [] and the detector
   number []. For instance, the three objects shown in
   Figure `3 <#fig:pype_spec2d>`__ have the labels , , and . The
   single-slit nature of our spectrograph means that multiple objects
   extracted from a given image will have names differing only in the
   code.

   |image| |image1|

   PypeIt provides a script for examining the remaining noise in the
   Full Residual Image (): . This tool produces plots like those in
   Figure `[fig:pype_spec2d_noise] <#fig:pype_spec2d_noise>`__, where
   the image is the same as the lower-right panel in
   Fig. `3 <#fig:pype_spec2d>`__. To make the DeVeny frames look normal,
   invoke this tool thuswise:

   The examples in
   Fig. `[fig:pype_spec2d_noise] <#fig:pype_spec2d_noise>`__ are the
   pre- and post-scrubbed frames discussed in
   Appendix `[app:deveny_pickup] <#app:deveny_pickup>`__. [9]_ The
   histograms at right show pixel values not masked out, with the ideal
   :math:`\sigma = 1` distribution, indicative of photon-limited object
   extraction and sky subtraction, shown in orange. The pre-scrubbed
   frame illustrates the sinusoidal EMI pickup noise that has been
   affecting DeVeny data over the past several years, the effect of
   which on the residual noise is very apparent in the top histogram in
   both width and shape. The post-scrubbed frame not only illustrates
   the removal of the sinusoidal EMI, but also the residual noise more
   closely matches the expected (orange) distribution.

    

-  **Examine the extracted 1D spectra**: If one or more objects have
   been automatically or manually identified in the reduced 2D spectral
   image, 1D data products will be produced. These 1D products are the
   primary outputs of PypeIt, and may be described by a series of
   1-dimensional arrays: vacuum wavelength, extracted flux (from one or
   more methods), and associated error arrays for each identified
   object. These arrays are packaged into multi-extension FITS files,
   and are accompanied by files with extraction information (*read*:
   table of contents) for each 1D spectrum.

   The 1D spectral files have names like:

   where the filename model is identical to the 2D version above.

   .. figure:: figs/pypeit_spec1d.png
      :alt: Example of the PypeIt reduced and extracted 1D spectrum for
      the object mentioned in the text (), displayed in the XSpecGUI
      launched from . The red dotted line indicates the :math:`1\sigma`
      uncertainty in the flux values.
      :name: fig:pype_spec1d
      :height: 3in

      Example of the PypeIt reduced and extracted 1D spectrum for the
      object mentioned in the text (), displayed in the XSpecGUI
      launched from . The red dotted line indicates the :math:`1\sigma`
      uncertainty in the flux values.

   To view the 1D extracted spectra, use the script , which loads the
   data and launches a GUI. Like the 2D version above, it should be
   called from the reduction directory:

   This should launch an XSpecGUI on your screen (see example in
   Fig. `4 <#fig:pype_spec1d>`__). If you wish to view the
   flux-corrected spectrum (after you have completed that step – see
   §\ `1.4.3.2 <#pype:flux>`__), use the option to the call above.

   The accompanying file contains information about the extracted
   object(s), including FWHM of the optimal extraction in arcsec (this
   should be similar to the seeing on the observing night, modulo jitter
   in the star position along the slit), the SNR of the extracted
   spectrum (useful in identifying spurious objects), and the RMS in
   pixels of the wavelength solution (for DeVeny should be the same for
   every object):

   .. container:: footnotesize

      ::

         | slit |                    name | spat_pixpos | spat_fracpos | box_width | opt_fwhm |    s2n | wv_rms |
         |  120 | SPAT0033-SLIT0120-DET01 |        32.9 |        0.117 |      3.80 |    2.188 |   9.13 |  0.065 |
         |  120 | SPAT0128-SLIT0120-DET01 |       128.2 |        0.535 |      3.80 |    2.121 | 146.12 |  0.065 |
         |  120 | SPAT0231-SLIT0120-DET01 |       231.2 |        0.984 |      3.80 |    1.641 |   5.17 |  0.065 |

   By default, loads the first (lowest code) object extracted from the
   2D spectrum. Examination of the spectral image with or printing the
   file will help you identify which extracted object(s) corresponds to
   your desired target(s). If there are spurious low-signal objects
   identified, you may re-run the reduction with adjusted object-finding
   parameters (see §\ `1.5.2 <#pype:find_object>`__). A particular
   extracted object may be loaded into the XSpecGUI by using the option:

   or by specifying a particular FITS extension (1-indexed,
   corresponding to the order of objects listed in the file) via the
   option:

   as was done for Figure `4 <#fig:pype_spec1d>`__.

    

   Unless told to skip it by the parameter , PypeIt performs both a
   boxcar (top-hat) extraction around the trace and a Horne optimal
   extraction [10]_ using the fitted spatial profile. The
   boxcar-extracted spectrum may be displayed using the option to ,
   otherwise the optimal extraction is displayed (if available).

-  **Missing 1D spectra**: Sometimes PypeIt will not extract all (or
   any) of the objects you expect to be in a given frame. This can look
   like either:

   -  some, but not all, of the expected objects were found and
      extracted (orange traces on the images of ) and the file has fewer
      entries than expected, or

   -  no objects were extracted and no file was created.

   In either of these cases, the steps for attempting to extract such
   missing objects are the same:

   #. You may modify the object finding parameters in your PypeIt
      Reduction File (see §\ `1.5.2 <#pype:find_object>`__), remove this
      file, and rerun *without the option*. This will have the effect of
      processing only the one frame, and should run fairly quick. If the
      missing objects are found, you’re done.

   #. If the objects are still not extracted with repeated modification
      of the / parameters, you can attempt to manually identify and
      extract the object. The full instructions are in the `PypeIt
      documentation <https://pypeit.readthedocs.io/en/release/manual.html>`__,
      but the gist is that you will need to add a column to your PypeIt
      Reduction File () containing information about where to find the
      object as a colon-separated list.

      For example, assume you wanted to extract the faint object between
      the two leftmost extracted objects in
      Figure `3 <#fig:pype_spec2d>`__ (see the object-finding QA plot in
      Fig. `6 <#fig:pype_findobj_qa>`__). Using , identify the spatial
      position of the trace around the middle of the detector (). The
      entry in the column of the Pypeit Reduction File is of the form ,
      where the boxcar radius (in pixels) is an optional input.

      For this particular object (which was observed with
      :math:`1\times2` – spectral :math:`\times` spatial – binning), the
      column for this frame would read , where the (*in pixels*) is the
      value of extracted objects listed in the text file divided by the
      spatial plate scale of the spectral image (the DeVeny plate scale
      of 0.34/pixel times the spatial binning).

      The resulting 2D spectral image with the manual trace and 1D
      spectrum of the manually extracted object are shown in
      Figure `[fig:pype_manual_extract] <#fig:pype_manual_extract>`__.
      In this case, even though the object is detectable to the human
      eye, it does not contain enough signal to produce a useable
      spectrum (SNR :math:`\sim 1`). This is the file, including the
      manual extraction:

.. container:: scriptsize

   ::

      | slit |                    name | spat_pixpos | spat_fracpos | box_width | opt_fwhm |    s2n | manual_extract | wv_rms |
      |  120 | SPAT0033-SLIT0120-DET01 |        32.9 |        0.117 |      3.80 |    2.188 |   9.13 |          False |  0.065 |
      |  120 | SPAT0077-SLIT0120-DET01 |        77.5 |        0.317 |      3.80 |    2.108 |   0.88 |           True |  0.065 |
      |  120 | SPAT0128-SLIT0120-DET01 |       128.2 |        0.535 |      3.80 |    2.121 | 146.12 |          False |  0.065 |
      |  120 | SPAT0231-SLIT0120-DET01 |       231.2 |        0.984 |      3.80 |    1.641 |   5.17 |          False |  0.065 |

|image2| |image3|

 

.. _`pype:afterburner`:

Post-Processing the Files
~~~~~~~~~~~~~~~~~~~~~~~~~

While the main PypeIt run ends with files, this is not the end of the
processing available with the package. There are several post-processing
steps that may be considered, depending on the needs of your particular
program:

-  Coadding 2D spectral images of the same target to increase S/N in the
   extracted spectra.

-  Flux calibration of extracted 1D spectra.

-  Coadding / collating flux-calibrated 1D spectra of the same object
   into separate files.

-  Telluric correction for NIR spectra (only relevant for the very red
   end of DeVeny’s range).

.. _pype_coadd2d:

*Coadding 2D Spectral Images*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PypeIt has the ability to coadd 2D spectral images of the same object to
increase signal-to-noise prior to object finding and extraction. This
process is primarily done with multislit instruments taking multiple
frames of the same set of faint objects, but can be done for DeVeny data
if desired. There is a set of `worked
examples <https://pypeit.readthedocs.io/en/release/tutorials/coadd2d_howto.html>`__
in the PypeIt documentation should you wish to do this.

If you plan to coadd multiple 2D spectral images of the same target, you
will want to ensure that telescope guiding is on and stable before you
take your series of exposures. This will ensure your target is in the
same place on the slit in each frame. Coadding is done after the main
PypeIt run and is executed with the script. Because the input files to
this script can be a bit cumbersome, there is a setup script available
that ingests the file or reads FITS headers in a directory as a starting
point.

.. _`pype:flux`:

*Flux Calibrating 1D Spectra*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The main PypeIt run returns extracted 1D spectra, measured in
instrumental units (namely, *electrons*). For some science programs,
this is sufficient, and further processing is unnecessary prior to
analysis (skip ahead to §\ `1.4.4 <#pype:specutils>`__). Other programs
either benefit from or require correcting for the relative spectral
sensitivity of the instrument and converting the instrumental intensity
into physical flux units before the spectra can be analyzed. PypeIt
provides routines for creating a sensitivity function for your data set
from observations of `spectrophotometric standard
stars <https://www.eso.org/sci/observing/tools/standards/spectra/stanlis.html>`__,
and applying that to the remainder of the science data.

If you plan to flux calibrate your spectra, it is imperative to include
one or more `spectrophotometric standard
stars <https://www.eso.org/sci/observing/tools/standards/spectra/stanlis.html>`__
in your observing program. Exactly which stars and when to observe them
depend on the specific requirements of your science program.

Provided here is a brief outline of the flux-calibration steps, and the
reader is encouraged to read the `PypeIt docs on this
topic <https://pypeit.readthedocs.io/en/release/fluxing.html>`__ for an
exhaustive description of both the theoretical background and the steps
and scripts involved in the process.

When performing the flux calibration, files are modified in place,
adding the additional components of the data model (, , etc.) as FITS
extensions.

-   The first step is to build a sensitivity function from your observed
   spectrophotometric standard star that translates the count rate (in
   :math:`{\rm e}^- / {\rm s}`) on the detector as a function of
   wavelength into a flux density (in units of
   :math:`10^{-17} {\rm erg} / {\rm s} / {\rm cm}^2 / {\rm \AA}`). Due
   to factors such as grating blaze and the transmission function of the
   optics in the telescope and spectrograph, this sensitivity function
   will not be uniform and requires careful fitting.

   .. figure:: figs/pypeit_sensfunc_throughput.pdf
      :alt: Example of PypeIt sensitivity function throughput. This
      observation was taken of G191-B2B with DV6 at 27.04 and 1.2 slit
      on the night of 2022-11-02UT.
      :name: fig:pype_transmission
      :height: 3in

      Example of PypeIt sensitivity function throughput. This
      observation was taken of G191-B2B with DV6 at 27.04 and 1.2 slit
      on the night of 2022-11-02UT.

   The script performs this fitting, using the standard star file as the
   input, and outputting a FITS file containing all of the relevant
   sensitivity function information. It may be run by calling (*e.g.*):

   This will produce an output sensitivity function file in the working
   directory – you may name the output file anything you like, but
   preferably something identifiable to the setup and/or date of the
   observation. In addition to the sensitivity function FITS file,
   quality assurance and throughput plots are produced with the same
   base name as the sensitivity function.
   Figure `5 <#fig:pype_transmission>`__ shows the thoughput plot for
   the spectrophotometric standard star G191-B2B taken on 2022-11-02UT
   (the same night as the data in Figs. `3 <#fig:pype_spec2d>`__ -
   `[fig:pype_manual_extract] <#fig:pype_manual_extract>`__).

-   Once you are satisfied with with the sensitivity function, the next
   step is to create a file that drives the actual flux calibration
   process in the way a file guides the main processing run. Execute the
   setup script by feeding it the same of the directory containing the
   science images (by default ):

   This script ingests all of the files in and creates three output
   files for use with the remaining post-processing steps. We will
   discuss the file here, and the others below. As with the Pypeit
   Reduction File, you will need to edit this file (named ) to ensure
   the flux calibration proceeds as expected. Shown below is an example
   file created by the above call to , edited as required for a
   successful run (shown in green). Note that the one edit you *must*
   make is to include the name of the produced by the previous step.
   Since many DeVeny users work blueward of :math:`\sim9000`\ Å and will
   use the algorithm for their sensitivity functions, you will also
   likely need to set the parameter to in the parameter block of the
   file.

   .. container:: footnotesize

      ::

         # Auto-generated Flux input file using PypeIt version: 1.15.0
              # UTC 2023-11-06T18:32:53.162
              
              # User-defined execution parameters
              [fluxcalib]
                extinct_correct = \textcolor{ForestGreen}{True}  # Set to True if your SENSFUNC derived with the UVIS algorithm
              # Please add your SENSFUNC file name below before running pypeit_flux_calib
              
              # Data block 
              flux read
               path Science/
                                                                    filename | sensfile
               spec1d_20221102.0067-B03_43_A_DeVeny_20221102T061001.710.fits | \textcolor{ForestGreen}{../sens_DV6_4900.fits}
               spec1d_20221102.0068-B03_43_B_DeVeny_20221102T062053.580.fits |         
               spec1d_20221102.0069-B03_43_C_DeVeny_20221102T063154.130.fits |         
               spec1d_20221102.0070-B03_43_F_DeVeny_20221102T064254.820.fits |         
               spec1d_20221102.0071-G191-B2B_DeVeny_20221102T065713.770.fits |         
              flux end

   In these examples, all script execution is done from the working
   directory (where the file lives), and the sensitivity file and file
   are both written to the same location. The files are in , as
   specified in the call to above. Therefore, in the file, we need to
   tell the script that the sensitivity file is in the directory *above*
   the 1D spectral files, hence the in front of the filename.

   |image4| |image5|

   In this example, will be used to flux correct all files in the
   lefthand column of the Data block. If you took spectra of multiple
   spectrophotometric standards in a night and wish to assign different
   science frames to different sensitivity functions, simply include the
   name of the appropriate sensitivity FITS file for each science frame
   in the file.

   Once you have this file properly edited, you are ready to apply the
   sensitivity function(s) and flux calibrate your data.

-   After all of the setup work above, the actual flux calibration
   computation is quite straightforward:

   All of the file information and parameter adjustments are in the
   file, and this script requires no additional information. Examples of
   flux-calibrated spectra for the objects in
   Figs. `4 <#fig:pype_spec1d>`__ and
   `[fig:pype_manual_extract] <#fig:pype_manual_extract>`__ are shown in
   Figure `[fig:pype_fluxcal] <#fig:pype_fluxcal>`__.

*Coadding / Collating Flux-Calibrated 1D Spectra*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

PypeIt has the ability to coadd flux-calibrated 1D spectra of the same
object. This may be because you have exposures of the same object from
different nights or the object was placed in different locations along
the slit in different frames, either of which precludes coadding the
processed 2D spectral images. In this case, you may use the script for
coadding these individual flux-calibrated extracted spectra. This step
is less common for DeVeny users; you are encouraged to read the
`documentation on this
topic <https://pypeit.readthedocs.io/en/release/coadd1d.html>`__ if you
wish to perform this action.

Similar to above, the script can process large sets data to match
observations of the same target and produce coadded spectra of all
matching objects. If this is a useful tool for you, please let LDT staff
know your use case and results.

The output of both and involves the
` <https://pypeit.readthedocs.io/en/release/out_onespec.html#current-data-model>`__
data format rather than the
` <https://pypeit.readthedocs.io/en/release/out_spec1D.html#current-data-model>`__
data format used by the files. The primary differences are that data are
written containing all the extracted objects from a single 2D spectral
image (essentially a list containing one or more spectra using the
native, possibly nonuniform, wavelength scale from the original frame),
whereas data contain the spectrum for a single object (usually coadded
from several raw frames) interpolated onto a uniform wavelength grid. If
you choose to analyze your data with , the PypeIt loaders
(§\ `1.4.4 <#pype:specutils>`__) handle all the differences between
these file formats for you.

*Performing a Telluric Correction*
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For observations done at the extreme red end of the DeVeny’s range
(:math:`\gtrsim 9000`\ Å), you will want to perform a telluric
correction to minimize the effects of atmospheric emission on your data.
This step involves comparing your data plus a model of the object’s
intrinsic spectrum to a large atmospheric model grid. If you wish to
perform this step, you will need to `download a telluric
grid <https://pypeit.readthedocs.io/en/release/installing.html#atmospheric-model-grids>`__
or create one of your own (at present, LDT does not have its own grid
available through PypeIt, but the developers recommend using the grid
computed for Mauna Kea).

Once again, if you choose to perform this step, please read through the
`documentation on this
topic <https://pypeit.readthedocs.io/en/release/telluric.html>`__, and
let LDT staff know the use case and how well it worked.

In a future PypeIt release, the mode of telluric correction will change
to a PCA analysis obviating download of large telluric grid files by the
user. Stay tuned for this change.

 

.. _`pype:specutils`:

Loading PypeIt 1D Spectra into for Analysis
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

PypeIt is a package for reducing spectroscopic data from raw frames
collected at the telescope to 1D spectra, ready for analysis. To do the
actual analysis in service of your particular science program, you will
need to employ other tools. One possibility is the Astropy-coordinated
package . [11]_

As of v1.12.2, PypeIt includes a loader for importing pipeline outputs
into , and can import either the (all objects in a frame) or the (output
of ) PypeIt 1D spectral format. These loaders automatically recognize
PypeIt data from the FITS headers and properly parse the data into class
instance(s).

In the examples below, the objects and are shown as coming from the
module, but this mechanism is really just importing the objects and
registering the PypeIt loaders at the same time.

 *format*
^^^^^^^^^

Because a file may contain more than one extracted spectrum from a 2D
spectral image, the loader for this file type requires the use of the
object. This object is is basically a of objects, one for each extracted
spectrum in the file, and can consist of a single element if that is all
that was found.

::

        from pypeit.specutils import SpectrumList
        spec = SpectrumList.read(spec1d_file)

This loader provides PypeIt-specific options (see `the
API <https://pypeit.readthedocs.io/en/develop/api/pypeit.specutils.pypeit_loaders.html#pypeit.specutils.pypeit_loaders.pypeit_spec1d_loader>`__)
that enable you to specify the type of extraction ( or ) used and
whether or not to use the flux-calibrated spectrum. By default, optimal
extraction takes precedence over boxcar extraction, and flux-calibrated
data take precedence over uncalibrated counts.

.. _format-1:

 *format*
^^^^^^^^^

PypeIt files may be loaded into either a object or a single-element
object, as the user desires.

::

        from pypeit.specutils import Spectrum1D
        spec = Spectrum1D.read(onespec_file)

This loader provides a PypeIt-specific option that enables you to select
the uniform grid wavelength vector, instead of the contribution-weighted
wavelengths (see the `module
documentation <https://pypeit.readthedocs.io/en/release/api/pypeit.specutils.pypeit_loaders.html>`__
for details).

 

What you do with the object(s) will be defined by the requirements of
your science program and is beyond the scope of this manual.

 

 

 

.. _`sec:special`:

PypeIt Parameter Modifications for Specific Cases
-------------------------------------------------

There are various situations in which you will need to modify the
Parameter Block of your PypeIt Reduction File (see
§\ `1.3.4.2 <#p:param>`__). The default DeVeny parameters were chosen to
cover the major use cases for the spectrograph, but the instrument’s
high configurability and varied uses means there will still be many
instances where these instrument-specific parameters must be modified.
The principal categories of modifiable parameters for DeVeny users are
grouped below, but the complete list is given
`online <https://pypeit.readthedocs.io/en/release/pypeit_par.html>`__.

Think of parameter modifications as part of an outline, where each level
represents a unique thought. Therefore, if you need to modify both the
arc lamps and the FWHM of the arc lines under wavelength calibrations,
you would include something like:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{lamps}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{HgI,CdI,ArI}
         \PYG{+w}{      }\PYG{n+na}{fwhm}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{7.0}

rather than two individual blocks. In short, each parameter group in
brackets should appear only once in your Parameter Block. Also,
indentation is not necessary but may help in visually organizing the
outline.

 

.. _`wavecalib`:

Wavelength Calibration Parameters
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Arc Lamps
^^^^^^^^^

PypeIt is able to read the identification of the arc lamps energized
directly from the FITS header, and the user is not generally required to
specify which line lists should be used in the wavelength calibration
process. There are, however, cases where such specification is useful or
necessary: *a*) when the user wishes to restrict the list of lines
PypeIt should consider when creating a wavelength solution, and *b*)
when frames taken with different lamps are combined to create a
Calibration frame.

 

The first case should only be necessary for the DV4 and DV8 gratings,
which rely upon the wavelength calibration method. This method takes the
pattern of extracted lines in your Calibration frame and matches it
against the arc line lists for the specified lamps. In some cases,
including the line lists from all energized lamps in the matching can
produce spurious results (using the Hg or Cd lists with very red
spectra, or the Ne list with very blue spectra). In the example of
energizing all four lamps while observing quite red with DV8, you might
want to restrict the lists to only Ne and Ar via:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{lamps}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{NeI\PYGZus{}DeVeny,ArI\PYGZus{}DeVeny}

As of v1.15.0, PypeIt includes instrument-specific line lists for all
four lamps, indicated by the appended in the lamp name. These lists have
been vetted against DeVeny spectra to include lines seen with our lamps
and excluding lines not reliably detected. To specify the PypeIt-default
line lists, you may do so with the above Parameter Block addition, using
just the ion name ( or ).

 

For the second case, the combined Calibration frame will not combine the
FITS keywords from the input frames to produce the complete list of
lines, so the user must manually specify them. Additionally, the
individual frames must be continuum-subtracted in order to properly clip
and combine the spectra into a sensible Calibration frame. Suppose you
wish to combine single-lamp frames of Ar and Hg to create your
Calibration frame. You would need to add the the following to your
Parameter Block:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{lamps}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{HgI\PYGZus{}DeVeny,ArI\PYGZus{}DeVeny}
         \PYG{+w}{   }\PYG{k}{[[arcframe]]}
         \PYG{+w}{      }\PYG{k}{[[[process]]]}
         \PYG{+w}{         }\PYG{n+na}{subtract\PYGZus{}continuum}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{True}
         \PYG{+w}{   }\PYG{k}{[[tiltframe]]}
         \PYG{+w}{      }\PYG{k}{[[[process]]]}
         \PYG{+w}{         }\PYG{n+na}{subtract\PYGZus{}continuum}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{True}

The order of the lamps specified here is inconsequential, as the code
sorts the list internally.

Wavelength Calibration Method
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

For all gratings except DV4 and DV8, template arc spectra using the Hg,
Cd, and Ar lamps are included with PypeIt for use with the wavelength
calibration method. If you are using one of the these gratings and
relying primarily upon Ne for your calibration, it is advisable to
employ the calibration method. Do so by adding the following to your
Parameter Block:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{method}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{holy-grail}

If both the built-in and methods fail to provide an accurate wavelength
calibration, you may manually identify lines and create a template for
use with that night’s data. This process is described in
§\ `1.6.4 <#pyptrouble:wavecal>`__.

Line Width for Arc Frames
^^^^^^^^^^^^^^^^^^^^^^^^^

For wavelength calibration, PypeIt assumes that your spectral line FWHM
are around 3.0 pixels (see §\ `[set5] <#set5>`__), but also measures the
FWHM directly from the file. If you are using arcs taken with a slit
width that produces FWHM significantly different from this value, you
may need to specify the expected value in your PypeIt Reduction File
based on a manual inspection of the arcs. (See
§\ `[sec:demag] <#sec:demag>`__ for a discussion about optimal
slitwidth.) For instance, if you set the slit width to have arc lines
with a FWHM of :math:`\sim9` pixels (say, a 3 slit with DV1), you would
specify:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{fwhm}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{9.0}
         \PYG{+w}{      }\PYG{n+na}{fwhm\PYGZus{}fromlines}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{False}

Specifying forces the code to use the supplied FWHM and may result in a
more successful wavelength calibration.

Wavelength Solution Order
^^^^^^^^^^^^^^^^^^^^^^^^^

Once the lines have been identified, PypeIt iteratively fits a Legendre
polynomial series between pixel and wavelength space. For DeVeny, the
polynomial order of the initial guess and final solution at the
wavelength calibration are grating-dependent, given the varying
wavelength coverages of DeVeny’s grating complement (see
Table `[tab:gratings] <#tab:gratings>`__). Shown in
Table `[tab:pype_legendre] <#tab:pype_legendre>`__ are the values for
these orders for each grating based on manual inspection of wavelength
solutions. If you are unsatisfied with the RMS of the wavelength
solution, adjusting the solution order may improve the situation. These
values may be changed by modifying the parameters:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{n\PYGZus{}first}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{<initial guess>}
         \PYG{+w}{      }\PYG{n+na}{n\PYGZus{}final}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{<final solution>}

.. container:: deluxetable

   | lccclccclcc DV1 & 3 & 5 & & DV4 & 2 & 4 & & DV7 & 2 & 4
   | DV2 & 3 & 5 & & DV5 & 2 & 4 & & DV8 & 2 & 4
   | DV3 & 3 & 5 & & DV6 & 2 & 4 & & DV9 & 2 & 4

Here, is the initial order used in the iterative solution (this may need
modification if a attempt fails), and is the final order of the solution
(this may be modified to alter the RMS of the wavelength solution).

Night Sky Lines for Calibration
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

Use of night sky lines for wavelength calibration is the basis of
DeVeny’s flexure correction (§\ `1.6.1 <#sec:pype_flex>`__). You will
need to take at least one arc spectrum at some point in the night
(during start-of-night calibrations) to establish a wavelength reference
across the CCD. PypeIt extracts the night sky spectrum from the
background of your science frames, and computes an approximate
wavelength calibration by cross-correlating it with an archived sky
spectrum. No additional arcs are needed to make this link, and PypeIt
will compute a pixel shift in the wavelength calibration to match your
science frame with your . No changes to the Parameter Block of your
PypeIt Reduction File are required, as this is the default behavior for
DeVeny data.

PypeIt does support night-sky wavelength calibration for near-infrared
instruments using the copious OH lines in this portion of the spectrum,
but DeVeny does not reach far enough into IR for this method to provide
useful wavelength solutions.

 

.. _`pype:find_object`:

Object Finding and Extraction
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The parameters related to object finding and extraction are generally
modified *after* you have done an initial pass through , and wish to
improve the ability of the code to work with your data.

General Object Finding
^^^^^^^^^^^^^^^^^^^^^^

Refer to the `Object Finding
documentation <https://pypeit.readthedocs.io/en/release/object_finding.html>`__
for full details on the algorithms. Object finding is governed by the
set of parameters, and is carried out on the spectrally-smashed image (a
1D array that represents the summed spatial profile of the exposure).
PypeIt produces a quality assurance plot for object finding on each 2D
spectral image (in the directory) – an example is shown in
Figure `6 <#fig:pype_findobj_qa>`__ for the image in
Fig. `3 <#fig:pype_spec2d>`__.

.. figure:: figs/pypeit_findobj_qa.png
   :alt: Example of PypeIt object finding QA for the 2D spectral image
   shown in Figs. `3 <#fig:pype_spec2d>`__, where the black plot is the
   spectrally summed spatial distribution of signal-to-noise in the
   image. The red dashed line indicates the parameter discussed in the
   text, which can be adjusted to either allow other peaks in the plot
   to “surface” or to “submerge” unwanted objects.
   :name: fig:pype_findobj_qa
   :height: 3in

   Example of PypeIt object finding QA for the 2D spectral image shown
   in Figs. `3 <#fig:pype_spec2d>`__, where the black plot is the
   spectrally summed spatial distribution of signal-to-noise in the
   image. The red dashed line indicates the parameter discussed in the
   text, which can be adjusted to either allow other peaks in the plot
   to “surface” or to “submerge” unwanted objects.

The most commonly modified parameter is , which limits the search to
sources with peak flux in excess of the theshold times the RMS of the
smashed image. The default is (a signal-to-noise of) 50 and you may wish
to modify this parameter to find more/fewer objects. For instance, if
you wish the code to automatically find fainter objects with peak flux
:math:`10\sigma` above the estimated RMS in the integrated slit profile,
you would add the following to the Parameter Block:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[findobj]]}
         \PYG{+w}{      }\PYG{n+na}{snr\PYGZus{}thresh}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{10.}

On the flip side, if you observed fairly bright objects want to
eliminate the inclusion of spurious faint sources in your final file,
you may *increase* to the point that only a single object is detected.
Similarly, you could use the parameter to limit the object finding to a
limited number of objects in each science frame (ordered by flux):

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[findobj]]}
         \PYG{+w}{      }\PYG{n+na}{maxnumber\PYGZus{}sci}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{1}

which would return at most one object from each frame.

Nights with Poor (or Really Excellent) Seeing or Observations of Extended Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

The default initial object finding kernel size for DeVeny data assumes a
seeing of :math:`\sim1.5\arcsec` regardless of binning, [12]_ which
should cover most conditions at LDT when observing pointlike objects. If
the seeing is significantly better or worse than this value – or you are
observing extended objects – and you are having difficulty automatically
finding your desired objects in the frame, you may alter the value with
the parameter. Note that this parameter *is specified in pixels* rather
than arcseconds (the default value is 4.4 pixels for unbinned data).
Compute the needed value via:
:math:`{\rm FWHM} = {\rm seeing} \div 0.34\arcsec/{\rm pixel}  \div {\rm spat\_bin}`.
For instance, if you had 2.5 seeing with unbinned data, you would
specify:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[findobj]]}
         \PYG{+w}{      }\PYG{n+na}{find\PYGZus{}fwhm}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{7.4}

A related parameter you may need to modify is the radius around the peak
of the trace to use for boxcar extraction of the source, *which is
specified in arcseconds*. The DeVeny default value is 1.9 (for a total
boxcar width of 3.8 centered on the trace). You will want this parameter
to be :math:`\sim1.3\times` the seeing to encompass nearly 100% of the
flux assuming a Gaussian profile. So, for the aforementioned 2.5 seeing,
you should specify:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[extraction]]}
         \PYG{+w}{      }\PYG{n+na}{boxcar\PYGZus{}radius}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{3.2}

in your PypeIt Reduction File. Note that, unlike , is specified in
arcseconds, which is unaffected by CCD binning.

All of the above applies equally well to nights with exceptional seeing
(:math:`\leq 0.8\arcsec`), where tightening up these parameters might be
necessary to properly find and extract your spectra or to extended
objects whose profiles along the slit are much wider than the seeing
disk.

Extraction with Extended Emission Lines
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

It is common for bright emission lines to spatially extend beyond the
source continuum, especially for galaxies or comets. In these cases, the
code may reject the emission lines because they present a different
spatial profile from the majority of the flux. While this is a desired
behavior for optimal extraction of the continuum, it leads to incorrect
and non-optimal fluxes for the emission lines.

The current mitigation is to allow the code to reject the pixels for
profile estimation but then to include them in extraction. This may mean
the incurrence of cosmic rays in the extraction. To utilize this
strategy, add the following to the Parameter Block:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[extraction]]}
         \PYG{+w}{      }\PYG{n+na}{use\PYGZus{}2dmodel\PYGZus{}mask}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{False}

It is likely that you will want to use the BOXCAR extractions instead of
the OPTIMAL, but *caveat emptor*. When viewing the 2D spectrum using the
script, you should use the option.

 

For very extended, bright emission lines you may need to additionally
use:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[skysub]]}
         \PYG{+w}{      }\PYG{n+na}{no\PYGZus{}local\PYGZus{}sky}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{True}

to avoid poor local sky subtraction. See the `Sky Subtraction
documentation <https://pypeit.readthedocs.io/en/release/skysub.html>`__
for further details. Note that if this option is used, no object model
will be created or saved (the object *will* be extracted) and the output
of will not look as clean as that shown in
Fig. `3 <#fig:pype_spec2d>`__.

Emission Line Only or High-:math:`z` Objects
^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^^

If you have a faint object with only emission lines or a high-:math:`z`
object what only appears on part of the trace, you may need to specify
the spectral range on the CCD over which the pipeline should search for
the object. Do this with:

.. container:: small

      ::

         \PYG{k}{[reduce]}
         \PYG{+w}{   }\PYG{k}{[[findobj]]}
         \PYG{+w}{      }\PYG{n+na}{find\PYGZus{}min\PYGZus{}max}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{minpixel, maxpixel}

where and are the *spectral* pixels bounding the region you see your
object in the 2D spectra as inspected with . By limiting the spectral
range over which the object finding happens, the S/N in the smashed
image will be improved and the code may be able to more easily identify
the object. If this step doesn’t work, then proceed with manual
extraction as described in
§\ `[pypeitem:missing_1dspec] <#pypeitem:missing_1dspec>`__.

 

.. _`pype:other`:

Miscellaneous Parameters
~~~~~~~~~~~~~~~~~~~~~~~~

Illumination Correction
^^^^^^^^^^^^^^^^^^^^^^^

If your science program requires correcting for the illumination pattern
along the slit, it is possible to turn on this function. Flexure in the
spatial direction is not yet accounted for, and a shifted illumination
function correction can introduce systematic error into extracted
spectra (see Appendix `2.2 <#sec:spatial_flexure>`__). If your science
program requires illumination correction for variations in throughput
along the slit, you may do so using either dome flats or sky flats and
adding the following to the Parameter Block of your PypeIt Reduction
File:

.. container:: small

      ::

         \PYG{k}{[baseprocess]}
         \PYG{+w}{   }\PYG{n+na}{use\PYGZus{}illumflat}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{True}

Twilight sky flats (identified as such in the LOUI -
Fig. `[fig:loui] <#fig:loui>`__ #4) will automatically be labeled with
frame type , but if you wish to use dome flats for an illumination
correction, you will need to add this frame type to your dome flats in
the Data Block of your PypeIt Reduction File. (As shown in
Figure `7 <#fig:illum_function>`__, the illumination function of dome
flats matches that of the sky to :math:`\sim0.5`\ %.)

Beyond the Red
^^^^^^^^^^^^^^

If your spectra are exclusively in the very red end of the DeVeny range
(:math:`\lambda \gtrsim 7000`\ Å), and you are `flux
calibrating <https://pypeit.readthedocs.io/en/release/fluxing.html>`__
your data, you will need to correct for telluric absorption (at
wavelengths below this value, the UVIS extinction model is used for the
sensitivity function). You must specify the IR algorithm when creating
the sensitivity function to correctly account for atmospheric absorption
in this range of the spectrum. LDT staff have not created a telluric
atmospheric model grid for our site, but we suggest using either the
Mauna Kea or Mount Graham values as being generically applicable.

Add one of the following lines to the Parameter Block of your
file: [13]_

.. container:: small

      ::

         \PYG{k}{[sensfunc]}
         \PYG{+w}{   }\PYG{n+na}{algorithm}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{IR}
         \PYG{+w}{   }\PYG{k}{[[IR]]}
         \PYG{+w}{      }\PYG{n+na}{telgridfile}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{TelFit\PYGZus{}MaunaKea\PYGZus{}3100\PYGZus{}26100\PYGZus{}R20000.fits}
         \PYG{+w}{      }\PYG{n+na}{telgridfile}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{TelFit\PYGZus{}MountGraham\PYGZus{}5500\PYGZus{}10500\PYGZus{}R10000.fits}

The code will automatically download the telluric grid file from the
cloud the first time you run the fluxing script – be warned that this
file is :math:`\sim8`\ GB, and may take a while to download. You may
also use the script independently from the fluxing to download and cache
the file.

This functionality has not yet been tested, but please contact LDT staff
with the outcome if you attempt to use this feature.

In a future PypeIt release, the mode of telluric correction will change
to a PCA analysis obviating download of large telluric grid files by the
user. Stay tuned for this change.

 

 

.. _`sec:troubleshooting`:

Special Considerations, Advanced Usage, and Troubleshooting
-----------------------------------------------------------

This section is devoted to special considerations, advanced usage, and
troubleshooting.

.. _`sec:pype_flex`:

Special Consideration: Flexure in DeVeny and How PypeIt Handles It
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

Appendix `2 <#sec:deal_flexure>`__ outlines the flexure that occurs in
the DeVeny camera and general methods of correcting for it. The present
standard method for flexure correction is to apply a flexure shift based
on the extracted sky spectrum during the main PypeIt run. This method
will be applied automatically using the current DeVeny parameters, and
you should use only single-pointing arcs for wavelength calibration
(taken at zenith or the position of the flatfield screen).

This default method of flexure correction computes a cross-correlation
between the extracted sky spectrum and an archived spectrum (currently
the sky above Cerro Paranal). To use a different sky spectrum, specify
(for the Mt. Hamilton, CA spectrum shown in
Fig. `[fig:pype_flexure_qa] <#fig:pype_flexure_qa>`__):

.. container:: small

      ::

         \PYG{k}{[flexure]}
         \PYG{+w}{   }\PYG{n+na}{spectrum}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{sky\PYGZus{}kastb\PYGZus{}600.fits}

The correlation thusly computed is used to shift the wavelength solution
in pixel space to align with the night sky lines extracted from the 2D
image via simple linear interpolation. Examples of the quality assurance
plots for this process are shown in
Figure `[fig:pype_flexure_qa] <#fig:pype_flexure_qa>`__. If you wish to
not have any flexure correction applied, you may specify the following:

.. container:: small

      ::

         \PYG{k}{[flexure]}
         \PYG{+w}{   }\PYG{n+na}{spec\PYGZus{}method}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{skip}

If your science requirements indicate the taking of *in situ* arcs for
wavelength calibration, see §\ `1.6.2 <#pype:groups>`__ for a
description of this advanced usage. In this case, you may want to set ,
otherwise flexure corrections will still be applied. It may be
instructive to see the magnitude of the flexure correction with *in
situ* arcs, which should be well under a pixel.

|image6| |image7|

 

.. _`pype:groups`:

Advanced Usage: Calibration Groups
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

By default, PypeIt will use all calibration frames within a given setup
() for all science frames within that setup. For many DeVeny programs,
this is perfectly acceptable. It is possible, however, to assign
particular calibration frames to specific science frames as required by
the science program.

PypeIt uses the concept of a “calibration group” to define complete sets
of calibration frames (arcs, flats, biases) and the science frames to
which these calibration frames should be applied. The necessary column
is already included in the PypeIt Reduction File produced by , and all
that is necessary is to adjust the values there according to your
requirements. For example, editing the file shown in
§\ `1.3.4 <#subsec:edit>`__, we would end up with a Data Block that
looks something like:

.. container:: scriptsize

   ::

      # Data block
      data read
       path /home/observer/data/20210522a
                filename |       frametype | ... |filter1 | slitwid | lampstat01 | calib
      20210522.0057.fits |        arc,tilt | ... |  CLEAR |     1.1 | Cd, Ar, Hg |   \textcolor{ForestGreen}{1,2}
      20210522.0058.fits |        arc,tilt | ... |  CLEAR |     1.1 | Cd, Ar, Hg |     \textcolor{ForestGreen}{3}
      20210522.0001.fits |            bias | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{all}
      20210522.0002.fits |            bias | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{all}
      ...
      20210522.0032.fits |       illumflat | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{all}
      20210522.0033.fits |       illumflat | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{all}
      ...
      20210522.0022.fits | pixelflat,trace | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{1}
      20210522.0023.fits | pixelflat,trace | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{1}
      20210522.0024.fits | pixelflat,trace | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{2,3}
      20210522.0025.fits | pixelflat,trace | ... |  CLEAR |     1.1 |        off |   \textcolor{ForestGreen}{2,3}
      ...
      20210522.0078.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{1}
      20210522.0079.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{1}
      20210522.0080.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{2}
      20210522.0081.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{2}
      20210522.0082.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{3}
      20210522.0083.fits |         science | ... |  CLEAR |     1.1 |        off |     \textcolor{ForestGreen}{3}
      data end

The values in green have been edited from the original that was output
by the setup script. Here, we have divided the calibrations into 3
separate groups (arbitrarily in this case, for illustration purposes).
You may assign calibration frames to one or more groups via
comma-separated lists or the specifier. Science frames, however, must
belong only to a single calibration group. In the example above, science
frames and () will be reduced with all frames and all frames, but only
the first frame and the first two frames.

This division of frames could be useful if the observer takes both
evening and morning calibration frames (and wished to associate certain
science frames with one set or the other), or requires the use of *in
situ* arcs for wavelength calibration. After successfully processing the
calibration frames (with ), the code will write out a file that
specifies which calibration frames have been assigned to each
calibration group. It will be important to inspect this file before
proceeding with the full reduction to ensure everything is grouped as
expected.

Whether or not you choose to use calibration groups, PypeIt will include
in the FITS cards (of the and files) the list of calibration frames used
to process each science image.

 

.. _`pypetrouble:crashing`:

Troubleshooting: Crash on improper frame types
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If your PypeIt run crashes out very early (just after reading in the
frame metadata), and you get output to your screen similar to:

.. container:: small

   ::

      [INFO]    :: metadata.py 1287 get_frame_types() - Typing files
      [INFO]    :: metadata.py 1297 get_frame_types() - Using user-provided frame types.
      [ERROR]   :: bitmask.py 112 _prep_flags() - The following bit names are not recognized: None
      [ERROR]   :: metadata.py 1303 get_frame_types() - Improper frame type supplied!
                   Check your PypeIt Reduction File
      Traceback (most recent call last):
      ...
          raise PypeItError(msg)
      pypeit.pypmsgs.PypeItError: Improper frame type supplied!
                   Check your PypeIt Reduction File

the issue is the inclusion of files with a of in your PypeIt Reduction
File. Go back to §\ `1.3.4 <#subsec:edit>`__ and verify all files listed
in your PypeIt Reduction File meet the criteria described therein.

As of v1.14.0, PypeIt will automatically comment out lines in the Data
Block with a of , greatly easing headaches related to this issue.

 

.. _`pyptrouble:wavecal`:

Troubleshooting: When Wavelength Calibration Fails
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

The trickiest piece with spectroscopic data reduction is the production
of a valid wavelength calibration. PypeIt produces Quality Assurance
plots of this step for inspection, and you may use the script
(§\ `[chk_wavecalib] <#chk_wavecalib>`__) to determine the accuracy of
the calibration. Figure `[fig:pype_wavecalib] <#fig:pype_wavecalib>`__
shows examples of both accurate and poor wavelength calibrations.

As of v1.9.0, PypeIt contains full wavelength templates for the
150g/mm (DV1), 300g/mm (DV2, DV3), 600g/mm (DV6, DV7), and
1200g/mm (DV9) gratings, with a more complete template for the
500g/mm (DV5) grating added in v1.15.0. The code uses the method to
match your arc spectrum against the template using a cross-correlation
to establish the wavelength baseline for identifying and fitting
individual lines. These templates were created using the Hg, Cd, and Ar
lamps – if your particular data sets do not match this lamp set, the
cross correlation may not work as nicely, and you could end up with a
situation such as Figure `[fig:pype_badwave] <#fig:pype_badwave>`__. For
gratings DV4 and DV8, we do not yet have good template spectra, and so
these gratings rely upon the method based on pattern matching the
detected lines with that expected from the lamps observed. If you take
arcs with these gratings, please let LDT staff know so that our template
archive can grow.

While examining the calibration outputs from
(§\ `1.4.1 <#pype:calibrations>`__), if you find either a wavelength
calibration akin to Figure `[fig:pype_badwave] <#fig:pype_badwave>`__ or
no wavelength calibration at all, the calibration has failed. If
adjusting wavelength calibration parameters
(§\ `1.5.1 <#subsec:wavecalib>`__) does not resolve the issue, the most
efficient way forward is to manually identify the lines using the
`utility <https://pypeit.readthedocs.io/en/release/wave_calib.html#by-hand-approach>`__
and the reference spectra in Appendix `[app:arcs] <#app:arcs>`__. Since
v1.9.0, PypeIt has the ability to cache and directly use the output of .
When you save and quit the GUI, the script will print instructions in
the terminal for using the wavelength solution you just created, namely
adding the following to the parameter block of your PypeIt Reduction
File:

.. container:: small

      ::

         \PYG{k}{[calibrations]}
         \PYG{+w}{   }\PYG{k}{[[wavelengths]]}
         \PYG{+w}{      }\PYG{n+na}{reid\PYGZus{}arxiv}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{wvarxiv\PYGZus{}ldt\PYGZus{}deveny\PYGZus{}<YYYYMMDD>T<HHMM>.fits}
         \PYG{+w}{      }\PYG{n+na}{method}\PYG{+w}{ }\PYG{o}{=}\PYG{+w}{ }\PYG{l+s}{full\PYGZus{}template}

where the date and time in the filename are those of the file’s
creation. Simply add the block and .

If you need to do this for your data, please also send your , , and
DeVeny setup information to LDT Staff so that it may be added to the
standard PypeIt configuration in a future release.

 

Troubleshooting: Other edge cases or weird crashes
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

If you encounter other failure modes of the pipeline, please contact LDT
Staff for troubleshooting. The most efficient method of contact is to
use the channel of the `PypeIt Users
Slack <https://join.slack.com/t/pypeit-users/shared_invite/zt-1kc4rxhsj-vKU1JnUA~8PZE~tPlu~aTg>`__.

 

 

.. _`deveny_workflow`:

Cheat Sheet for Common DeVeny Workflows
---------------------------------------

Listed here is a brief “cheat sheet” of commands for a common DeVeny
workflow for quick reference.

-  Set up the PypeIt Reduction File(s)

   ::

        pypeit_setup -s ldt_deveny
        pypeit_setup -s ldt_deveny -c <all or subset ID>

-  Edit the PypeIt Reduction File(s) as necessary

-  Run PypeIt on the calibrations and inspect

   ::

        run_pypeit ldt_deveny_<subset ID>.pypeit -c
        pypeit_chk_edges ...
        pypeit_chk_wavecalib ...
        pypeit_chk_flats ...
        pypeit_identify ...

-  Run PypeIt on your science data

   ::

        run_pypeit ldt_deveny_<subset ID>.pypeit -o
        pypeit_show_2dspec ...
        pypeit_show_1dspec ...

-  Run any desired afterburner scripts

   ::

        pypeit_sensfunc ...
        pypeit_flux_setup Science/
        pypeit_flux_calib ...

.. _`sec:pype_filestructure`:

Example PypeIt Directory Structure
----------------------------------

This is an example of the directory structure generated by PypeIt, with
the as the base. In this way, both the raw and processed data files are
in the same place.

 

::

   RAWDIR
   ├── 20290101.0001.fits
   ├── 20290101.0002.fits
   ├── ...
   ├── ldt_deveny_A
   │   ├── Calibrations
   │   │   ├── Arc_A_0_DET01.fits
   │   │   ├── Bias_A_0_DET01.fits
   │   │   ├── ...
   │   ├── QA
   │   │   ├── MF_A.html
   │   │   └── PNGs
   │   │       ├── Arc_1dfit_A_0_DET01_S0120.png
   │   │       ├── Arc_FWHMfit_A_0_DET01_S0120.png
   │   │       ├── ...
   │   ├── Science
   │   │   ├── spec1d_20290101.0045-3c273_DeVeny_20290101T044914.020.fits
   │   │   ├── spec1d_20290101.0045-3c273_DeVeny_20290101T044914.020.txt
   │   │   ├── spec2d_20290101.0045-3c273_DeVeny_20290101T044914.020.fits
   │   │   ├── ...
   │   ├── ldt_deveny_A.calib
   │   ├── ldt_deveny_A.log
   │   ├── ldt_deveny_A.pypeit
   ├── setup_files
   │   ├── ldt_deveny.calib
   │   ├── ldt_deveny.obslog
   │   └── ldt_deveny.sorted

.. _`sec:deal_flexure`:

Compensating for Flexure in DeVeny’s Camera
===========================================

The current configuration of the DeVeny CCD camera causes relative
motion between the spectral image and the CCD chip itself as the
instrument’s orientation changes with respect to gravity. Because DeVeny
is mounted on one of the side ports of the LDT instrument cube, it has a
fairly complex relationship with the gravity vector as the mount and
rotator move. The specific cause of this motion is not fully understood,
but it is indistinguishable from physical flexure of the instrument. The
motion of the image on the CCD occurs in both the spectral and spatial
directions, but is more pronounced (and is more problematic) in the
former. Because the spectral image is oriented with the spectroscope
slit along CCD columns, we can discuss the effects of the two motion
directions independently.

 

Movement in the Spectral Direction
----------------------------------

There is evidence of that the spectrum can shift position on the CCD by
greater than ten pixels for different combinations of zenith distance
and cassegrain rotator angle, as seen in
Figure `[fig:DV1_flex] <#fig:DV1_flex>`__. This can have significant
impacts on the wavelength calibration of spectra if science data are
only compared against the start-of-night, zenith-pointing arc frames.
There are several methods to deal with this flexure:

-  If wavelength calibration to better than 10 pixels (:math:`\sim41\AA`
   for DV1, :math:`\sim11\AA` for DV6/DV7) is not required, no
   additional correction is needed.

-  Arc frames may be taken at the sky location of science spectra (ask
   the TO to close the instrument cover), and these are correlated with
   the appropriate science frame during data reduction and analysis. For
   *in situ* comparison arc frames, keep in mind lamp stabilization
   times (Table `[tab:arccover] <#tab:arccover>`__,
   Fig. `[fig:lamps] <#fig:lamps>`__).

-  If present, night sky lines may be used to either provide a full
   wavelength calibration, or at a minimum provide a shift to be applied
   to align the wavelength calibration and the science spectrum. (See
   §\ `1.6.1 <#sec:pype_flex>`__ for a discussion of how this process
   works.)

For the second method, it is important to keep on top of comparison
frames. If your observations hop from object to object across the sky,
an *in situ* arc for each object is recommended. For objects very near
each other (members of a star or galaxy cluster), it may be possible to
spread out comparison arcs, depending on the requirements of your
science program.

The PypeIt spectroscopic data reduction package (see
Appendix `1 <#app:pypeit>`__) utilizes this last method for correcting
spectral flexure in science frames with respect to either start-of-night
arc frames (standard reduction) or *in situ* frames (advanced usage,
§\ `[sec:pype_advanced] <#sec:pype_advanced>`__). A comparison of direct
measurement of spectral line positions with the PypeIt-derived shift
(against the start-of-night frames) is shown in
Figure `[fig:pypeit_flex] <#fig:pypeit_flex>`__. In short, the two
methods agree to within a few tenths of a pixel (:math:`<1\AA` for any
grating), with better agreement for longer science exposures (stronger
night sky lines). The advantage of this method is the time saved in not
taking comparison arc frames (including lamp warm-up). Carefully
consider the pros and cons of each method, including evaluating your
project’s science requirements and inspect your science frames to ensure
the presence and usability of night sky lines.

.. _`sec:spatial_flexure`:

Movement in the Spatial Direction
---------------------------------

In addition to the spectral-direction flexure, the slit image moves
several pixels in the spatial (along-the-slit) direction as a function
of telescope position. Where this motion will cause problems is in
correcting for the illumination function along the slit for accurate
flux calibration.

While designed to be so, the slit jaws are not perfectly smooth and
dust-free. A slit width of 1 means the jaw are separated by only
0.153 mm = 153 . A particulate grain that occludes just 3  of the slit
will block 2% of the light at that location – a small but noticeable
amount. To illustrate this issue, the top panel of
Figure `7 <#fig:illum_function>`__ shows the *illumination function* of
the slit as seen with the DV3 grating on 2021-10-31UT. An illumination
function is generated by flattening the spectrum along the spectral
axis, removing variations as a function of color. As seen in the figure,
there are variations of up to :math:`\sim2\%` within the central rows of
the slit.

Fortunately, flatfielding takes care of the illumination function. The
catch is that, like a wavelength calibration, a dome flat frame from the
start of the night will not necessarily have the telescope in the same
orientation as the science object of interest. The illumination function
can shift several pixels away from its position when the telescope is
pointed at the dome flat screen.

This whole discussion is connected to flux calibrating spectra – the
process of converting the counts in your image into physical units by
comparing science frames with same-night spectra of spectrophotometric
standard stars taken at similar airmass. If your program requires
accurate (better than 2%) flux calibration, you may decide to measure
the illumination function at the position of your science target. Ask
your TO to rotate the dome in front of the telescope and turn on the
top-ring lamps. The light reflected from the inside of the dome
structure will not be as bright as off the dome flat screen, but will be
enough to measure the spatial flexure at that location.

.. figure:: figs/illum_functions.eps
   :alt: Slit illuminations functions for dome and sky flats for the DV3
   grating. Data taken 2021-10-31UT. In the top panel, the sky flat
   (orange) was shifted by :math:`-0.7` pixels to align the features in
   the illumination functions. The bottom panel shows the ratio of
   sky:dome flat illumination functions to gauge the differences between
   sky illumination (identical to science frames) and that cast by the
   cloverleaf pattern of the top-ring lamps. Answer: they generally
   match to within 0.5%.
   :name: fig:illum_function
   :width: 4in

   Slit illuminations functions for dome and sky flats for the DV3
   grating. Data taken 2021-10-31UT. In the top panel, the sky flat
   (orange) was shifted by :math:`-0.7` pixels to align the features in
   the illumination functions. The bottom panel shows the ratio of
   sky:dome flat illumination functions to gauge the differences between
   sky illumination (identical to science frames) and that cast by the
   cloverleaf pattern of the top-ring lamps. Answer: they generally
   match to within 0.5%.

.. [1]
   PypeIt documentation is at
   ` <https://pypeit.readthedocs.io/en/release/>`__

.. [2]
   An Astropy package for spectroscopy –
   ` <https://specutils.readthedocs.io/en/stable/index.html>`__

.. [3]
   The original LDT/DeVeny configuration was introduced in v1.4.2. It
   was updated with added features in v1.8.0, and more complete
   wavelength calibrations in v1.9.0. Refinements in the default
   parameters were included in v1.13.0 and v1.15.0.

.. [4]
   PypeIt does have a (somewhat cumbersome) mechanism for accepting
   pre-existing bad-pixel masks, but the DeVeny CCD is very clean and
   the BPM procedure is fast.

.. [5]
   ` <https://tools.ietf.org/html/rfc1149>`__

.. [6]
   You may specify a file extension other than by using the argument to
   . All raw DeVeny files, however, end with .

.. [7]
   See Appendix `[app:obstools] <#app:obstools>`__ for one option.

.. [8]
   The viewer is installed as part of the PypeIt virtual environment
   (§\ \ `1.2 <#pype:install>`__), and should launch automatically when
   needed. If not, in a terminal type to manually launch the viewer.

.. [9]
   The images here appear reversed from
   Fig. `[fig:scrub_raw] <#fig:scrub_raw>`__ because this script orients
   blue at the left, whereas the DeVeny detector has blue at the right.

.. [10]
   `Horne, K. 1986, PASP, 98,
   609 <https://ui.adsabs.harvard.edu/abs/1986PASP...98..609H/abstract>`__

.. [11]
   ` <https://specutils.readthedocs.io/en/stable/index.html>`__ In
   contrast to PypeIt itself, the use of *does* require knowledge of
   Python for use. This is but one possible analysis tool, and the
   reader is encouraged to seek out the best tool for their particular
   work.

.. [12]
   The actual seeing is usually better than this, but intermittent
   vibration in the instrument cube tends to smear out spectra along the
   slit.

.. [13]
   See the PypeIt `sensitivity function
   documentation <https://pypeit.readthedocs.io/en/release/fluxing.html#pypeit-sensfunc>`__.

.. |image| image:: figs/pypeit_spec2d_noise_prescrub.png
   :width: 7in
.. |image1| image:: figs/pypeit_spec2d_noise_postscrub.png
   :width: 7in
.. |image2| image:: figs/pypeit_spec2d_manual.png
   :height: 1.8in
.. |image3| image:: figs/pypeit_spec1d_manual.png
   :height: 1.8in
.. |image4| image:: figs/pypeit_spec1d_fluxed_A.png
   :width: 3.25in
.. |image5| image:: figs/pypeit_spec1d_fluxed_B.png
   :width: 3.25in
.. |image6| image:: figs/pypeit_flexure_qa1.png
   :height: 1.8in
.. |image7| image:: figs/pypeit_flexure_qa2.png
   :height: 1.8in
