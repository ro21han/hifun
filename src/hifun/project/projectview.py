import pygtk
import threading
import gobject
from hifun import project
from hifun import properties
from quickdesktop import resource
from quickdesktop import quickui
from quickdesktop import projectutils
from quickdesktop import events
from quickdesktop import menus
from quickdesktop import plugin
pygtk.require("2.0")
import gtk


class ProjectNavigator(gtk.VBox):
    
    def __init__(self):
        gtk.VBox.__init__(self, True, 10)
        self.project = None
        self._setupWidgets()
        self.addProjectOpenedListener()
        self.addProjectClosedListener()
        self.addRunAddedListener()
        self.addRunActivatedListener()

    def _setupWidgets(self):
        self.treescroll = gtk.ScrolledWindow()
        self.pack_start(self.treescroll, True, True, 0)

    def addProjectOpenedListener(self):
        CODE = """
listenerObject.openProject(eventData['project'])"""
        events.addEventListener(projectutils.PROJECT_OPENED, self, CODE, {})

    def addProjectClosedListener(self):
        CODE = """
listenerObject.closeProject(eventData['project'])"""
        events.addEventListener(projectutils.PROJECT_CLOSED, self, CODE, {})

    def addRunAddedListener(self):
        CODE = """
listenerObject.runAdded(eventData['run'])"""
        events.addEventListener(project.RUN_ADDED, self, CODE, {})

    def addRunActivatedListener(self):
        CODE = """
listenerObject.runActivated(eventData['run'])"""
        events.addEventListener(project.RUN_ACTIVATED, self, CODE, {})


    def runAdded(self, run):
        itr = self.treeStore.get_iter_root()
        self.treeStore.append(itr, [self.runicon, run['name']])

    def runActivated(self, runname):
        if self.project:
            self.refreshIcons(runname)

    def openProject(self, hifunproject):
        self.project = hifunproject
        self._setupTree()
        self.treeWidget.show()

    def closeProject(self, hifunproject):
        if self.project == hifunproject:
            self.project = None
            if self.treeWidget:
                self.treeWidget.destroy()
                self.treeWidget = None
        else:
            print "Error!XXXX fix me"

    def _setupTree(self):
        self.projecticon = self._getIcon(resource.getResource("resource:project.png"))
        self.runicon = self._getIcon(resource.getResource("resource:run.png"))
        self.activerunicon = self._getIcon(resource.getResource("resource:activerun.png"))

        self.treeStore = self._createTreeStore(self.project)
        self.treeWidget = gtk.TreeView(self.treeStore)
        self.tvcolumn = gtk.TreeViewColumn("Project")
        self.treeWidget.append_column(self.tvcolumn)

        self.cellpb = gtk.CellRendererPixbuf()
        self.tvcolumn.pack_start(self.cellpb, False)
        self.tvcolumn.set_attributes(self.cellpb,pixbuf=0)

        self.cell = gtk.CellRendererText()
        self.tvcolumn.pack_start(self.cell, True)
        self.tvcolumn.set_attributes(self.cell,text=1)

        self.treeWidget.set_search_column(1)
        self.treeWidget.set_reorderable(False)
        self.treeWidget.connect("cursor-changed", self.activeNodeChanged)
        self.treeWidget.connect("button_press_event", self.mouseClick)
        self.treescroll.add(self.treeWidget)

    def mouseClick(self, treeview, event):
        if event.type == gtk.gdk._2BUTTON_PRESS and event.button == 1:
            self.doubleclick(event)
        if event.button==3:
            self.popupmenu(treeview, event)

    def doubleclick(self, event):
        nodetype, node = self.getObjectAtMouse(event)
        properties.showProperties(node, nodetype)

    def getObjectAtMouse(self,event):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = self.treeWidget.get_path_at_pos(x, y)

        nodetype = None
        node = None
        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            if  path == (0,):
                nodetype = "project"
                node = self.project
            else:
                nodetype = "run"
                itr = self.treeStore.get_iter(path)
                nodeobject = self.treeStore.get_value(itr, 1)
                node = self.project[nodeobject]
        return nodetype, node

    def popupmenu(self, treeview, event):
        x = int(event.x)
        y = int(event.y)
        time = event.time
        pthinfo = treeview.get_path_at_pos(x, y)

        if pthinfo is not None:
            path, col, cellx, celly = pthinfo
            nodetype,  node = self.getObjectAtMouse(event)
            menu = self.getRightClickMenu(nodetype, node)            
            treeview.grab_focus()
            treeview.set_cursor( path, col, 0)
            menu.menu.popup( None, None, None, event.button, time)

    def getRightClickMenu(self, menuname, node):
        menudata = plugin.PluginManager().getPlugin(menuname + "rightclick")
        data = {}

        data['node'] = node
        if menuname == "project":
            data['nodetype'] = "project"
        elif menuname == "run":
            data['nodetype'] = "run"
        else:
            data['nodetype'] = None

        data['project'] = self.project
        data['topwindow'] = quickui.getParentWindow(self.treeWidget)
        menu = menus.createInstance(menus.Menu, menudata, data=data)
        menu.show()
        return menu

    def activeNodeChanged(self, treeview):
        treeselection = self.treeWidget.get_selection()
	model, itr1 = treeselection.get_selected()
        if not itr1:
            return
        if  model.iter_parent(itr1):
            activerun = model.get(itr1, 1)[0]
            self.project.setActiveRun(activerun)
            self.project.save()
            self.refreshIcons(activerun)

    def refreshIcons(self, activerun):
        rootiter = self.treeStore.get_iter_root()
        itr = self.treeStore.iter_children(rootiter)
        while itr:
            r = self.treeStore.get_value(itr, 1)
            if r == activerun:
                self.treeStore.set(itr, 0, self.activerunicon)
            else:
                self.treeStore.set(itr, 0, self.runicon)
            itr = self.treeStore.iter_next(itr)

    def _getIcon(self, path):
        i = gtk.Image()
        print path
        i.set_from_file(path)
        return i.get_pixbuf()

    def _createTreeStore(self, hifunproject):
        store = gtk.TreeStore(gtk.gdk.Pixbuf,str)
        itr = store.append(None, [self.projecticon, hifunproject['name']])
        for r in hifunproject.runs.keys():
            if hifunproject.activerun == r:
                itrr = store.append(itr, [self.activerunicon, r])
            else:
                itrr = store.append(itr, [self.runicon, r])

        return store
    
    def show(self):
        gtk.VBox.show(self)
        self.treescroll.show()

