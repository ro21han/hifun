from quickdesktop import quickui
from quickdesktop import projectutils
from quickdesktop import tool
from quickdesktop import const
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



def SolverRun():
    p = projectutils.getActiveProject()

    if not p.runs:
        quickui.error("You should create a Run before doing this operation.")
        return
    SolverExecute(p=p,run=p.activerun)

class SolverExecute:
    def __init__(self,p=None,run=None):
	
	self.project=p or projectutils.getActiveProject()
	self.runname=run or self.project[self.runname]['name']
	self.no_of_subd=self.project[self.runname]['subdomians']
	self.runpath=os.path.join(self.project[self.runname]['path'])
	self.rep=p.getRepository()
	self.machfile=p.getMachinsFile()
	self.flags=p.getSolverFlags()

	self.subd_dir=os.path.join(self.project['projecdir'],'Subds_')+str(self.no_of_subd)
	self.subd_dir_link=os.path.join(self.project['projecdir'],'Flowsolver_input/Subdomains')

        if not os.path.isfile(os.path.join(self.runpath,'Flowsolver_input/userchoice.inp')) or \ 
	   not os.path.isfile(os.path.join(self.runpath,'Flowsolver_input/freestream.inp')) or \
	   not os.path.isfile(os.path.join(self.runpath,'Flowsolver_input/run_option.inp')) or \
	   not os.path.isfile(os.path.join(self.runpath,'Flowsolver_input/boundary_information.inp')) or \
	   not os.path.isfile(os.path.join(self.runpath,'Flowsolver_input/lift_drag_contrib.inp')):
	   quickui.error(message='Required Flow solver input files are not available for current run.\nPlease check.')
	   raise IOError('Required Flow solver input files are not available for current run. Please check.')

        if not os.path.isfile(self.machfile):
	   quickui.error(message='Required Machine file is not found. Unable to execute.')
	   raise IOError('Required Machine file is not found. Unable to execute.')


        if os.path.exists(self.subd_dir):
	   if not os.path.islink(self.subd_dir_link) or not os.path.realpath(self.subd_dir_link)==self.subd_dir:
	      quickui.error(message='Invalid Subdomain directory.\nPlease check.')
	      raise IOError('Invalid Subdomain directory.\nPlease check.')
	else:
	   quickui.error(message='Unable to locate subdomain directory.\nPlease check.')
	   raise IOError('Unable to subdomain directory.\nPlease check.')

	extra_lib_path=os.getenv('EXTRA_LIB')
	flist=os.listdir(extra_lib_path)
	pt=re.compile(('openmpi.'))
	for item in flist:
	    if re.match(pt,item):
	       openmpi_dir=os.path.join(extra_lib_path,item)
	       break
        if not os.path.exists(openmpi_dir):
	   quickui.error(message='Unable to locate openmpi.\nPlease check.')
	   raise IOError('Unable to locate openmpi. Please check.')

	mpiexe=os.path.join(openmpi_dir,'bin/mpirun')

	if not os.path.isfile(mpiexe):
           quickui.error(message='Unable to locate mpirun command.\nPlease check.')
           raise IOError('Unable to locate mpirun command. Please check.')

	rans_exe=os.path.join(const.home,'bin/rans_3d_tempfac_mod2_WF')

	solvercmd=[mpiexe,'-machinefile',self.machfile,'-np',str(self.no_of_subd),rans_exe]
	if self.flags:
	   solvercmd.insert(1,self.flags)

	p1=subprocess.Popen(solvercmd)

	p1.wait()
