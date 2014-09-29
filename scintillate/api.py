# scintilate api.py
# improved version from pymendez
import os
import sys
import pwd
import grp
import copy
import json
import time
import tarfile
import calendar
import StringIO
import flickrapi
from pprint import pprint
from collections import deque
from datetime import datetime



NAPI = 2500 # lets start off slow
NTIME = 3600

DATETIME_TAGS = ['CreateDate', 'DateTime', 'DateTimeDigitized', 'DateTimeOriginal']
SUBSEC_TAGS = ['SubSecTime', 'SubSecTimeDigitized', 'SubSecTimeOriginal']
# SERIAL_TAGS = ['']

try:
    from pymendez import auth
    CREDENTIALS = auth('flickr',['key', 'secret', 'username', 'token'])
except Exception as e:
    print e
    CREDENTIALS = None


import xml.etree
def nprint(item, **kwargs):
    '''A simple helper function do print out some things'''
    if isinstance(item, xml.etree.ElementTree.Element):
        xml.etree.ElementTree.dump(item)
    elif isinstance(item,str) and 'jsonFlickrApi' in item:
        pprint(_json(item), **kwargs)
    else:
        pprint(item, **kwargs)




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
                    # doprint = True
                    time.sleep(0.5)
                    now = calendar.timegm(time.gmtime())
            
            # sleep to spread out the load
            time.sleep(float(n)/timescale)
            # keep track of when things were run
            calls.append(calendar.timegm(time.gmtime()))
            return func(*args, **kwargs)
        return ratelimiter
    return decorate


@ratelimit(10, 5)
def testrate(i):
    print i, datetime.now()


def convert_time(timestr):
    return datetime.fromtimestamp(float(timestr))


def _json(item):
    data = json.loads(item[14:-1])# strip out the container function
    if data['stat'] == 'fail':
        raise IOError('API Error: {}'.format(data))
    return data


class Upload(object):
    def __init__(self, credentials=CREDENTIALS, fmt='etree', cache=True):
        '''Credentials is a list/tuple of key, secret, username, token
        fmt is one of ['etree','xmlnode'] ? json breaks walk
        '''
        self.flickr = flickrapi.FlickrAPI(*credentials, format=fmt, cache=cache)
        if cache:
            c = flickrapi.SimpleCache(timeout=30000, max_entries=2000)
            self.flickr.cache = c # mainly for length reasons
    def push(self, filename, title, description, tags, ispublic=False):
        def callback(progress, done):
            if done:
                print 'Finished!'
            else:
                print '%s%% '%progress
        tmp = dict(
            filename=filename,
            title=title,
            description=description,
            tags=' '.join(['"%s"'%x for x in tags]) + ' scintillate',
            is_public="1" if ispublic else "0",
        )
        self.flickr.upload(**tmp)
    

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
        '''Get a dictionary of the exif data.'''
        tmp = dict(photo_id=ident, format='json')
        tmp.update(kwargs)
        self.check_rate()
        # return self._exif(self.flickr.photos_getExif(**tmp))
        return _json(self.flickr.photos_getExif(**tmp))['photo']['exif']
    
    def getexiftag(self, exif, tag):
        for item in exif:
            if item['tag'].lower() == tag.lower():
                return item['raw']['_content']
    
    def _silenttags(self, exif, tags, fcn):
        '''Searches the exif for one tag and then applies a function to it.
        returns 0 if nothing found.'''
        for tag in tags:
            try:
                return fcn(self.getexiftag(exif,tag))
            except Exception as e:
                pass
        return 0
    
    def parseexifdate(self, datestr):
        '''Parse the date from the exif string'''
        if '-' in datestr:
            datestr = datestr.replace('-', ':')
        tmp = datetime.strptime(datestr, '%Y:%m:%d %H:%M:%S')
        return calendar.timegm(tmp.timetuple())
    
    def getexifdate(self, exif):
        return self._silenttags(exif, DATETIME_TAGS, self.parseexifdate)
    
    def getexifsubsec(self, exif):
        '''Get the subsec(ond) part of the exif data. This makes the 
        exif data more uniq.'''
        fcn = lambda x: float(x)/100.0
        return self._silenttags(exif, SUBSEC_TAGS, fcn)
    
    def getexiftime(self, exif, **kwargs):
        ndate = 0
        try:
            # if exif is None:
            #     exif = self.getexif(ident, **kwargs)
            ndate += self.getexifdate(exif)
            ndate += self.getexifsubsec(exif)
            return ndate
        except IOError as e:
            print 'Failed to load: {}'.format(e)
    
    def genexifitems(self, exif):
        fcn = lambda x: x
        items = dict(
            cammodel = ['CanonModelID', 'Model'],
            camlens = ['LensType'],
            camserial = ['SerialNumber','InternalSerialNumber'],
            camexposure = ['ExposureTime'],
            camaperature = ['FNumber'],
            camiso = ['ISO', 'CameraISO'],
            camfocal = ['FocalLength'],
            camev = ['MeasuredEV'],
            imgserial = ['ImageUniqueID'],
            temperature = ['CameraTemperature'],
            imgnumber = ['FileNumber','FileIndex'],
            imgdir = ['DirectoryIndex']
        )
        for item,tags in items.iteritems():
            yield item, self._silenttags(exif, tags, fcn)
    
    def cleanexif(self, exif):
        '''Parse out some of the tags'''
        BAD_LABEL = ['User Def', 'AF', 'Contrast','Saturation','Sharpness',
                     'Interop','LCDDisplay', 'Set Button', 'Effect',
                     'Thumbnail']
        BAD_TAG = ['AELock', 'WB_', 'WBS', 'WBB', 'Effect', 'RGGB',
                   'ColorTone','Sensor','Resolution',
                   'ColorTemp', 'BlackMask', 'Crop', 'DustRemovalData',
                   'FlashBits','ZoomTargetWidth','ZoomSourceWidth',
                   'BaseISO','ManualFlashOutput','OriginalDecisionDataOffset',
                   'VRDOffset','FlashMeteringMode', 'CanonFirmwareVersion',
                   'ComponentsConfiguration', 'YCbCrPositioning','ExifVersion',
                   'ColorDataVersion','ToneCurve','WhiteBalanceRed','WhiteBalanceBlue']
        BAD_SPACE = ['CanonCustom']
        BAD = [[b.lower() for b in bad] 
               for bad in [BAD_LABEL,BAD_TAG,BAD_SPACE]]
        
        # out = copy.copy(exif)
        out = []
        remove_index = []
        for i, item in enumerate(exif):
            tmp = [item[x].lower() for x in ['label','tag','tagspace']]
            isbad = any(b in it 
                        for it,bd in zip(tmp,BAD) 
                            for b in bd)
            if not isbad:
                out.append(map(str, [item[x]['_content'] if x == 'raw' else item[x]
                                     for x in ['tag','raw','tagspace', 'label']]))
        return out
    
    
    
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






# debug
if __name__ == '__main__':
    from pysurvey import util
    util.setup_stop()
    
    api = Flickr()
    # for photo in api.genphotos():
    #     print photo
    #     break
    # print api.getinfo('8409361473')
    nprint(api.getexif('8409361473'))
    
    # nprint(api.getstats(datetime(2014,6,5)))
    
    # check rate limit in api
    # for x in range(100):
    #     print api.A()
    #     print api.B()
    
    # rate limit test
    # for i in range(1,100):
    #     testrate(i)
    
    
    
