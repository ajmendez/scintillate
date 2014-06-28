import os
import sys
import api
import time
import calendar
import collections
from pprint import pprint
from datetime import datetime

LOCAL_FILENAME = os.path.join(api.DIRECTORY, 'local.tar.gz')
EXTS = ['jpg','jpeg', 'cr2', 'png', 'mov']
DATETIME_TAGS = ['DateTime', 'DateTimeDigitized', 'DateTimeOriginal']
SUBSEC_TAGS = ['SubsecTime', 'SubsecTimeDigitized', 'SubsecTimeOriginal']
import PIL.Image, PIL.ExifTags
def getExif(filename):
    '''Gets the EXIF data from a file'''
    badTags = ['MakerNote', 'UserComment']
    ret = {}
    try:
        image = PIL.Image.open(filename)
        if hasattr(image, '_getexif'):
            exifinfo = image._getexif()
            if exifinfo != None:
                # ret['_filename'] = filename
                for tag, value in exifinfo.items():
                    decoded = PIL.ExifTags.TAGS.get(tag, tag)
                    if decoded not in badTags:
                        ret[decoded] = value
    except IOError as e:
        print('IOERROR ' + filename)
        print(' >> ' + e.message)
    return ret



class Directory(object):
    def __init__(self, exts=EXTS):
        self.exts = EXTS
        self.data = {}
    
    def gettag(self, exif, tag):
        for number,name in PIL.ExifTags.TAGS.iteritems():
            if name == tag:
                return exif[number]
    
    def parsedate(self, datestr):
        if '-' in datestr:
            datestr = datestr.replace('-', ':')
        tmp = datetime.strptime(datestr, '%Y:%m:%d %H:%M:%S')
        return calendar.timegm(tmp.timetuple())
    
    def getdate(self, exif):
        for tag in DATETIME_TAGS:
            try:
                tmp = self.gettag(exif, tag)
                return self.parsedate(tmp)
            except Exception as e:
                pass
        return 0
    
    def getsubsec(self, exif):
        for tag in SUBSEC_TAGS:
            try:
                tmp = self.gettag(exif, tag)
                return float(tmp)/100.0
            except Exception as e:
                pass
        return 0
    
    def exifdate(self, filename):
        ndate = 0
        try:
            image = PIL.Image.open(filename)
            # pprint(getExif(filename))
            if hasattr(image, '_getexif'):
                exif  = image._getexif()
                ndate += self.getdate(exif)
                ndate += self.getsubsec(exif)
            return ndate
        except IOError as e:
            print 'Failed to load: {}'.format(e)
    
    def cdate(self, date):
        if isinstance(date, (int, float)):
            return self.cdate(datetime.fromtimestamp(date))
        elif isinstance(date, str):
            return self.cdate(self.parsedate(date))
        elif isinstance(date, datetime):
            return str(date)
    
    def file(self, filename):
        '''get a filename'''
        out = dict(
            filename = os.path.basename(filename),
               title = os.path.splitext(os.path.basename(filename))[0],
                size = os.path.getsize(filename),
             created = os.path.getctime(filename),
            modified = os.path.getmtime(filename),
                exif = self.exifdate(filename),
        )
        return out
    
    def parse(self, kwargs, directory, files):
        '''Function that parses the files the data structure.'''
        if directory in self.data:
            return
        
        tmp = []
        for file in files:
            fullfile = os.path.join(directory, file)
            ext = os.path.splitext(file)[1].replace('.','')
            if (len(ext) > 0) and (ext in self.exts):
                tmp.append(self.file(fullfile))

        if len(tmp) > 0:
            self.data[directory] = tmp
            print 'Finished: {: 4d} : {}'.format(len(tmp), directory)
            # pprint(tmp)
    
    def walk(self, directory, **kwargs):
        '''Wrapper around the os.path.walk.'''
        directory = os.path.abspath(os.path.expanduser(directory))
        os.path.walk(directory, self.parse, kwargs)





if __name__ == '__main__':
    from pysurvey import util
    util.setup_stop()
    
    
    local = Directory(sys.argv[1])
    local.walk()
    
    # pprint(getExif(os.path.abspath(os.path.expanduser(sys.argv[1]))))