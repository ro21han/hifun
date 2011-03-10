import os
from quickdesktop import quickui
from quickdesktop import common
from quickdesktop import const
from quickdesktop import configuration
from quickdesktop import projectutils
from quickdesktop import resource
import re
import unittest


class MSH2GEOWriter:
 
    def __init__(self,path,output):

        path=path+"/msh_to_geo.inp"
        f=open(path,"w")
        
        f.write(output['path'] + "\n")
        f.write(output['mshfile'] + "\n")
        f.write(output['outputfile'] + "\n")
        f.write(output['zip'] + "\n")
        f.write(output['bcfile'] +"\n")
        f.write(output['scale'] +"\n")
        
        #write bcs
        boundary_conditions = output['bcs']
        # no. of bcs
        f.write(str(len(boundary_conditions)))
        f.write("\n")
        for i in boundary_conditions:
            f.write(i[0]+' '+i[1].replace(' ','_',-1)+" "+ i[2])
            f.write("\n")

	if "cellzone" in output:
		f.write(str(len(output['cellzone'])))
		f.write("\n")
		for k in output['cellzone']:
			f.write(k[0]+' '+str(self.check(k[1],"Porous Zone"))+' '+str(self.check(k[1],"Rotating Zone"))+'\n')
	else:
		f.write("0")
	

        if "interfaces" in output:
	    interface = output['interfaces']

	    l = []
            for item in interface:
		if item[1]:
		   for k in item[1]:
		      if ((item[0], k) not in l) and ((k, item[0]) not in l):
			 l.append((item[0], k))
	    
            f.write(str(len(l)) + "\n")
            for item in l:
		f.write(item[0]+" "+item[1]+"\n")
		
        else:
            f.write("0")
        #XXX FIXME write interface options
        f.close()

    def check(self,l,name):
	if not l or name not in l:
		return 0
	return 1


def writeSolverData():
    p = projectutils.getActiveProject()
    if not p.runs:
        quickui.error("You should create a Run before doing this operation.")
        return
    SolverInpWriter(project=p, runname=p.activerun)

class SolverInpWriter:

    def __init__(self, project=None, runname=None):
        self.project = projectutils.getActiveProject()

        self.runname=runname

        if not self.runname:
            self.runname = p.activerun
        
        path=os.path.join(self.project[self.runname]['path'],"run.tree")
        self.runtree=common.parseTree(path,root=self.runname)
        self.path= self.project[self.runname]['path']
          
        self.bcs=self.project['bcs']
        self.cellzone=self.project['cellzone']
 
        self.configs = self._readConfigTree()
        solverdata=self._getSolverData()
        self.rans_dir=os.path.join(self.project[self.runname]['path'],'Flowsolver_input')
        
        if not os.path.isdir(self.rans_dir):
	   os.mkdir(self.rans_dir)
           if not os.path.isdir(self.rans_dir):
	      quickui.error(message='Unbale to create Flowsolver_input dorectory.')
              raise OSError('Unbale to create Flowsolver_input dorectory.')

        templatePath=self._getTemplate('userchoice.inp_template')
        self._writeSolverData('/userchoice.inp',solverdata,templatePath,)
        templatePath=self._getTemplate('freestream.inp_template')
        self._writeSolverData('/freestream.inp',solverdata,templatePath,)
        templatePath=self._getTemplate('run_option.inp_template')
        self._writeSolverData('run_option.inp',solverdata,templatePath,)
        templatePath=self._getTemplate('boundary_information.inp_template')
        self._writeSolverData('boundary_information.inp',solverdata,templatePath,)
        templatePath=self._getTemplate('lift_drag_contrib.inp_template')
        self._writeSolverData('lift_drag_contrib.inp',solverdata,templatePath,)
        templatePath=self._getTemplate('halt.inp_template')
        self._writeSolverData('halt.inp',solverdata,templatePath,)

	self.createSubdLink()

    def createSubdLink(self):
	if os.path.exists(os.path.join(self.project['projectdir'],'Subds_')+str(self.project[self.runname]['subdomains'])):
	   if not os.path.exists(os.path.join(self.path,'Subdomains')):
              os.symlink(os.path.join(self.project['projectdir'],'Subds_')+str(self.project[self.runname]['subdomains']),os.path.join(self.path,'Subdomains'))
        else:
           quickui.error(message='Unable to locate subdomain directory.')
	   raise OSError('Unable to locate subdomain directory.')


    def _readConfigTree(self):
        def readConfigTree(tree, treeLeaf):
            if type(tree) == type([]):
                [readConfigTree(node, treeLeaf) for node in tree[1:]]
            else:
                treeLeaf[tree]=configuration.getConfiguration(tree,self.path)
		

        configs = {}
        readConfigTree(self.runtree, configs)
        return configs

    def _isBoundaryCondition(self, key):
        w = self.project.pwall
        f = self.project.pfluid
        p = self.project.pinlet

        return re.match(w, key) or re.match(f, key) or re.match(p, key)

    def _getSolverData(self):
        var={}    
        for k,v in self.configs.items() :
            #if not self._isBoundaryCondition(k):
            for i in v['ITEMS']:
               var[i['quickid']] = i['value']

	w_index=2000
        p_index=3000

	wlist=[]
	plist=[]

        for item in self.bcs:
            if item[1] == 'Wall':
	       var['windex_'+item[0]]=w_index=w_index+1
	       wlist.append(item[0])
	    elif item[1] == 'Pressure Inlet':
	       var['pindex_'+item[0]]=p_index=p_index+1
	       plist.append(item[0])

	flist=[]
	for item in self.cellzone:flist.append(item[0])

	porous_index=0

	pat=re.compile(('por_zone_'))

	for k,v in var.items():
	    if re.match(pat,k):
	       if v:
                  porous_index=porous_index+1	       

	var['wallList']=wlist
	var['pinletList']=plist
	var['cfaceList']=flist
	var['no_of_porous']=porous_index
	var['no_of_walls']=w_index-2000
	var['no_of_pinlet']=p_index-3000
	var['no_of_cellzones']=len(self.cellzone)

        return var

    def _getTemplate(self,template):
        template="resource:"+template
        respath=resource.getResource(template)
        return respath

    def _writeSolverData(self,outfile,solverdata,template=None):
        if template:
	   if outfile == 'boundary_information.inp':
              outfile=self.rans_dir+str('/')+outfile
              out=open(outfile,"w")

	      out.write(str(solverdata['no_of_walls'])+'\n')

              if solverdata['no_of_walls'] > 0:
	         for item in solverdata['wallList']:
	  	     out.write(str(solverdata['windex_'+item])+' '+str(solverdata['wall_boundary_type_'+item])+' '+str(solverdata['wall_temp_type_'+item])+'\n')
	             if solverdata['wall_boundary_type_'+item] == 1 and solverdata['wall_temp_type_'+item] == 1:
		        for v in solverdata['Tvelocities_'+item]:
		  	    for x in v:
			        out.write(str(x)+' ')
		        out.write('\n')
	             elif solverdata['wall_boundary_type_'+item] == 1 and solverdata['wall_temp_type_'+item] == 2:
		        for v in solverdata['Tvelocities_'+item]:
			    for x in v:
			        out.write(str(x)+' ')
		        out.write(str(solverdata['walltemp_'+item]))
		        out.write('\n')
	             elif solverdata['wall_boundary_type_'+item] == 2 and solverdata['wall_temp_type_'+item] == 1:
		        out.write(str(solverdata['rotational_speed_'+item])+' ')
		        for v in solverdata['Rvelocities_'+item]:
		     	    for x in v:
			        out.write(str(x)+' ')
		        out.write('\n')
	             elif solverdata['wall_boundary_type_'+item] == 2 and solverdata['wall_temp_type_'+item] == 2:
		        out.write(str(solverdata['rotational_speed_'+item])+' ')
		        for v in solverdata['Rvelocities_'+item]:
		 	    for x in v:
			        out.write(str(x)+' ')
		        out.write(str(solverdata['walltemp_'+item]))
		        out.write('\n')

	      out.write(str(solverdata['no_of_pinlet'])+'\n')

              if solverdata['no_of_pinlet'] > 0:
	         for item in solverdata['pinletList']:
	  	     out.write(str(solverdata['direction_'+item])+' ')
    		     out.write(str(solverdata['inlet_machno_'+item])+' '+str(solverdata['total_pressure_'+item])+' '+str(solverdata['total_temp_'+item])+'\n')
		     if solverdata['direction_'+item] == 2:
			for v in solverdata['specify_direction_'+item]:
		 	    for x in v:
			        out.write(str(x)+' ')
		     else:
			for v in solverdata['specify_direction_'+item]:
		 	    for x in v:
			        out.write('0.0'+' ')

		     out.write('\n')

	      out.write(str(solverdata['no_of_cellzones'])+' ')
              if solverdata['no_of_cellzones'] > 0:
	         out.write(str(solverdata['no_of_porous'])+'\n')
                 if solverdata['no_of_porous'] > 0:
		    for v in range(solverdata['no_of_porous']):
		       out.write(str(v+1)+' ')

		       if type(solverdata['por_zone_'+solverdata['cfaceList'][v]]) == bool:
                          out.write(str(int(solverdata['por_zone_'+solverdata['cfaceList'][v]])))
                          out.write(' ')
		       if type(solverdata['rotating_zone_'+solverdata['cfaceList'][v]]) == bool:
                          out.write(str(int(solverdata['rotating_zone_'+solverdata['cfaceList'][v]])))
                          out.write('\n')

		       if solverdata['por_zone_'+solverdata['cfaceList'][v]]:
 		          for x in solverdata['viscous_res_'+solverdata['cfaceList'][v]]:
		             for y in x:
		                out.write(str(y)+' ')
	   	             out.write('\n')
		          for x in solverdata['inretial_res_'+solverdata['cfaceList'][v]]:
		             for y in x:
		                out.write(str(y)+' ')
		             out.write('\n')

		          if solverdata['rotating_zone_'+solverdata['cfaceList'][v]]:
			     out.write(str(solverdata['rotational_speed_'+solverdata['cfaceList'][v]])+' ')
			     for x in solverdata['Rvelocities_'+item]:
			        for y in x:
			           out.write(str(y)+' ')
			        out.write(' ')
			     out.write('\n') 
		    out.write('\n') 
	      out.close()

	   elif outfile == 'lift_drag_contrib.inp':
              outfile=self.rans_dir+str('/')+outfile
              out=open(outfile,"w")
              if solverdata['no_of_walls'] > 0:
	         for item in solverdata['wallList']:
	  	     out.write(str(int(solverdata['contribution_'+item]))+'\n')
	      out.close()
	   else:
              outfile=self.rans_dir+str('/')+outfile
              out=open(outfile,"w")
              tf=open(template,"r")
              for line in tf.readlines():
                 id=line.split(',',-1)
                 for i in id:
                    i=i.replace('\n','',-1)

                    if type(solverdata[i]) == bool:
                       out.write(str(int(solverdata[i])))
                       out.write('\t')
                    else:
                       out.write(str(solverdata[i]))
                       out.write('\t')
                 out.write("\n")
              tf.close()
              out.close()


class TestSolverWriter(unittest.TestCase):
    def testsolver(self):
        sw=SolverInpWriter()
        data=sw._getSolverData()

        self.assertTrue(data['natureofflow'], 1)

if __name__ == "__main__":
    const.home="/media/ROHAN_W/rep/hifun"
    unittest.main()
