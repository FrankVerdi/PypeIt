#!/usr/bin/env python

"""
Check that the installation of python is C enabled.
"""

from pypeit.scripts import scriptbase

class ChkPlugins(scriptbase.ScriptBase):

    @staticmethod
    def main(args):

        from pypeit.display import required_plugins, plugins_available
        from pypeit import msgs
        from pypeit import PypeItError

        success, report = plugins_available(return_report=True)
        if not success:
            raise PypeItError(report)
        msgs.info('All required plugins found: {0}'.format(', '.join(required_plugins)))


