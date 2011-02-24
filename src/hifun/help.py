from quickdesktop import quickui
from quickdesktop import resource
from quickdesktop import tool
import gtk


def showAbout(parent=None):
    about = gtk.AboutDialog()
    parent = parent or tool.getToolWindow()
    print parent
    about.set_position(gtk.WIN_POS_CENTER_ON_PARENT)
    about.set_parent_window(parent)

    image = gtk.gdk.pixbuf_new_from_file(resource.getResource("resource:logo.xpm"))
    about.set_logo(image)
    quickui.setIcon(about)
    about.set_program_name("HiFUN")
    about.set_version("1.0")
    about.set_authors(["Nikhil Shende","Rohan W", "Vikrant Patil"])
    about.set_website("http://www.sandi.co.in")
    about.run()
    about.destroy()
