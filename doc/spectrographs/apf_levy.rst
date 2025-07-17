.. highlight:: rest

********
APF Levy
********


Overview
========

This file summarizes the APF high resolution spectrometer,
called the Levy after the donors. The spectrometer
is a cross-dispersed echelle spectrograph with a fixed
position for the all of the dispersive elements.
The only important characteristics from a data 
reduction perspective are the length the slit,
which can be either 3 or 8 arc-seconds, and the
binning used on the the detector which cab be
either 1x1 or 2x2.

Frame Types
-----------

There are a set of standard cailibrations frames that 
are acquired each night. These include:
- wide flat 
- dark
- arc lamp (ThAr)
- narrow flat
- iodine cell flats

The arc frames are usually taken with the pinhole, 3 and
8 arc-second long slits. The wide flats are taken
with the 8 arc-second long slit that are 2 arcseconds in width,
while the narrow flats are taken with the 3 arc-second long slit.

Currently the wide flats AND the narrow flats are identified 
as trace frames in the PypeIt file. *EDIT the PypeIt file to
use the wide flats for the trace images for  8 arc-second
long slit science frames and the narrow flats for the trace 
frames for the 3 arc-second long slit science frames.*


Flat Fielding
-------------

For the flat fields, currently the nightly calibrations
produce 50 "wide flats" but only 12 "narrow flats".
The 3"  arc-second long slit is used for the narrow flats
and the 8" arc-second long slit is used for the wide flats.


Slit tracing
------------

Files labeled as narrow flats are used for the
slit tracing for data taken with the 3 arc-second long
slit.

The WideFlat images should also be used for slit tracing 
for data taken with the 8 arc-second long slit.

**Note**: The WideFlat images will not be automatically
assigned as a Trace images for the 8 arc-second long slit
configuration. 

This must be done manually by the user by editing the
PypeIt file.

Wavelength Calibration
----------------------

The wavelength calibration is done using ThAr lamps, which
are also used to compute the Tilt frames.

Iodine cell observations are not used for the wavelength
calibration. To correctly use the iodine cell requires 
specialized software which is not supported by PypeIt.

Object detection
----------------

The sky subtraction is turned off during the object 
detection step. The pixel sampling is coarse, with 
the pixels having a size of 0.4" in the spatial 
direction. Typical object sizes are a full-width
at half maximum of  4 pixels  in the spectrum while a 3 
arc-second long slit has only 8 pixels in the spatial 
direction.

For faint objects observed with the 8 arc-second long
slit, turning on the sky subtraction in the object 
detection step may be helpful.
