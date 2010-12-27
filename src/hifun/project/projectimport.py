from quickdesktop import wizard 
from quickdesktop import quickui
from quickdesktop import wizard
from quickdesktop import projectutils
from quickdesktop import tool
from quickdesktop import const
from hifun import project
from hifun.parsers import mshparser
from hifun.parsers import solverio
from hifun.project import preprocess
from math import *
import hifun
import re
import os
import subprocess
import shutil
import zipfile

title = "Project creation wizard"

class FileChoosingPage(wizard.Wizpage):
    """
    Page for choosing fluent/gambit msh file.
    """

    def __init__(self, pageid = "FileChoosingPage",title = "Choose Files",
                 description = """
* Give Project Name. It can be alpha-numeric and '_', '-'
* Input .msh file generated from Gambit/Fluent.
* Give boundary condition file generated from 'FLUENT'. It is optional.
"""
                 ):
        wizard.Wizpage.__init__(self,pageid=pageid, title=title, description=description)

    def _validFile(self,x):

        if x and os.path.exists(x) and os.path.isfile(x):
            return
        raise ValueError("Invalid .msh file.")

    def _validName(self, x):
	p=re.compile("[\w_-]+")
	if not re.match(p,x):
		raise ValueError("Project Name should not have special characters except '_' and '-'")

    def _getWidget(self):
        file = quickui.createWidget(type="QFileChooser", quickid="mshfile", description="Select .msh file", action="fileopen", validator=self._validFile, filefilter=(".msh", "*.msh","*.msh.gz", "*.msh.GZ"))
        bcfile = quickui.createWidget(type="QFileChooser", quickid="bcfile", description="Select boundary condition", action="fileopen", validator=None)
        pname = project.getNewProjectName("New_Project")
        projectname = quickui.createWidget(type="String", quickid="projectname", description="Project Name", value= pname, validator=self._validName)
        zipopt = quickui.createWidget(type="Boolean",quickid="zip",description="Zip Output", value=False)


        return quickui.createWidget(type="Group",quickid=self.pageid, components=[projectname, file, bcfile, zipopt])

    def postprocess(self, state, output):
        def parseMesh(meshfile=None, output={}, task=None):
            task.set_text("Parsing mesh")
            p = mshparser.MeshParser(meshfile)
            output['parser'] = p
            
        wizard.Wizpage.postprocess(self, state, output)
        state['mshfile'] = output[self.pageid]['mshfile']
        x = {}
        status = quickui.runWithProgressDialog(state['parent'], "Progress", parseMesh, pulse=True, meshfile=state['mshfile'], output=x)
	if not status:
	   raise IOError('Unable to parse msh file.')

	p = x['parser']
        zones = p.getFaceZones()
        cellzones = p.getCellZones()
	dimension = p.getDimention()

        bcs = [(z['name'], z['bc'], z['id']) for z in zones]
        fluidbcs =  [(z['name'],z['bc'], z['id']) for z in cellzones]
	output.update(BcSelectPage=dict(bcs=bcs))
        state['fluidbcs'] = fluidbcs
        output['allbcs'] = bcs + fluidbcs
	state['bcs'] = output['BcSelectPage']['bcs']
        state['mshval'] = reduce(lambda x,y: x and y, [z['bc'] for z in zones], True)
	output['dimension'] = dimension

class Scale(wizard.Wizpage):
    
    def __init__(self, pageid="Scale", title = "scale",
                 description="""
Choose scale to multiply the X, Y, Z coordinates.
"""
                 ):

        wizard.Wizpage.__init__(self, pageid=pageid, title=title, description= description)

    def _getWidget(self):
        s = quickui.createWidget(type="Float", quickid="scale", value=1.0, description="Scale")
        return quickui.createWidget(type="Group", quickid=self.pageid, components=[s])

    def postprocess(self, state, output):
        try:
           wizard.Wizpage.postprocess(self, state, output)
	except ValueError:
	   raise ValueError('Invalid value entered for scale.')

class BcSelectPage(wizard.Wizpage):
    """
    Page for selecting boundary condition manually
    """

    def __init__(self, pageid = "BcSelectPage",title = "Choose Boundary Condtion",
                 description = """
Set Boundary Conditions manually.
"""
                 ):
        wizard.Wizpage.__init__(self,pageid=pageid, title=title, description=description)

    def preprocess(self, state):
        zonelist = state['bcs']

        bcs = ['Farfield Riemann', 'Interface', 'Interior', 'Internal', 'Pressure Inlet', 'Pressure Outlet', 'Supersonic Inflow', 'Supersonic Outflow', 'Symmetry', 'Wall']

        def validate(v):
            if v in bcs:
                return v
            return None

	if state['mshval']:
            zones = [z[0] for z in zonelist]
            values = [validate(z[1]) for z in zonelist]
        else:
            zones = [item[0] for item in zonelist]
            values = [None for item in zonelist]

	tlist = quickui.createWidget(type="ListPair", quickid="bcs", description="Boundary Condition Assignment", list1=zones, list2=bcs, name1="Zone List", name2="Options")

        self.pagecontents = quickui.createWidget(type="Group", quickid= self.pageid, components=[tlist])
        self.compose()

    def postprocess(self, state, output):
        wizard.Wizpage.postprocess(self, state, output)
	
        bcs = dict([(x,y) for x,y in output[self.pageid]['bcs']])
        
        oldbcs = dict([(x,z) for x,y,z in state['bcs']])
	
        newbcs = []
        interfaces = []
        for name,bc in bcs.items():
	    
            if not bc:
                del output[self.pageid]
                raise ValueError("Boundary condition for %s is not set."%(name))
            elif bc[0]=="Interface":
                interfaces.append(name)

            newbcs.append((name, bc[0], oldbcs[name]))

        if len(interfaces)==1:
            del output[self.pageid]
            raise ValueError("At least two boundaries should be Interfaces.")
        elif len(interfaces)>=2:
            state['interface'] = 1
        else:
            state['interface'] = 0

        output[self.pageid]['bcs']= newbcs
        state['bcs'] = newbcs
        output['allbcs'] = state['bcs'] + state['fluidbcs']


class CellzoneOptionPage(wizard.Wizpage):
    """
    Page for selecting Cellzone options

    """

    def __init__(self, pageid = "CellzoneOptionPage",title = "Choose Cellzone Options",
                 description = """
Note that if both the options need to be assigned to
a cellzone, select them together using shift or ctrl button.
"""
                 ):
        wizard.Wizpage.__init__(self,pageid=pageid, title=title, description=description)

    def preprocess(self, state):
        cellzones = ['Porous Zone', 'Rotating Zone']

        zones = [z[0] for z in state['fluidbcs']]

	clist = quickui.createWidget(type="ListPair", quickid="cellzone", description="Cellzone Options Assignment", list1=zones, list2=cellzones, name1="Zone List", name2="Options", selection="multi")

        self.pagecontents = quickui.createWidget(type="Group", quickid= self.pageid, components=[clist])
        self.compose()

	
class InterfacePairPage(wizard.Wizpage):
    """
    Page for pairing Interfaces manually
    """

    def __init__(self, pageid = "InterfacePairPage",title = "Interface Paring",
                 description = """
Pair interfaces manually.
"""
                 ):
        wizard.Wizpage.__init__(self,pageid=pageid, title=title, description=description)

    def preprocess(self, state):

	ilist = []
        list = state['bcs']
 
	for i in list:
		if i[1] == "Interface" or i[1] == "interface":
			ilist.append(i[0])

        plist = quickui.createWidget(type="PairingInterface",quickid="IList",description="Interface List",options=ilist) 

        self.pagecontents = quickui.createWidget(type="Group", quickid= self.pageid, components=[plist])

        self.compose()

    def postprocess(self, state, output):
        wizard.Wizpage.postprocess(self, state, output)
	print output[self.pageid]['IList']
        interfaces = [i[0] for i in state['bcs'] if i[1]=="Interface"]
        if interfaces:
           for item in output[self.pageid]["IList"]:
               if not item[1]:
                  del output[self.pageid]
                  raise ValueError("Interface %s is not paired, please pair it."%(item[0]))

def getPages():
    return [FileChoosingPage(), Scale(), BcSelectPage(), CellzoneOptionPage(), InterfacePairPage()]

floworder = {
    "*":[("FileChoosingPage", "True")],
    "FileChoosingPage":[("Scale", "True")],
    "Scale":[("BcSelectPage","True")],
    "BcSelectPage":[("CellzoneOptionPage","True")],
    "CellzoneOptionPage":[("InterfacePairPage","state['interface']"),
                    ("*", "True")],
    "InterfacePairPage":[("*","True")]
}

def runWizard():

    parent = tool.getToolWindow()
    outputs=wizard.runWizard(hifun.project.projectimport, parent = parent)

    if outputs:
        projectname=outputs['FileChoosingPage']['projectname']
        mshfile=outputs['FileChoosingPage']['mshfile']
        bcs = outputs['allbcs']
	scale=str(outputs['Scale']['scale'])
#        cellzone = [(item[0], list(item[1])) for item in outputs['CellzoneOptionPage']['cellzone']]
	cellzone=[]
        for item in outputs['CellzoneOptionPage']['cellzone']:
		if item[1] == None:
 		       cellzone.append((item[0], None))
		else:
 		       cellzone.append((item[0], list(item[1])))
        zip_choice = str(int(outputs['FileChoosingPage']['zip']))

	interface=[]
        if 'InterfacePairPage' in outputs and 'IList' in outputs['InterfacePairPage']:
                ipair = outputs['InterfacePairPage']['IList']
		print ipair
            	for item in outputs['InterfacePairPage']['IList']:
		    if item[1]:
		       for k in item[1]:
		          if ((item[0], k) not in interface) and ((k, item[0]) not in interface):
			     interface.append((item[0], k))


        p=project.Project(projectname,mshfile,bcs,cellzone, outputs['dimension'],zip_choice,scale,interface)

        write_msh2geo(p,outputs)

        p.save()

        projectutils.addProject(p)

	file=open('hifunerr.log','w')
        file.write("HIFUN log file"+'\n')
        file.write("=============="+'\n')
	file.close()

def write_msh2geo(p,outputs):
        path = p['projectdir']
        mshfile = outputs['FileChoosingPage']['mshfile']
        if mshfile.endswith(".msh.gz"):
            ext = ".msh.gz"
        elif mshfile.endswith(".msh.GZ"):
            ext = "msh.GZ"
        else:
            ext = ".msh"
        basefilename = os.path.basename(mshfile).replace(ext,".geo")
	toWrite = {}
	toWrite['path'] = path
        toWrite['mshfile'] = mshfile
        toWrite['outputfile'] = os.path.join(path, basefilename)
	toWrite['dimension'] = str(outputs['dimension'])
        toWrite['zip'] = str(int(outputs['FileChoosingPage']['zip']))
        toWrite['bcfile'] = str(outputs['FileChoosingPage']['bcfile'])
        toWrite['scale'] = str(outputs['Scale']['scale'])
        toWrite['bcs'] = outputs['BcSelectPage']['bcs']

	if 'CellzoneOptionPage' in outputs:
	        toWrite['cellzone']=outputs['CellzoneOptionPage']['cellzone']
 
        if 'InterfacePairPage' in outputs:
                toWrite['interfaces'] = outputs['InterfacePairPage']['IList']

        solverio.MSH2GEOWriter(path,toWrite)

	preprocess.executeSerialPreprocessor(p,toWrite)


def openProject():
    value=project.getRepository()
    file = quickui.createWidget(quickid="projectpath", description="Open Project", type = "QFileChooser", action="diropen",value=value)
    f = quickui.showDialog(file, parent=tool.getToolWindow())
    if not f:
        return
    project.openProject(f)

