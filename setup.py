#!/usr/bin/env python

from distutils.core import setup

setup(name='HifunGUI',
      version='1.0',
      description='GUI package for HiFUN',
      author='sandi',
      author_email='nikhil.shende@sandi.co.in',
      url='http://www.sandi.co.in',
      packages=['hifun', 'hifun.parsers', 'hifun.project'], 
      package_dir = {'hifun':"src/hifun",'hifun.parsers':"src/hifun/parsers","hifun.project":'src/hifun/project'},
      requires = ['pygtk (>2.0)', 'Quickdesktop (>1.1.2)'],
      license = 'propritory',
      platforms = ['linux']
     )
