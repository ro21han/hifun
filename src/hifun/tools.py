from quickdesktop import common
from quickdesktop import resource
from quickdesktop import quickui
from quickdesktop import tool
from quickdesktop import configuration
import os


def getUserSpecificLocation():
    s = os.path.join(os.environ['HOME'], ".hifun")
    if not os.path.exists(s):
        os.mkdir(s)
    return s

def getConfSaveSpace():
    return getUserSpecificLocation()

def getRepository():
    return configuration.getConfigValue("toolsettings:repository", getConfSaveSpace())

def showToolOptions():
    savespace = getConfSaveSpace()
    treepath = resource.getResource("resource:tooloptions.tree")
    optionTree = common.parseTree(treepath, root="Options")
    quickui.showConfigurationTree(title="Tool Options", tree=optionTree, parent=tool.getToolWindow(), savespace=savespace)    
