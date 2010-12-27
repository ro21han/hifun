from quickdesktop import common
from quickdesktop import quickui
from quickdesktop import tool

class PropManager(common.DataManager):
    
    def __init__(self):
        common.DataManager.__init__(self, "properties", ".prop")

def showProperties(node, nodetype, parent=None):
    parent = parent or tool.getToolWindow()
    data = PropManager().getData(nodetype)

    widgets = {}
    for p in data['PROPERTIES']:
        name = p['name']
        w = createPropWidget(node, p)
        if p['type'] in ["String", "Integer", "Float"]:
            w.set_editable(False)
        elif p['type'] not in ["Table"]:
            w.set_sensitive(False)
        widgets[name] = w

    if data['LAYOUT']:
        layout = {}
        for k,v in data['LAYOUT'][0].items():
            if type(v)==type([]):
                layout[k] = v
            else:
                layout[k] = [i.rstrip().lstrip() for i in v.split(",")]
    else: layout = {}
    
    c = quickui.createLayout(layout, widgets)
    quickui.showDialog(c, parent=parent)

def createPropWidget(node, properties):
    items = [item for item in properties.keys() if item!="name"]
    args = dict([(item, properties[item]) for item in items])
    name = properties['name']
    return quickui.createWidget(quickid = name, value=node.getProperty(name), **args)
  
