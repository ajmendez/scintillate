import os
import sys
import api
import data
import time
import calendar
import collections
from pprint import pprint
from datetime import datetime

LOCAL_FILENAME = os.path.join(data.DIRECTORY, 'local.tar.gz')
EXTS = ['jpg','jpeg', 'cr2', 'png', 'mov']
DATETIME_TAGS = ['EXIF:'+x for x in api.DATETIME_TAGS] + ['Image DateTime']
SUBSEC_TAGS = ['EXIF:'+x for x in api.SUBSEC_TAGS]

try:
    import exifread
    import exiftool
    ET = exiftool.ExifTool() 
    ET.start()
except:
    ET=None

# import PIL.Image, PIL.ExifTags
# def getExif(filename):
#     '''Gets the EXIF data from a file'''
#     badTags = ['MakerNote', 'UserComment']
#     badTags = []
#     ret = {}
#     try:
#         image = PIL.Image.open(filename)
#         if hasattr(image, '_getexif'):
#             exifinfo = image._getexif()
#             if exifinfo != None:
#                 # pprint(exifinfo)
#                 # ret['_filename'] = filename
#                 for tag, value in exifinfo.items():
#                     decoded = PIL.ExifTags.TAGS.get(tag, tag)
#                     if decoded not in badTags:
#                         ret[decoded] = value
#     except IOError as e:
#         print('IOERROR ' + filename)
#         print(' >> ' + e.message)
#     return ret



class Directory(object):
    def __init__(self, exts=EXTS):
        self.exts = EXTS
        self.data = {}
    
    def getexif(self, filename):
        return ET.get_metadata(filename)
        # return exifread.process_file(open(filename, 'rb'))
        # image = PIL.Image.open(filename)
        # # pprint(getExif(filename))
        # if hasattr(image, '_getexif'):
        #     exif  = image._getexif()
        
    def gettag(self, exif, tag):
        return exif[tag]
        # return exif[tag].values
        
        ## crap
        # if tag == 'MakerNote ImageUniqueID':
        #     return list(exif[tag].values)
        # else:
        #     return str(exif[tag])
        ## old
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
        tags = ['exif']
        tmp = self.gettags(exif, DATETIME_TAGS, self.parsedate)
        return tmp if tmp else 0
    
    def getsubsec(self, exif):
        fcn = lambda x: float(x)/100.0
        tmp = self.gettags(exif, SUBSEC_TAGS, fcn)
        return tmp if tmp else 0
    
    def exiftime(self, exif):
        ndate = 0.0
        try:
            ndate += self.getdate(exif)
            ndate += self.getsubsec(exif)
            return ndate
        except IOError as e:
            print 'Failed to load: {}'.format(e)
        return ndate
    
    def powershotserial(self, serial, cam=False):
        if isinstance(serial, (str,unicode)) and len(serial) == 32:
            if cam:
                return serial[12:]
            else:
                return serial[:12]
        return serial
    
    def camserial(self, exif):
        # tags = ['MakerNote SerialNumber', 'MakerNote InternalSerialNumber ']
        tags = ['MakerNotes:SerialNumber', 'MakerNotes:InternalSerialNumber',
                'MakerNotes:ImageUniqueID']
        fcn = lambda x: self.powershotserial(x, True)
        tmp = self.gettags(exif, tags, fcn)
        return tmp if tmp else 0
    
    def cammodel(self, exif):
        # tags = ['Image Model']
        tags = ['EXIF:Model', 'MakerNotes:CanonImageType']
        fcn = lambda x: x
        tmp = self.gettags(exif, tags, fcn)
        return tmp if tmp else 0
    
    def imgserial(self, exif):
        # tags = ['MakerNote ImageUniqueID']
        tags = ['MakerNotes:ImageUniqueID']
        fcn = lambda x: self.powershotserial(x, False)
        # fcn = lambda x: x if isinstance(x,str) else ''.join(hex(c)[2:] for c in x)
        # fcn = lambda x: ''.join(hex(c)[2:] for c in x)
        tmp = self.gettags(exif, tags, fcn)
        return tmp if tmp else 0
    
    def imgnumber(self, exif):
        tags = ['MakerNotes:FileIndex', 'MakerNotes:FileNumber']
        tags2 = ['MakerNotes:DirectoryIndex']
        fcn = lambda x: x
        tmp = self.gettags(exif, tags, fcn)
        tmp2 = self.gettags(exif, tags2, fcn)
        if tmp2 is None:
            return tmp if tmp else 0
        return '{}-{}'.format(tmp2,tmp) if tmp else 0

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
            exiftime = self.exiftime(exif),
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
    
    
    
    ## Walk Tests
    # local = Directory()
    # local.walk(sys.argv[1])
    # pprint(local.data)
    
    ## File Tests
    local = Directory()
    pprint(local.getexif(sys.argv[1]))
    pprint(local.file(sys.argv[1]))
    
    ## Exif tests
    filename = '/Volumes/Pictures/Camera_2014.03/03.13/100CANON/IMG_0256.JPG'
    # pprint(getExif(filename))
    
