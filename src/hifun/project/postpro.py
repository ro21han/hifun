from hifun import project
from hifun.project import run
from hifun.project import preprocess
from hifun import properties
from quickdesktop import resource
from quickdesktop import quickui
from quickdesktop import projectutils
from quickdesktop import events
from quickdesktop import const
from quickdesktop import tool
import linecache
import gtk
import os
import subprocess
import re


def PostProcess(project=None):
    p = project or projectutils.getActiveProject()
    x={}

    activeRun=p.getActiveRun()

    x['path']=path=p['projectdir']

    x['rundir']=activeRun['path'] or None

    if not os.path.isfile(os.path.join(x['rundir'],'userchoice.inp')) and \
       not os.path.isfile(os.path.join(x['rundir'],'freestream.inp')) and \
       not os.path.isfile(os.path.join(x['rundir'],'boundary_information.inp')):
       quickui.warning(message='Required files are not available in current run directory.\nUnable to proceed.') 
       raise IOError('Required files are not available in current run directory. Unable to proceed.')

    x['subd']=activeRun['subdomains'] or 0

    setPostproData(x=x,p=p)

    if not os.path.exists(x['postdir']):
	os.mkdir(x['postdir'])

    rb=quickui.createWidget(type="RadioButton", quickid="radio1",description="Select output type",options={0:"Wall Surface Mesh",1:"Volume Mesh"},value=0)
    v = quickui.showDialog(rb, parent=tool.getToolWindow())

    if v==None:  
       return;

    if rb.value == 0:
       runSurface(out=x)
    elif rb.value == 1:
       runVolume(out=x)
    os.chdir(x['cexepath'])

def setPostproData(x={},p=None):
    p = p or projectutils.getActiveProject()

    path = x['path']

    x['zip_opt']=p['zip_opt']

    if not 'cexepath' in x:
       x['cexepath']=os.getcwd()

    mshfile=p['mshfile']

    if mshfile.endswith(".msh.gz"):
       ext = ".msh.gz"
    elif mshfile.endswith(".msh.GZ"):
       ext = "msh.GZ"
    else:
       ext = ".msh"
  
    x['subd_dir']=subds_dir=os.path.join(path,'Subds_')+str(x['subd'])

    if int(x['zip_opt']):
       x['min_dist_file']=os.path.join(path,"min_distance.out.gz")
       x['geoout']=os.path.join(path,os.path.basename(mshfile).replace(ext,".geo.gz"))
       x['cmd']=['gunzip', '-c']
    else:
       x['geoout']=os.path.join(path,os.path.basename(mshfile).replace(ext,".geo"))
       x['min_dist_file']=os.path.join(path,"min_distance.out")
       x['cmd']=['cat']

    if os.path.isfile(x['min_dist_file']):
	x['min_dist_flag']='1'
    else:
	x['min_dist_flag']='0'

    x['postdir']=os.path.join(x['rundir'],"Postprocessor")

    x['voldir']=os.path.join(x['postdir'],"Volume_Data")
    x['surfacedir']=os.path.join(x['postdir'],"Surface_Data")

    x['vtkout']=os.path.join(x['voldir'],os.path.basename(mshfile).replace(ext,".vtk"))
    x['cgnsout']=os.path.join(x['voldir'],os.path.basename(mshfile).replace(ext,".cgns"))
    x['pltout']=os.path.join(x['surfacedir'],os.path.basename(mshfile).replace(ext,".plt"))
    x['restartout']=os.path.join(x['postdir'],'restart.dat')
    x['frc_mnt_file']=os.path.join(x['surfacedir'],"forces_moments_store.dat")
    x['int_coff_file']=os.path.join(x['surfacedir'],"integrated_coeffs.dat")

    x['ndims']='3'
    x['solver_opt']='1'
    x['gamma']="1.4"
    x['gas_constant']="287.0"
    x['file_type']='1'
    x['sensor_flag']='0'
    x['sol_flag']='0'

    nature_of_flow=linecache.getline(os.path.join(x['rundir'],'Flowsolver_input','userchoice.inp'),1)
    turb_model=linecache.getline(os.path.join(x['rundir'],'Flowsolver_input','userchoice.inp'),7)

    nature_of_flow=nature_of_flow.strip()
    turb_model=turb_model.strip()

    if (nature_of_flow == '2' and turb_model == '0') or (nature_of_flow == '1'):
       x['flow_opt']='1'
    elif nature_of_flow == '2' and turb_model == '2':
       x['flow_opt']='2'
    else:
       x['flow_opt']='0'


def runVolume(out={}):

    parent=tool.getToolWindow()

    if os.path.exists(out['rundir']):

       os.chdir(out['postdir'])
       sub=re.compile(('SUBDOMAIN.[0-9]+')) 
       res=re.compile(('restart[0-9]+.dat')) 

       sdirlist=os.listdir(out['subd_dir'])
       rdirlist=os.listdir(out['rundir'])
  
       slist=[]
       rlist=[]

       for item in sdirlist:
           if re.match(sub,item):
              slist.append(item)
       for item in rdirlist:
           if re.match(res,item):
              rlist.append(item)
  
       if len(slist)==out['subd'] and len(slist)==len(rlist):

          slist.sort()
          rlist.sort()
          out['sol_flag']='1'
          
          if checkFile(out=out,key='restartout'):
             msg='restart.dat is already available in \n'+out['postdir']+'\n Do you want to overwrite?'
             ans=quickui.question(message=msg)
             if ans == -8:
	        removeFile(fin=out['restartout'],zip_opt=out['zip_opt'])
                state = quickui.runWithProgressDialog(parent, "Combine Restart", executeCmbRestart, pulse=False,output=out)

		if not state or not checkFile(out=out,key='restartout'):
                   os.chdir(out['cexepath'])
	           quickui.error(message='Unable to combine restart files.')
                #elif int(out['zip_opt']):
                #   quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key='restartout',output=out)

             else:
	        out['sol_flag']='1'
		if int(out['zip_opt']) and not out['restartout'].endswith('.gz'):
		   out['restartout']=out['restartout']+'.gz'
          else:
             state = quickui.runWithProgressDialog(parent, "Combine Restart", executeCmbRestart, pulse=False,output=out)

	     if not state or not checkFile(out=out,key='restartout'):
                os.chdir(out['cexepath'])
	        quickui.error(message='Unable to combine restart files.')
             #elif int(out['zip_opt']):
             #   quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key='restartout',output=out)
       else: 
          out['sol_flag']='0'
	  quickui.error(message='Problem with number of restart files and subdomain files. Unable to combine restart files.')
    else:
       out['sol_flag']='0'

    if not os.path.exists(out['voldir']):
       os.mkdir(out['voldir'])

    rb=quickui.createWidget(type="RadioButton", quickid="radio1",description="Select output type",options={0:"VTK Format",1:"CGNS Format"},value=0)
    v = quickui.showDialog(rb, parent=tool.getToolWindow())

    if v==None:
       os.chdir(out['cexepath'])
       return

    os.chdir(out['voldir'])

    if rb.value == 0:   

       if checkFile(out=out,key='vtkout'):

          msg=out['vtkout']+'\nis already available. Do you want to overwright?'
          ans=quickui.question(message=msg)

          if ans == -8:
                removeFile(fin=out['vtkout'],zip_opt=out['zip_opt'])
          else:
             if int(out['zip_opt']) and not out['vtkout'].endswith('.gz'):
	        out['vtkout']=out['vtkout']+'.gz'
             os.chdir(out['cexepath'])
             return

       state = quickui.runWithProgressDialog(parent, "VTK Write", executeVTK, pulse=False,output=out)

       if not state or not checkFile(out=out,key='vtkout'):
	  quickui.error(message='Unable to write output in VTK format.')
	  raise IOError

       #if int(out['zip_opt']):
       #   quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key='vtkout',output=out)
    elif rb.value == 1:
       if checkFile(out=out,key='cgnsout'):
          msg=out['cgnsout']+'\nis already available. Do you want to overwright?'
          ans=quickui.question(message=msg)

          if ans == -8:
             removeFile(fin=out['cgnsout'],zip_opt=out['zip_opt'])
          else:
             if int(out['zip_opt']) and not out['cgnsout'].endswith('.gz'):
	        out['cgnsout']=out['cgnsout']+'.gz'
             os.chdir(out['cexepath'])
             return

       state = quickui.runWithProgressDialog(parent, "CGNS Write", executeCGNS, pulse=False,output=out)

       if not state or not checkFile(out=out,key='cgnsout'):
	  quickui.error(message='Unable to write output in cgns format.')
          os.chdir(out['cexepath'])
	  raise IOError

       if int(out['zip_opt']):
          quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key='cgnsout',output=out)

    os.chdir(out['cexepath'])

def runSurface(out={}):

    parent=tool.getToolWindow()

    if not os.path.exists(out['surfacedir']):
       os.mkdir(out['surfacedir'])
    else:
       if checkFile(out=out,key='frc_mnt_file') and checkFile(out=out,key='int_coff_file') and checkFile(out=out,key='pltout'):

          msg="forces_moments_store.dat\n\n"+out['pltout']+"\n\nintegrated_coeffs.dat\n\nare allready available.\nDo you want to overwrite?."
          ans=quickui.question(message=msg)
  
          if ans == -8:
	     removeFile(fin=out['frc_mnt_file'],zip_opt=out['zip_opt'])
	     removeFile(fin=out['int_coff_file'],zip_opt=out['zip_opt'])
	     removeFile(fin=out['pltout'],zip_opt=out['zip_opt'])
	     if out['frc_mnt_file'].endswith('.gz') and out['int_coff_file'].endswith('.gz'):
 		out['frc_mnt_file']=out['frc_mnt_file'][:-3]
 		out['int_coff_file']=out['int_coff_file'][:-3]
	  else:
             return

    os.chdir(out['surfacedir'])

    if os.path.isfile("sfc_yplus.plt"):
       os.remove('sfc_yplus.plt')

    if os.path.isfile("comb_sfc_yplus.plt"):
       os.remove('comb_sfc_yplus.plt')

    optv=quickui.createWidget(type="RadioButton", quickid="radio1",description="Symmetry Option",options={'.false.':"False",'.true.':"True"},value='.false.')
    v = quickui.showDialog(optv, parent=tool.getToolWindow()) 

    if v==None:
       return

    opt_win=os.path.join(const.home,"bin/opt")
  
    p1=subprocess.Popen([opt_win,out['rundir'],optv.value])
    p1.wait()
   
    if not os.path.isfile('freestream.inp') and not os.path.isfile('userchoice.inp') and not os.path.isfile('boundary_information.inp'):
       
       quickui.error(message='freestream.inp, userchoice.inp and boundary_information.inp not found in current directory.')
       raise IOError

    sub=re.compile(('SUBDOMAIN.[0-9]+')) 
    res=re.compile(('restart[0-9]+.dat')) 

    sdirlist=os.listdir(out['subd_dir'])
    rdirlist=os.listdir(out['rundir'])
  
    slist=[]
    rlist=[]

    for item in sdirlist:
        if re.match(sub,item):
           slist.append(item)
    for item in rdirlist:
        if re.match(res,item):
           rlist.append(item)
  
    if len(slist) != out['subd'] or len(slist) != len(rlist):
       quickui.error(message='Invalid number of subdomain files or restart files. Unable to execute.')
       raise IOError

    slist.sort()
    rlist.sort()

    for i in range(len(slist)):
       if int(out['zip_opt']):
          ext=slist[i][-7:-3]
       else:
          ext=slist[i][-4:]
       
       state = quickui.runWithProgressDialog(parent, "POSTPRO", executePLT, pulse=False, subd_file=os.path.join(out['subd_dir'],slist[i]),restart_file=os.path.join(out['rundir'],rlist[i]), output=out)

       if not state or not os.path.isfile('sfc_yplus.plt'):
          quickui.error(message='File sfc_yplus.plt can not be found for process '+str(ext)+'\nGoing to next.')
       else:   	
          p2=subprocess.Popen(['mv','sfc_yplus.plt',os.path.join(out['surfacedir'],'sfc_yplus')+ext+'.plt'])
          p2.wait()
          p2.poll()

    state=quickui.runWithProgressDialog(parent, "Combine PLT", executeCombPLT, pulse=False, output=out)

    if not state or not os.path.isfile(os.path.join(os.getcwd(),'comb_sfc_yplus.plt')):
       quickui.error(message='Unable to combine plt files.')
       """
       mv_cmd=['mv','userchoice.inp','boundary_information.inp','freestream.inp','forces_moments_store.dat','integrated_coeffs.dat',out['surfacedir']]
       p1=subprocess.Popen(mv_cmd)

       p1.wait()
       p1.poll()
       """
       raise IOError

    rm_cmd=['rm','-rf']
 
    sfc=re.compile(('sfc_yplus[0-9]{0,4}\.plt')) 

    sdirlist=os.listdir(out['surfacedir'])

    cmb_plt=[]

    for item in sdirlist:
       if re.match(sfc,item):
	  cmb_plt.append(os.path.join(out['surfacedir'],item))
    cmb_plt.sort()

    for item in cmb_plt:
       rm_cmd.append(item)

    p1=subprocess.Popen(rm_cmd)

    p1.wait()
    p1.poll()

    state = quickui.runWithProgressDialog(parent, "Remove Duplicate Edges", executeRemove_DupEdge, pulse=False, output=out)

    checkFile(out=out,key='frc_mnt_file')
    checkFile(out=out,key='int_coff_file')

    if not state or not checkFile(out=out,key='pltout'):
       quickui.error(message='File '+out['pltout']+' does not exists. Unable to execute.')
       
       #mv_cmd=['mv','comb_sfc_yplus.plt','userchoice.inp','boundary_information.inp','freestream.inp','forces_moments_store.dat','integrated_coeffs.dat',out['surfacedir']]

       #p1=subprocess.Popen(mv_cmd)

       #p1.wait()
       #p1.poll()
       
       raise IOError
    
    os.remove('comb_sfc_yplus.plt')

       #mv_cmd=['mv','userchoice.inp','boundary_information.inp','freestream.inp','forces_moments_store.dat','integrated_coeffs.dat',out['surfacedir']]

       #p1=subprocess.Popen(mv_cmd)

       #p1.wait()
       #p1.poll()
  
    #if int(out['zip_opt']):
    #   quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key='pltout',output=out)

def checkFile(out={},key=None):
    if os.path.isfile(out[key]) or os.path.isfile(out[key]+'.gz'):
       if int(out['zip_opt']):
	  if preprocess.istext(out[key]):
             parent=tool.getToolWindow()
	     quickui.runWithProgressDialog(parent, "Zipping", preprocess.zip_File, pulse=True,key=key,output=out)
	     return True
	  elif not out[key].endswith('.gz'):
	     out[key]=out[key]+'.gz'
             return True
	  else:
	     return True
       else:
          return True
    else:
       return False
      
def executeRemove_DupEdge(output=None,task=None):

    rmv_cmd=[os.path.join(const.home,"bin/remove_dup_edges"),'comb_sfc_yplus.plt',output['pltout']]

    pipe1=subprocess.PIPE 
    p1=subprocess.Popen(rmv_cmd,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    preprocess.progressUpdate(p=p1,task=task)

    p1.wait()
    p1.poll()


def executeCombPLT(output={},task=None):
    
    sfc=re.compile(('.*\.plt')) 

    sdirlist=os.listdir(output['surfacedir'])

    cmb_plt=[]
    cmb_plt_cmd=[]

    for item in sdirlist:
       if re.match(sfc,item):
	  cmb_plt.append(os.path.join(output['surfacedir'],item))

    cmb_plt.sort()

    cmb_plt_cmd.append(os.path.join(const.home,'bin/combine_plt'))


    for item in cmb_plt:
       cmb_plt_cmd.append(item)

    pipe1=subprocess.PIPE 
    p1=subprocess.Popen(cmb_plt_cmd,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    preprocess.progressUpdate(p=p1,task=task)

    p1.wait()
    p1.poll()

def executePLT(subd_file=None, restart_file=None,output={},task=None):
    cmd=[]
    [cmd.append(item) for item in output['cmd']]
    cmd.append(subd_file)
    cmd.append(restart_file)
   
    pipe1=subprocess.PIPE
    p1=subprocess.Popen(cmd,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    postproExe=os.path.join(const.home,'bin/postpro')

    pipe2=subprocess.PIPE
    p2=subprocess.Popen(postproExe,stdin=p1.stdout,stdout=pipe2,stderr=pipe2)

    preprocess.progressUpdate(p=p2,task=task)


    p1.poll()
    p2.wait()
    p2.poll()

def executeCmbRestart(output={},task=None):

    restartOut=output['restartout']

    if not os.path.exists(output['subd_dir']):
	  output['sol_flag']='1'
          return 

    subds_cell_file=os.path.join(output['subd_dir'],'subd_cells.dat')

    if output['zip_opt']:
       subds_cell_file=subds_cell_file+'.gz'

    if not os.path.isfile(subds_cell_file):
       output['sol_flag']='0'
       return


    def writeTempfile(out):
	file=open('combine_restarts_nb.inp','w')

	file.write(out['flow_opt']+'\n')
	file.write(out['rundir']+'\n')
	file.write(subds_cell_file+'\n')
	file.write(out['restartout'])

	file.close()

    writeTempfile(output)

    cmbR_exe=[os.path.join(const.home,'bin/comb_res')]

    pipe1=subprocess.PIPE
    p1=subprocess.Popen(cmbR_exe,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    preprocess.progressUpdate(p=p1,task=task)
 
    p1.wait()


def executeVTK(output={},task=None):

    list=linecache.getline(os.path.join(output['rundir'],'freestream.inp'),3).rsplit()
    mach_no=list[0]
        
    list=linecache.getline(os.path.join(output['rundir'],'freestream.inp'),4).rsplit()
    temp_ref=list[1]
    mu_ref=list[2]
        
    f=open('VTK_files.inp','w')

    f.write(output['ndims']+'\t'+output['sol_flag']+'\t'+output['min_dist_flag']+'\t'+output['flow_opt']+'\t'+output['solver_opt']+'\n')
    f.write(output['gamma']+'\t'+output['gas_constant']+'\t'+temp_ref+'\t'+mu_ref+'\t'+mach_no+'\n')
    f.write(output['geoout']+'\n')
    f.write(output['restartout']+'\n')
    f.write(output['min_dist_file']+'\n')
    f.write(output['vtkout'])

    f.close()

    vtk_exe=os.path.join(const.home,'bin/vtk_write')

    pipe1=subprocess.PIPE

    p1=subprocess.Popen(vtk_exe,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    preprocess.progressUpdate(p=p1,task=task)

    p1.wait()
    p1.poll()

def executeCGNS(output={},task=None):

    f=open('write_module.inp','w')

    f.write(output['ndims']+'\t'+output['file_type']+'\t')
    if int(output['sol_flag']):
       f.write(output['flow_opt']+'\t'+output['sensor_flag']+'\n')
    else:
       f.write(output['sol_flag']+'\t'+output['sensor_flag']+'\n')
    f.write(output['geoout']+'\n')
    f.write(output['restartout']+'\n')
    f.write('sensor00.out'+'\n')
    f.write(output['cgnsout'])

    f.close()

    cgns_exe=os.path.join(const.home,'bin/cgns_write')

    pipe1=subprocess.PIPE

    p1=subprocess.Popen(cgns_exe,stdin=pipe1,stdout=pipe1,stderr=pipe1)

    preprocess.progressUpdate(p=p1,task=task)

    p1.wait()
    p1.poll()

def removeFile(fin=None,zip_opt=0):
    if zip_opt:
       if not fin.endswith('.gz'):
          os.remove(fin+'.gz')
       else:
          os.remove(fin)
    else:
       os.remove(fin)
