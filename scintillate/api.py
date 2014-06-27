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
import flickrapi
from pprint import pprint
from collections import deque
from datetime import datetime

DIRECTORY = os.path.expanduser('~/data/flickr/')
STATS_FILENAME = os.path.join(DIRECTORY, 'stats2.json')
PHOTO_FILENAME = os.path.join(DIRECTORY, 'photos.tar.gz')

NAPI = 1800 # lets start off slow
NTIME = 3600

try:
    from pymendez import auth
    CREDENTIALS = auth('flickr',['key', 'secret', 'username', 'token'])
except Exception as e:
    print e
    CREDENTIALS = None


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
  
  def save(self):
    '''Save the file as a json.dump or a tarfile depending
    on the file ending'''
    if '.tar.gz' in self.filename:
      self.savegz()
    else:
      json.dump(self.data, open(self.filename,'w'), indent=2)
  
  def load(self):
    '''Load the file as a json file or a tar file.'''
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





def ratelimit(n=3600, timescale=3600):
    '''decorator that limits the function to be called N times per timescale [seconds].'''
    def decorate(func):
        calls = []#deque(maxlen=n) # could probably use a list
        def ratelimiter(*args, **kwargs):
            # Ensure that we do not go above the averate rate
            # now = datetime.now()
            now = calendar.timegm(time.gmtime()) # integer seconds are nice
            doprint = False
            while len(calls) >= n:
                # block until we can pop
                if (now - calls[0]) > timescale:
                    calls.pop(0)
                    
                    break
                else:
                    sys.stdout.write('.')
                    sys.stdout.flush()
                    doprint = True
                    # print 'Holding until rolling average [n={},t={}]'.format(n,timescale)
                    time.sleep(0.5)
                    now = calendar.timegm(time.gmtime())
            if doprint:
                sys.stdout.write('\n')
            
            # Spread out calls into some nice range
            calls.append(now)
            time.sleep(float(n)/timescale) # TODO uncomment after debug
            # sys.stdout.write('r:{}'.format(len(calls)))
            # sys.stdout.flush()
            return func(*args, **kwargs)
        return ratelimiter
    return decorate


@ratelimit(10, 5)
def testrate(i):
    print i, datetime.now()


def convert_time(timestr):
    return datetime.fromtimestamp(int(timestr))


def _json(item):
    return json.loads(item[14:-1])# strip out the container function


class Flickr(object):
    def __init__(self, credentials=CREDENTIALS, fmt='etree', cache=True):
        '''Credentials is a list/tuple of key, secret, username, token
        fmt is one of ['etree','xmlnode'] ? json breaks walk
        '''
        self.flickr = flickrapi.FlickrAPI(*credentials, format=fmt, cache=cache)
        if cache:
            c = flickrapi.SimpleCache(timeout=30000, max_entries=2000)
            self.flickr.cache = c # mainly for length reasons
    
    @ratelimit(NAPI, NTIME)
    def check_rate(self):
        '''run before each flickr call'''
    
    def getinfo(self, ident, **kwargs):
        '''Get the information'''
        tmp = dict(photo_id=ident, format='json')
        tmp.update(kwargs)
        self.check_rate()
        # return self._info(self.flickr.photos_getInfo(**tmp))
        return _json(self.flickr.photos_getInfo(**tmp))['photo']

    def getexif(self, ident, **kwargs):
        tmp = dict(photo_id=ident, format='json')
        tmp.update(kwargs)
        self.check_rate()
        # return self._exif(self.flickr.photos_getExif(**tmp))
        return _json(self.flickr.photos_getExif(**tmp))['photo']
    
    def getstats(self, date):
        '''Generator: gets the stats from a date
        date is a datetime object'''
        tmp = dict(date=date.strftime('%Y-%m-%d'),
                   format='json',
                   per_page=500)
        out = {'date':tmp['date']}
        
        self.check_rate()
        out['views'] = _json(self.flickr.stats_getTotalViews(**tmp))['stats']
        for k,v in out['views'].iteritems():
            out['views'][k] = int(v['views'])
        
        self.check_rate()
        out['domainlist'] = []
        t = _json(self.flickr.stats_getPhotostreamDomains(**tmp))['domains']
        if int(t['total']) > 0:
            t = t['domain']
            for domain in t:
                t2 = _json(self.flickr.stats_getPhotostreamReferrers(domain=domain['name'], **tmp))
                domain['referrer'] = t2['domain']['referrer']
                out['domainlist'].append(domain)
        
        self.check_rate()
        out['photos'] = _json(self.flickr.stats_getPopularPhotos(**tmp))
        
        return out
    
    def genphotos(self, **kwargs):
        '''Walk my photos'''
        tmp = dict(
            user_id = 'me', # me or flickr ID
            media = 'all',  # photos / videos / all
            per_page = 500, # < 500
            # format = 'etree', # stupid
        )
        tmp.update(kwargs)
        for i,photo in enumerate(self.flickr.walk(**tmp)):
            yield self._photo(photo)
            if i%tmp['per_page'] == 0:
                self.check_rate()
        
    
    
    def _photo(self, photo):
        '''convert an etree photo to a dictionary:
        now: id, title, public
        can: farm, isfamily, isfamily, isfriend, owner, secret, server'''
        out = dict(
            id = photo.get('id'),
            title = photo.get('title'),
            public = photo.get('ispublic') == '0',
        )
        return out
    
    # def _info(self, info):
    #     ''' Parse out the info data
    #     now: id, media, rotation, uploaded, views, title, description,
    #          lastupdate, posted, taken, ispublic
    #     todo: notes, tags, people, comments
    #     '''
    #     photo = info.find('photo')
    #     out = dict(
    #         id = photo.get('id'), # copy
    #         media = photo.get('media'),
    #         rotation = photo.get('rotation'),
    #         uploaded = photo.get('dateuploaded'),
    #         views = photo.get('views'),
    #         title = photo.find('title').text,
    #         description = photo.find('description').text,
    #         lastupdate = photo.find('dates').get('lastupdate', ''),
    #         posted = photo.find('dates').get('posted', ''),
    #         taken = photo.find('dates').get('taken', ''),
    #         ispublic = photo.find('visibility').get('ispublic') == 1,
    #     )
    #     return out
    #
    # def _exif(self, exif):
    #     '''Get _ALL_ of the exif data.  This is quite verbose! should make
    #     this into some sort of DB since many of the values are going to be
    #     the same.
    #     '''
    #     photo = exif.find('photo')
    #     out = {'id':photo.get('id')}
    #     for item in photo.findall('exif'):
    #         # there are some tag collisions in this technique -- but it is ok
    #         out[item.get('tag')] = dict(
    #             label = item.get('label'),
    #             tagspace = item.get('tagspace'),
    #             raw = item.find('raw').text,
    #         )
    #         clean = item.find('clean')
    #         if clean is not None:
    #             out[item.get('tag')]['clean'] = clean.text
    #     return out




import xml.etree
def nprint(item, **kwargs):
    '''A simple helper function do print out some things'''
    if isinstance(item, xml.etree.ElementTree.Element):
        xml.etree.ElementTree.dump(item)
    elif isinstance(item,str) and 'jsonFlickrApi' in item:
        pprint(_json(item), **kwargs)
    else:
        pprint(item, **kwargs)


# debug
if __name__ == '__main__':
    from pysurvey import util
    util.setup_stop()
    
    api = Flickr()
    # for photo in api.genphotos():
    #     print photo
    #     break
    # print api.getinfo('8409361473')
    # nprint(api.getexif('8409361473'))
    
    nprint(api.getstats(datetime(2014,6,5)))
    
    # check rate limit in api
    # for x in range(100):
    #     print api.A()
    #     print api.B()
    
    # rate limit test
    # for i in range(1,100):
    #     testrate(i)
    
    
    
