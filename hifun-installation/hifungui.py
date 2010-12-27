#!/usr/bin/python

from quickdesktop.tool import ToolWindow
from quickdesktop import const
from quickdesktop import quickui
import gtk
gtk.gdk.threads_init()

if __name__=="__main__":
    import sys
    const.home = sys.argv[1]
    tw = ToolWindow()
    tw.show()
