import os
import sys
import api
import data
import time
import calendar
import exifread
import collections
from pprint import pprint
from datetime import datetime

LOCAL_FILENAME = os.path.join(data.DIRECTORY, 'local.tar.gz')
EXTS = ['jpg','jpeg', 'cr2', 'png', 'mov']
DATETIME_TAGS = ['EXIF'+x for x in api.DATETIME_TAGS] + ['Image DateTime']
SUBSEC_TAGS = ['EXIF'+x for x in api.SUBSEC_TAGS]

import PIL.Image, PIL.ExifTags
def getExif(filename):
    '''Gets the EXIF data from a file'''
    badTags = ['MakerNote', 'UserComment']
    badTags = []
    ret = {}
    try:
        image = PIL.Image.open(filename)
        if hasattr(image, '_getexif'):
            exifinfo = image._getexif()
            if exifinfo != None:
                # pprint(exifinfo)
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
        # if tag == 'MakerNote ImageUniqueID':
        #     return list(exif[tag].values)
        # else:
        #     return str(exif[tag])
        return exif[tag].values
        # for number,name in PIL.ExifTags.TAGS.iteritems():
        #     if name == tag:
        #         return exif[number]

    def gettags(self, exif, tags, fcn):
        for tag in tags:
            try:
                tmp = self.gettag(exif, tag)
                return fcn(tmp)
            except:
                pass
    
    def parsedate(self, datestr):
        if '-' in datestr:
            datestr = datestr.replace('-', ':')
        tmp = datetime.strptime(datestr, '%Y:%m:%d %H:%M:%S')
        return calendar.timegm(tmp.timetuple())
    
    
    def getdate(self, exif):
        tags = ['exif ']
        tmp = self.gettags(exif, DATETIME_TAGS, self.parsedate)
        return tmp if tmp else 0
    
    def getsubsec(self, exif):
        fcn = lambda x: float(x)/100.0
        tmp = self.gettags(exif, SUBSEC_TAGS, fcn)
        return tmp if tmp else 0
    
    def exifdate(self, exif):
        ndate = 0.0
        try:
            ndate += self.getdate(exif)
            ndate += self.getsubsec(exif)
            return ndate
        except IOError as e:
            print 'Failed to load: {}'.format(e)
        return ndate
    
    def camserial(self, exif):
        fcn = lambda x: x[0]
        tmp = self.gettags(exif, ['MakerNote SerialNumber', 'MakerNote InternalSerialNumber '], fcn)
        return tmp if tmp else 0
    
    def cammodel(self, exif):
        fcn = lambda x: x
        tmp = self.gettags(exif, ['Image Model'], fcn)
        return tmp if tmp else 0
    
    def imgserial(self, exif):
        fcn = lambda x: x if isinstance(x,str) else ''.join(hex(c)[2:] for c in x)
        # fcn = lambda x: ''.join(hex(c)[2:] for c in x)
        tmp = self.gettags(exif, ['MakerNote ImageUniqueID'], fcn)
        return tmp if tmp else 0
    
    def imgnumber(self, exif):
        fcn = lambda x: x[0]
        tmp = self.gettags(exif, ['MakerNote ImageNumber'], fcn)
        return tmp if tmp else 0
    
    def getexif(self, filename):
        return exifread.process_file(open(filename, 'rb'))
        # image = PIL.Image.open(filename)
        # # pprint(getExif(filename))
        # if hasattr(image, '_getexif'):
        #     exif  = image._getexif()
    
    def cdate(self, date):
        if isinstance(date, (int, float)):
            return self.cdate(datetime.fromtimestamp(date))
        elif isinstance(date, str):
            return self.cdate(self.parsedate(date))
        elif isinstance(date, datetime):
            return str(date)
    
    def file(self, filename):
        '''get a filename'''
        exif = self.getexif(filename)
        out = dict(
            filename = os.path.basename(filename),
               title = os.path.splitext(os.path.basename(filename))[0],
                size = os.path.getsize(filename),
             created = os.path.getctime(filename),
            modified = os.path.getmtime(filename),
                exif = self.exifdate(exif),
           camserial = self.camserial(exif),
           imgserial = self.imgserial(exif),
           imgnumber = self.imgnumber(exif),
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
            if (len(ext) > 0) and (ext.lower() in self.exts):
                tmp.append(self.file(fullfile))
            sys.stdout.write('.')
            sys.stdout.flush()
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
    
    
    local = Directory()
    local.walk(sys.argv[1])
    pprint(local.data)
    
    # pprint(getExif('/Users/ajmendez/Downloads/Rome to External Disk/IMG_2957.JPG'))
    #[13, 88, 211, 211, 254, 218, 53, 83, 195, 128, 165, 136, 61, 216, 132, 212]
    # [10, 88, 141, 208, 254, 218, 53, 83, 195, 128, 165, 136, 61, 216, 132, 212]
    # [11, 88, 145, 208, 254, 218, 53, 83, 195, 128, 165, 136, 61, 216, 132, 212]
    # [08, 88, 233, 209, 254, 218, 53, 83, 195, 128, 165, 136, 61, 216, 132, 212]
    # [94, 66, 103, 242, 226, 218, 53, 83, 195, 128, 165, 136, 61, 216, 132, 212]
    
    # f = open('/Users/ajmendez/Downloads/Rome to External Disk/IMG_4019.JPG','rb')
    f =open('/Users/ajmendez/Desktop/tmp/IMG_0834.JPG','rb')
    # f = open('/Users/ajmendez/Downloads/Rome to External Disk/IMG_2957.JPG','rb')
    # f = open('/Users/ajmendez/Downloads/Rome to External Disk/IMG_2956.JPG','rb')
    # f = open('/Users/ajmendez/Downloads/_pictures/ChTv638.jpg')
    exif = exifread.process_file(f)
    # pprint(exif)
    # print exif['MakerNote ImageUniqueID']
    # raise ValueError()
    # pprint(getExif(os.path.abspath(os.path.expanduser(sys.argv[1]))))