#
# pypeid_modes.py -- keyboard modes for manipulating PypeIt plots in Ginga
#
#
from ginga.gw.PlotView import PlotViewBase
from ginga.misc import Bunch
from ginga.modes.mode_base import Mode
from ginga.modes.plot2d import Plot2DMode


# Note inheritance from Plot2DMode, which already defines many callbacks
#
class Spec1DMode(Plot2DMode):
    """
    Spec1DMode enables special bindings for viewing PypeIt spec1d files.

    Enter the mode by
    -----------------
    * Space, then "1"

    Exit the mode by
    ----------------
    * Esc

    Mouse/trackpad bindings in mode
    -------------------------------
    * Shift + left click : set pan position
    * middle click : set pan position
    * scroll : zoom in/out
    * ctrl + scroll : zoom in/out X axis only
    * shift + scroll : zoom in/out Y axis only
    * alt + scroll : zoom in/out Y axis only
    * meta + scroll : zoom in/out at cursor

    Keystroke bindings in mode
    --------------------------

    Zooming
    -------
    * equals : zoom in one zoom level
    * ctrl + equals : zoom in X axis one zoom level
    * shift + equals (plus) : zoom in Y axis one zoom level
    * minus : zoom out one zoom level
    * ctrl + minus : zoom out X axis one zoom level
    * shift + minus (underscore): zoom out Y axis one zoom level
    * 9 : zoom out maintaining cursor position
    * ctrl + 9 : zoom out X axis maintaining cursor position
    * shift + 9 (left paren): zoom out Y axis maintaining cursor position
    * 0 : zoom in maintaining cursor position
    * ctrl + 0 : zoom in X axis maintaining cursor position
    * shift + 0 (right paren): zoom in Y axis maintaining cursor position
    * backquote : fit plot to window
    * 1 : fit x axis only to window
    * 2 : fit y axis only to window
    * k : set lower X range to X value at cursor
    * l : set upper X range to X value at cursor
    * K : set lower Y range to Y value at cursor
    * L : set upper Y range to Y value at cursor

    Panning
    -------
    * left arrow : pan left
    * right arrow : pan right
    * up arrow : pan up
    * down arrow : pan down

    Regions
    -------
    * [ : mark lower X boundary of region
    * ] : mark upper X boundary of region
    * backslash : clear region
    * singlequote : (zoom) set X range to region
    * f : fit region and show result
    """

    # Needs to be set by reference viewer (via set_shell_ref) before any
    # channel viewers are created
    fv = None

    @classmethod
    def set_shell_ref(cls, fv):
        cls.fv = fv

    @classmethod
    def is_compatible_viewer(cls, viewer):
        return isinstance(viewer, PlotViewBase)

    def __init__(self, viewer, settings=None):
        super().__init__(viewer, settings=settings)

        self.actions = dict(
            dmod_spec1d=['__1', None, 'spec1d'],

            ms_showxy=['spec1d+nobtn'],
            ms_panset2d=['spec1d+middle', 'spec1d+shift+left'],

            sc_zoom2d=['spec1d+*+scroll'],

            kp_pan_left=['spec1d+*+left'],
            kp_pan_right=['spec1d+*+right'],
            kp_pan_up=['spec1d+*+up'],
            kp_pan_down=['spec1d+*+down'],

            kp_zoom_in=['spec1d++', 'spec1d+='],
            kp_zoom_out=['spec1d+-', 'spec1d+_'],
            kp_zoom_cursor_in=['spec1d+*+0', 'spec1d+*+)'],
            kp_zoom_cursor_out=['spec1d+*+9', 'spec1d+*+('],

            kp_zoom_fit=['spec1d+backquote'],
            kp_zoom_fit_x=['spec1d+1'],
            kp_zoom_fit_y=['spec1d+2'],

            kp_cut_x_lo=['spec1d+k'],
            kp_cut_x_hi=['spec1d+l'],
            kp_cut_x_range=['spec1d+singlequote'],
            kp_cut_y_lo=['spec1d+K'],
            kp_cut_y_hi=['spec1d+L'],

            kp_unsmooth=['spec1d+A'],
            kp_smooth_less=['spec1d+a'],
            kp_smooth_more=['spec1d+s'],

            kp_mark_left=['spec1d+['],
            kp_mark_right=['spec1d+]'],
            kp_mark_clear=['spec1d+backslash'],
            kp_fitting=['spec1d+f'],

            plot_zoom_rate=1.2,
            plot_pan_pct=0.10,
        )

    def __str__(self):
        return 'spec1d'

    def start(self):
        pass

    def stop(self):
        pass

    def get_plugin(self):
        chname = self.fv.get_channel_name(self.viewer)
        channel = self.fv.get_channel(chname)
        pl_obj = channel.opmon.get_plugin('spec1dview')
        return pl_obj

    #####  MOUSE ACTION CALLBACKS #####

    def ms_showxy(self, viewer, event, data_x, data_y):
        """Motion event in the channel viewer window.  Show the pointing
        information under the cursor.
        """
        self.fv.showxy(viewer, data_x, data_y)
        return False

    #####  KEYBOARD ACTION CALLBACKS #####

    def kp_unsmooth(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.unsmooth()

    def kp_smooth_more(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.smooth_more()

    def kp_smooth_less(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.smooth_less()

    def kp_cut_x_range(self, viewer, event, data_x, data_y):
        if not self.canpan:
            return False
        event.accept()
        plugin = self.get_plugin()
        plugin.cut_x_range('mark')

    def kp_mark_left(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.set_region_side('mark', 'left', data_x)

    def kp_mark_right(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.set_region_side('mark', 'right', data_x)

    def kp_mark_clear(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.clear_region('mark')

    def kp_fitting(self, viewer, event, data_x, data_y):
        event.accept()

        plugin = self.get_plugin()
        plugin.fit_range('mark')
