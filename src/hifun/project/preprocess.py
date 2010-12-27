from quickdesktop import wizard 
from quickdesktop import quickui
from quickdesktop import wizard
from quickdesktop import projectutils
from quickdesktop import tool
from quickdesktop import const
from hifun.parsers import mshparser
from hifun.parsers import solverio
from hifun import project
#from hifun.project import projectimport
from math import *
import hifun
import re
import os
import subprocess
import shutil
import zipfile
import gzip

exeValList={'executeMsh':['geofile'],'executeTwo2Three':['convert3dout'],'executeArea':['outfilename'],'executeNsupport':['nodecellfile','cellfacefile'],'executeMinDist':['min_dist_file'],'executeFsupport':['fsupportfile'],'executeGraph':['graphfile'],'executeMetis':['partfile']}

def executeSerialPreprocessor(p,output): 

    exeList=[executeMsh,executeTwo2Three,executeArea,executeNsupport,executeMinDist,executeFsupport,executeGraph]

    errMsgList=['Unable to execute .msh to .geo convertor.','Unable to convert to 3D from 2D.','Unable to finish Geometric parameters computation.','Unable to finish Node Cell  support computation.','Unable to finish Minimum distance computation','Unable to finish Cell support computation.','Unable to finish Graph computation']

    labelList=['msh Convertor','2D to 3D Convertor','Compute Area','Node cell support computation','Minimum distance computation','Cell support computation','Graph computation']

    out={}

    set_Serial_Preprocess_Data(x=out,p=p)

    parent=tool.getToolWindow()

    os.chdir(out['path'])

    for i in range(len(exeList)):
       if output['dimension']=='2' and exeList[i].func_name=='executeTwo2Three':
          processExecution(parent=parent,label=labelList[i],exe=exeList[i], pulse=False,errmsg=errMsgList[i],out=out)
       elif not exeList[i].func_name == 'executeTwo2Three':
          processExecution(parent=parent,label=labelList[i],exe=exeList[i], pulse=False,errmsg=errMsgList[i],out=out)

    os.chdir(out['cexepath'])

def processExecution(parent=None,label=None,exe=None,pulse=True,errmsg=None,out={}):

    status = quickui.runWithProgressDialog(parent,label,exe,pulse=pulse,output=out)
    
    for item in exeValList[exe.func_name]:
       checkOutputFile(out=out,key=item,status=status,errmsg=errmsg)

def checkOutputFile(out={},key=None,status=False,errmsg=None):
    parent=tool.getToolWindow()

    if int(out['zip_opt']):
       status = quickui.runWithProgressDialog(parent,'Zipping',zip_File,pulse=True,key=key,output=out)

    if not status or (not os.path.isfile(out[key]) and not os.path.isfile(out[key]+'.gz') ):
       quickui.error(message=errmsg)
       raise IOError(errmsg)

def set_Serial_Preprocess_Data(x={},p=None):
    p = p or projectutils.getActiveProject()

    x['path']=path=p['projectdir']

    mshfile=p['mshfile']

    if mshfile.endswith(".msh.gz"):
       ext = ".msh.gz"
    elif mshfile.endswith(".msh.GZ"):
       ext = "msh.GZ"
    else:
       ext = ".msh"
    filename = os.path.basename(mshfile).replace(ext,".geo")

    if not 'cexepath' in x.keys():
       x['cexepath']=os.getcwd()

    x['geofile'] = os.path.join(path, filename)

    filename = os.path.basename(mshfile).replace(ext,".OUT")

    x['outfilename']=os.path.join(path, filename)

    x['scale'] = p['scale']

    x['nodecellfile']=os.path.join(path,"NODECELL.OUT")
    x['cellfacefile']=os.path.join(path,"CELLFACE.OUT")

    x['min_dist_file']=os.path.join(path,"min_distance.out")

    x['fsupportfile']=os.path.join(path,"FSUPPORT.OUT")

    x['graphfile']=os.path.join(path,"unstructured.graph")

    x['zip_opt']=p['zip_opt']

    x['cellzone_file']=os.path.join(x['path'],"cellzone.dat")

    if int(x['zip_opt']):
       #x['geofile']=x['geofile']+'.gz'
       x['cmd']='gunzip -c'
    else:
       x['cmd']='cat'

    x['convert3dout']=x['geofile']
    x['geofile_2d']=os.path.join(path,"2Dgeom.geo")

def executeMsh(output={},task=None):

    msh_exe=os.path.join(const.home,"bin/cas2geo_mod5")

    inp_file = os.path.join(output['path'],"msh_to_geo.inp")

    msh2geo=[msh_exe,inp_file]

    pipe=subprocess.PIPE
    p1=subprocess.Popen(msh2geo,stdin=pipe,stdout=pipe,stderr=pipe)

    progressUpdate(p=p1,task=task)

    p1.wait()

def executeTwo2Three(output={},task=None):

    os.rename(output['geofile'],output['geofile_2d'])
    if int(output['zip_opt']):
       os.rename(output['geofile_2d'],output['geofile_2d']+'.gz')
       output['geofile_2d']=output['geofile_2d']+'.gz'

    f=open('extract_3D_from_2D.inp','w')
    f.write('1.0'+'\n'+output['convert3dout'])
    f.close()

    two2three=os.path.join(const.home,"bin/extract_3D_from_2D")

    cmd=output['cmd'].split()
    cmd.append(output['geofile_2d'])
 
    pipe=subprocess.PIPE
    p1=subprocess.Popen(cmd,stdin=pipe,stdout=pipe,stderr=pipe)

    pipe2=subprocess.PIPE
    p2=subprocess.Popen(two2three,stdin=p1.stdout,stdout=pipe2,stderr=pipe2)

    progressUpdate(p=p2,task=task)
    p1.wait()
    p2.wait()

def executeArea(output={},task=None):

    filepath="area_geo.inp"

    f=open(filepath,"w")
    f.write('1.0' + "\n" + output['outfilename'])
    f.close()

    area_exe=os.path.join(const.home,"bin/area_vis_fg_mod")
    area_cmd=output['cmd'].split()
    area_cmd.append(output['geofile'])
       
    pipe1=subprocess.PIPE
    p2=subprocess.Popen(area_cmd,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    pipe=subprocess.PIPE
    p1=subprocess.Popen([area_exe],stdin=p2.stdout,stdout=pipe,stderr=pipe)

    progressUpdate(p=p1,task=task)
     
    p1.wait()
    

def executeNsupport(output={},task=None):

    nsup_inp="node_cell_support.inp"

    nc_exe=os.path.join(const.home,"bin/nc_supp")

    f=open(nsup_inp,"w")
    f.write(output['nodecellfile'] + "\n" + output['cellfacefile'])
    f.close()

    cmd=output['cmd'].split()
    cmd.append(output['outfilename'])

    pipe1=subprocess.PIPE
    p1=subprocess.Popen(cmd,stdout=pipe1)

    pipe=subprocess.PIPE
    p2=subprocess.Popen(nc_exe,stdin=p1.stdout,stdout=pipe,stderr=pipe)

    progressUpdate(p=p2,task=task)
    p1.wait()
    p2.wait()

def executeMinDist(output={},task=None):

    min_dist_inp="min_distance.inp"

    f=open(min_dist_inp,"w")
    f.write(output['outfilename']+'\n')
    f.write(output['nodecellfile']+'\n')
    f.write(output['min_dist_file'])
    f.close()

    min_dist_exe=os.path.join(const.home,"bin/min_dist")

    pipe=subprocess.PIPE
    p2=subprocess.Popen(min_dist_exe,stdin=pipe,stdout=pipe,stderr=pipe)

    progressUpdate(p=p2,task=task)

    p2.wait()


def executeFsupport(output={},task=None):
  
    fsupport_inp="support.inp"

    f=open(fsupport_inp,"w")
    f.write(output['fsupportfile'])
    f.close()

    fs_exe=os.path.join(const.home,"bin/supp")

    cmd=output['cmd'].split()
    cmd.append(output['outfilename'])
 
    pipe1=subprocess.PIPE
    p1=subprocess.Popen(cmd,stdout=pipe1)

    pipe=subprocess.PIPE
    p2=subprocess.Popen(fs_exe,stdin=p1.stdout,stdout=pipe,stderr=pipe)

    progressUpdate(p=p2,task=task)
    p1.wait()
    p2.wait()


def executeGraph(output={},task=None):

    graph_inp="m2g3d.inp"

    ug_exe=os.path.join(const.home,"bin/m2g3d_hn")

    f=open(graph_inp,"w")
    f.write("10" + "\n" + output['graphfile'])
    f.close()

    cmd=output['cmd'].split()
    cmd.append(output['outfilename'])
    cmd.append(output['fsupportfile'])

    pipe1=subprocess.PIPE
    p1=subprocess.Popen(cmd,stdout=pipe1)

    pipe=subprocess.PIPE
    p2=subprocess.Popen(ug_exe,stdin=p1.stdout,stdout=pipe,stderr=pipe)

    progressUpdate(p=p2,task=task)

    p2.wait()

#================================================================================================

def executeParallelPreprocessor(p,subds):

    out={}
    out['no_of_subds']=str(subds)

    parent = tool.getToolWindow()

    set_Parallel_Preprocess_Data(x=out,p=p)

    os.chdir(out['path'])

    if subds < 2:
       quickui.error(message='Number of subdomains are less than 2. Unable to Execute.')
       raise ValueError
    
    metis=os.path.join(const.home,"Third_Party/METIS/kmetis")

    if not metis:
       quickui.error(message='KMETIS not found. Unable to proceed')
       raise RuntimeError

    if os.path.exists(out['subd_dir']):
       msg="Subdomain Directory "+out['subd_dir']+" is already available. Do you want to overwrite?."
       subd=quickui.question(message=msg)
       if subd == -8:
	  shutil.rmtree(out['subd_dir'])
       else:
          return
 
    if out['graphfile'].endswith('.gz'):
       out['graphfile']=unzip_File(out['graphfile'])
      
    quickui.runWithProgressDialog(parent, "METIS", executeMetis, pulse=True, output=out)

    if int(out['zip_opt']):
       quickui.runWithProgressDialog(parent, "Zipping", zip_File, pulse=True, key='graphfile',output=out)
       #zip_File(key='graphfile',output=out,task=None)

    if not os.path.isfile(out['partfile']):
       quickui.error(message='Unable to create part file.')
       raise IOError

    if int(out['zip_opt']):
       quickui.runWithProgressDialog(parent, "Zipping", zip_File, pulse=True, key='partfile',output=out)
       #out['partfile']=zip_File(out['partfile'])


    if not os.path.isfile(out['cellzone_file']):
       quickui.error(message='cellzone.dat file not found in project directory. Unable to proceed.')
       raise IOError
 
    os.mkdir(out['subd_dir'])

    if not os.path.exists(out['subd_dir']):
       msg="Unable to create Subdomain Directory "+out['subd_dir']+"."
       subd=quickui.info(message=msg)
       raise OSError("Unable to create Subdomain Directory")
            
    os.chdir(out['subd_dir'])

    quickui.runWithProgressDialog(parent, "FEP", executeFEP, pulse=False,output=out)

    ps=re.compile(('SUBDOMAIN.'))

    slist=os.listdir(os.getcwd())
    lst=[]
    for item in slist:
       if re.match(ps,item):
          lst.append(item)

    if len(lst) != int(out['no_of_subds']):
       quickui.error(message='Unable to create SUBDOMAINS.')
       shutil.rmtree(out['subd_dir'])
       raise IOError

    os.chdir(out['cexepath'])

def set_Parallel_Preprocess_Data(x={},p=None):

    set_Serial_Preprocess_Data(x=x,p=p)

    if int(x['zip_opt']):
       for key in x.keys():
 	  if os.path.isfile(x[key]+'.gz') and (not x[key].endswith('.gz') or not x[key].endswith('.GZ')):
	     x[key]=x[key]+'.gz'

    x['subd_dir']=os.path.join(x['path'],"Subds_")+x['no_of_subds']

    x['partfile']=os.path.join(x['path'],'unstructured.graph.part.')+x['no_of_subds']

    x['partfile']=x['partfile'].strip()

def executeMetis(output={},task=None):

    metis=os.path.join(const.home,'Third_Party/Metis')+'/kmetis'

    metis_cmd=[metis,output['graphfile'],output['no_of_subds']]

    pipe=subprocess.PIPE
    p2=subprocess.Popen(metis_cmd,stdin=pipe,stdout=pipe,stderr=pipe)
    p2.wait()


def executeFEP(output={},task=None):

    fep=os.path.join(const.home,"bin/fep_nb_hn_opt_mod_gz")
    output['mychoice']='mychoice.inp'

    f=open(output['mychoice'],"w")
    f.write(output['no_of_subds'] + "\n"+str(1)+"\n"+str(1)+"\n"+output['zip_opt'])
    f.close()

    if int(output['zip_opt']):
       zip_File(key='mychoice',output=output,task=None)
       #output['cellzone_file']=zip_File(output['cellzone_file'])

    fep_cmd=[fep,output['mychoice'],output['outfilename'],output['partfile'],output['nodecellfile'],output['cellfacefile'],output['min_dist_file'],output['cellzone_file']]

    pipe=subprocess.PIPE
    p2=subprocess.Popen(fep_cmd,stdin=pipe,stdout=pipe,stderr=pipe)

    progressUpdate(p=p2,task=task) 

    p2.wait()


def progressUpdate(p=None,task=None): 
    fin=open('hifunerr.log','a')
    line=p.stdout.readline() 

    while line:
	  line=line.strip()

          if line=='SSS':
             line=p.stdout.readline() 
             line=line.strip()
       	     task.set_text(line)
		
	     frac=0.0
	     while frac<=1.0:

		   line=p.stdout.readline() 
	           line=line.strip()
	           try:
	               frac=float(line)
	           except ValueError:
	               fin.write(line+'\n')
	    	       break
	           task.set_fraction(frac)
          else:
	     fin.write(line+'\n')
          line=p.stdout.readline() 
    fin.close() 

def zip_File(key=None,output={},task=None):
    if os.path.isfile(output[key]) and (not output[key].endswith('.gz') and not output[key].endswith('.GZ')):
       if istext(output[key]):
          zipoutfile=output[key]+'.gz'
          p=subprocess.Popen(['gzip','-f',output[key]])
          p.wait()
          output[key]=zipoutfile
       elif not output[key].endswith('.gz') and not output[key].endswith('.GZ'):
	  os.rename(output[key],output[key]+'.gz')
          output[key]=output[key]+'.gz'

def unzip_File(fin=None):

    if fin.endswith('.gz'):
       subprocess.Popen(['gunzip', fin])
       return fin[:-3]
    else:
       return fin

def istext(path):
    return (re.search(r':.* text',subprocess.Popen(["file", '-L', path],stdout=subprocess.PIPE).stdout.read()) is not None)


