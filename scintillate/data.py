# scintilate api.py
# improved version from pymendez
import os
import sys
import pwd
import grp
import json
import time
import tarfile
import calendar
import StringIO
import subprocess


DIRECTORY = os.path.expanduser('~/data/flickr/')
STATS_FILENAME = os.path.join(DIRECTORY, 'stats2.json')
APISTATS_FILENAME = os.path.join(DIRECTORY, 'apistats.json')
PHOTO_FILENAME = os.path.join(DIRECTORY, 'photos.tar.gz')
EXIF_FILENAME = os.path.join(DIRECTORY, 'exif.tar.gz')




# from forage -- should be moved to mUtil
class Data(object):
  def __init__(self, filename=PHOTO_FILENAME, fcn=list):
    '''Setup a Data object that is saved to a filename.
    fcn is the base datatype that starts the object if one does not exist.
    filename should be xxx.json, or xxx.tar.gz 
    '''
    self.filename = filename
    self.fcn = fcn
    
  def __enter__(self, *args, **kwargs):
    '''With constructor -- asks user for confirmation if file
    does not exist -- I think this is a good thing.'''
    try:
      self.data = self.load()
    except Exception as e:
      self.data = self.fcn()
      print ' Failed to load: {}'.format(self.filename)
      print e
      isok = raw_input('Are you ok with this? [yes/no]: ')
      if 'y' not in isok.lower():
        raise
      # ensure that the directory exists
      dirname = os.path.dirname(self.filename)
      if not os.path.exists(dirname):
        os.makedirs(dirname)
    return self
  
  def __exit__(self, *args, **kwargs):
    '''save the file on exit'''
    self.save()
  
  def __len__(self):
    '''len() of object'''
    return len(self.data)
  
  def __iter__(self):
      return iter(self.data)
  
  def __getitem__(self, key):
      return self.data[key]
  
  def __setitem__(self, key, value):
      self.data[key] = value
  
  def backup(self):
      '''Backup the original file before saving'''
      backupfile = os.path.dirname(self.filename) + 'backup_'+os.path.basename(self.filename)
      print 'Backup: {}'.format(backupfile)
      print subprocess.call(['rsync','-a',self.filename, backupfile])
  
  def save(self):
    '''Save the file as a json.dump or a tarfile depending
    on the file ending'''
    print 'Saving: {}'.format(self.filename)
    self.backup()
    if '.tar.gz' in self.filename:
      self.savegz()
    else:
      json.dump(self.data, open(self.filename,'w'), indent=2)
  
  def load(self):
    '''Load the file as a json file or a tar file.'''
    print 'Loading: {}'.format(self.filename)
    if '.tar.gz' in self.filename:
      return self.loadgz()
    else:
      return json.load(open(self.filename))
  
  def getname(self):
    '''get a nice file name to put within the tar file.'''
    return os.path.basename(self.filename).replace('.tar.gz','.json')
  
  def savegz(self):
    '''save the file within a gziped tar file'''
    with tarfile.open(self.filename, 'w:gz') as tar:
      fileobj = StringIO.StringIO()
      json.dump(self.data, fileobj, indent=2)
      fileobj.seek(0)
      tarinfo = tarfile.TarInfo(self.getname())
      tarinfo.size = fileobj.len
      tarinfo.mtime = calendar.timegm(time.gmtime())
      tarinfo.mode = int('0644', 8) # convert to octal
      tarinfo.uid = os.getuid()
      tarinfo.uname = pwd.getpwuid(tarinfo.uid)[0]
      tarinfo.gid = os.getgid()
      tarinfo.gname = grp.getgrgid(tarinfo.gid)[0]
      tar.addfile(tarinfo, fileobj)
  
  def loadgz(self):
    '''Load a json object out of a tar.'''
    with tarfile.open(self.filename, 'r:gz') as tar:
      return json.load(tar.extractfile(tar.getmember(self.getname())))
  
  def append(self, item):
    '''Append to the file'''
    self.data.append(item)
  
  def get(self, key):
    return [item[key] for item in self.data]
  
  def update(self, up):
      self.data.update(up)

