from quickdesktop import configuration
from quickdesktop import const
from quickdesktop import storage
from quickdesktop import common
from quickdesktop import projectutils
from quickdesktop import events
from quickdesktop import resource
from hifun import tools
import os
import unittest
import re

RUN_ACTIVATED = "RUN_ACTIVATED"
RUN_ADDED     = "RUN_ADDED"

def getRepository():
    return tools.getRepository()

def openProject(path):
    path = os.path.abspath(path)
    name = os.path.basename(path)
    items = storage.load(os.path.join(path, name))
    p = Project(items=items)
    projectutils.addProject(p)
    
class Run(storage.Storable):
    
    def __init__(self, name = None, subdomains=None, cellzone=None, path = None, project=None, items=None):
        if items:
            storage.Storable.__init__(self, items=items)
            self.project = project
        else:
            self.project = project
            self.name = name
            self.subdomains = subdomains
            self.cellzone = cellzone
            if not path:
                self.path = project._getRunDir(name)
            else:
                self.path = path
    
    def __getitem__(self, name):
        if name == "name":
            return self.name
        elif name == "subdomains":
            return self.subdomains
        elif name == "path":
            return self.path
        elif name == "project":
            return self.project
        elif name == "storagepath":
            return os.path.join(self.path, self.name)
        
    def getDict(self):
        d = storage.Storable.getDict(self)
        del d['project'] # it will be recursive otheriwse
        return d

    def save(self):
        os.mkdir(self.path)

        treepath = resource.getResource("resource:run.tree")
        runTree = common.parseTree(treepath, root=self.name)
        bctree = self.project._getBCTree()
        runTree.append(bctree)

        cm = configuration.ConfigurationManager(savespace=self.path)
        cm.getConfiguration("wall")

        def write(cm, originalconfid, confid):
            def isCellzoneSet():
                l = [item[0] for item in self.cellzone]
		return confid in l

            def check(cellzonetype):
                if isCellzoneSet():
                    index = [item[0] for item in self.cellzone].index(confid)
                    if self.cellzone[index][1]:
                        return cellzonetype in self.cellzone[index][1]
		    else:
			return None

            confdata = cm.getConfiguration(originalconfid)
            confdata['id'] = confid
            path = cm._getSavedFilePath(confid)
            quickidmap = {}
            for i in confdata['ITEMS']:
                quickidmap[i['quickid']] = "_".join([i['quickid'], confid])

            for i in confdata['ITEMS']:
                if i['quickid'] == "por_zone" and check("Porous Zone"):
                    i['value'] = True
                elif i['quickid'] == "rotating_zone" and check("Rotating Zone"):
                    i['value'] = True
                i['quickid'] = quickidmap[i['quickid']]
                if 'hideon' in i:
                    hideon = i['hideon']
                    for k,v in quickidmap.items():
                        hideon = hideon.replace(k, v)
                    i['hideon'] = hideon
                print i['quickid']
            cm._writeConfiguration(confdata, path)

        [write(cm, "fluid", fluidid) for fluidid in self.project._getBoundaries(self.project.pfluid)]
        [write(cm, "wall", wallid) for wallid in self.project._getBoundaries(self.project.pwall)]
        [write(cm, "pressure_inlet", prinlet) for prinlet in self.project._getBoundaries(self.project.pinlet)]
        treepath = os.path.join(self.path, "run.tree")
        common.writeTree(runTree, treepath)
        filepath = os.path.join(self.path, self.name)
        storage.save(self, filepath)

    def getProperty(self, name):
        return vars(self)[name]

class Project(storage.Storable):

    def __init__(self, name=None, mshfile=None, bcs=None, cellzone=None, dimension=None, zip_opt=None, scale='1.0',interface=None,items=None):
        if items:# will be called for opening existing project
            storage.Storable.__init__(self, items=items)
            self.runs = {}
            for k in self.runpaths.keys():
                items = storage.load(self.runpaths[k])
                self.runs[k] = Run(project=self, items = items)
            if self.activerun:
                self.setActiveRun(self.activerun)
        else:
            rep = tools.getRepository()#this will be called only for new creation
            self.name = name
            self.mshfile = mshfile
            self.cellzone = cellzone
            self.dimension = dimension
            self.projectdir = os.path.join(rep, name)
            self.bcs = bcs # boundary conditions
            self.zip_opt=zip_opt
            self.runs = {}
            self.runpaths = {}
            self.activerun = None
	    self.scale = scale
	    self.interface=interface
            self.pfluid = "[Ff][Ll][Uu][Ii][Dd]"
            self.pwall = "[Ww][Aa][Ll]{2,2}"
            self.pinlet = "[Pp][Rr][Ee][Ss][Ss][Uu][Rr][Ee][-_ ][Ii][Nn][Ll][Ee][Tt]"
            try:
                os.mkdir(rep)
            except:
                pass
            os.mkdir(self.projectdir)

    def save(self):
        path = os.path.join(self.projectdir, self.name)
	storage.save(self, path)

    def getRunNames(self):
        return self.runs.keys()

    def getActiveRun(self):
        return self.runs[self.activerun]    

    def __getitem__(self, name):
        if name=="projectdir":
            return self.projectdir
        elif name =="name":
            return self.name
        elif name =="run":
            return self.runs[self.activerun]
        elif name == "runname":
            return self.activerun
	elif name == "mshfile":
	    return self.mshfile
	elif name == "zip_opt":
	     return self.zip_opt
	elif name == "bcs":
	     return self.bcs
	elif name == "cellzone":
	     return self.cellzone
	elif name == "scale":
	     return self.scale
	elif name == "ipair":
	     return self.interface
	elif name == "dimension":
	     return self.dimension
        elif name in self.getRunNames():
	     return self.runs[name]
        else:
            raise KeyError(name)
        
    def getDict(self):
        d = storage.Storable.getDict(self)
        del d['runs']
        return d

    def getProperty(self, name):
        if name=="bcs":
            return [(name, bc) for name, bc, index in self.bcs]
        elif name=="runs":
            return ",".join(self.getRunNames())
        elif name=="cellzone":
	    celllist=[]
	    for item in self.cellzone:
		if item[1]:
		   celllist.append((item[0],common.ListValue(item[1])))
		else:
		   celllist.append((item[0],item[1]))
		
            return celllist
        elif name=="scale":
            return self.scale
        elif name=="dimension":
            return self.dimension
        elif name=="ipair":
	     ilist=[]
	     if self.interface:
		for item in self.interface:
		   ilist.append((item[0],item[1]))
             return ilist
        else:
            return vars(self)[name]
        
    def _getRunDir(self, runname):
        return os.path.join(self.projectdir, runname + "_RUN")

    def createRun(self, runname, path=None, subdomains=None):
        r = Run(name=runname, subdomains=subdomains, path=path, project=self, cellzone=self.cellzone)
        r.save()
        self.runs[runname] = r
        self.runpaths[runname] = r['storagepath']
        e = events.EventMulticaster()
        e.dispatchEvent(RUN_ADDED, { 'type' : RUN_ADDED,
                                     'origin' : self, 
                                     'run':r
                                     })

    def setActiveRun(self, runname):
        self.activerun = runname
        e = events.EventMulticaster()
        e.dispatchEvent(RUN_ACTIVATED, {'type':RUN_ACTIVATED,
                                             'origin':self,
                                             'run':runname
                                             })

    def _getBoundaries(self, pattern=None):
        return [name for name, bc, id in self.bcs if re.match(pattern, bc)]

    def _getBCTree(self):
        l = ["Boundary Conditions"]
        fluid = ["Fluid"] + self._getBoundaries(self.pfluid)
        wall = ["Wall"] + self._getBoundaries(self.pwall)
        pressure_inlet = ["Pressure Inlet"] + self._getBoundaries(self.pinlet)
        if fluid[1:]: l.append(fluid)
        if wall[1:]: l.append(wall)
        if pressure_inlet[1:]: l.append(pressure_inlet)

        return l

    def delete(self):
        def delTree(path):
            if os.path.isdir(path):
                delTree(os.listdir(path))
                os.removedirs(path)
            else:
                os.unlink(path)
        delTree(self.projectdir)


def getNewProjectName(basename):
    rep = tools.getRepository()
    print rep
    if not os.path.exists(os.path.join(rep, basename)):
        return basename
    i = 0
    while os.path.exists(os.path.join(rep, basename+str(i))):
        i = i +1
    return basename + str(i)
    

class TestProject(unittest.TestCase):
    
    def testProjectSimple(self):
        name = "Dummy"
        p = Project(name, "/tmp/x.msh", bcs=[("Wall1","wall"), ("Wall2","wall"), ("Fluid1", "fluid")])
        self.assertEqual(p['name'], name)
        rep = tools.getRepository()
        path = os.path.join(rep, name)
        self.assertEqual(p['projectdir'], path)
        self.assertTrue(os.path.exists(p['projectdir']))
        p.createRun("SampleRun")
        self.assertTrue(os.path.exists(p['SampleRun']['path']))
        treefile = os.path.join(p['SampleRun']['path'], "run.tree")
        wall1 = os.path.join(p['SampleRun']['path'], "config", "Wall1.conf")
        wall2 = os.path.join(p['SampleRun']['path'], "config", "Wall2.conf")
        fluid1 = os.path.join(p['SampleRun']['path'], "config", "Fluid1.conf")
        self.assertTrue(os.path.exists(treefile))
        self.assertTrue(os.path.exists(wall1))
        self.assertTrue(os.path.exists(wall2))
        self.assertTrue(os.path.exists(fluid1))
        p.delete()

    


if __name__=="__main__":
    const.home = "/home/vikrant/programming/work/rep/hifun"
    unittest.main()
