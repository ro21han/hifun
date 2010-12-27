from quickdesktop import common
from quickdesktop import resource
from quickdesktop import quickui
from quickdesktop import tool

def showToolOptions():

    treepath = resource.getResource("resource:tooloptions.tree")
    optionTree = common.parseTree(treepath, root="Options")
    quickui.showConfigurationTree(title="Tool Options", tree=optionTree, parent=tool.getToolWindow())    
