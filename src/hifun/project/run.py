from quickdesktop import quickui
from quickdesktop import common
from quickdesktop import const
from quickdesktop import projectutils
from quickdesktop import wizard
from quickdesktop import tool
from hifun import project
from hifun.project import preprocess
import os
import gtk


def createRun(project=None):
    p = project or projectutils.getActiveProject()

    if p.runs:
        i = 1
        name = "Default_Run" + str(i)
        while name in p.runs:
            i = i + 1
            name = "Default_Run" + str(i)
    else:
        name = "Default_Run"

    runname = quickui.createWidget(quickid="run", description="Name of Run", type="String", value=name)
    subdomains = quickui.createWidget(type="Integer", quickid="subdomains", value=2, description="Number of Subdomains")
    group=quickui.createWidget(type="Group", quickid="rundetails" ,components=[runname,subdomains])
    v = quickui.showDialog(group, parent=tool.getToolWindow())

    if not v:
        return

    preprocess.executeParallelPreprocessor(p,v['subdomains'])
    p.createRun(runname=v['run'], subdomains = v['subdomains'])
    p.save()
    return v['run']

def chooseAndEditRun(project=None):
    project = projectutils.getActiveProject()
    runnames = project.getRunNames()
    r = {}
    for name in runnames:
        r[name] = name
    c = quickui.createWidget(quickid="runname", description="Choose Run", type="Enum", value=project.activerun, options=r)
    runname = quickui.showDialog(c)
    print runname
    if runname:
        editRun(project=project, runname=runname)

def editRun(project=None, runname=None):
    p = project or projectutils.getActiveProject()
    runname = runname or p.activerun
    p.setActiveRun(runname)
    treepath = os.path.join(p[runname]['path'], "run.tree")
    runTree = common.parseTree(treepath, root=runname)
    projectconfigpath = p['projectdir']
    response = quickui.showConfigurationTree(title=runname, tree=runTree, savespace=p[runname]['path'], parent=tool.getToolWindow())
    p.save()
