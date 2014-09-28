scintillate
===========

Scintillation maps flickr.

flickrapi exiftool exifread beautifulsoup4 requests pymendez
pip install git+https://github.com/smarnach/pyexiftool.git
sudo apt-get install libimage-exiftool-perl


* bin/flickr_files    : Searches through a directory to find photos to get
                         their modification date, EXIF date.
* bin/flickr_stats    : Grabs the stat information from the flickr servers. 
* bin/flickr_photos   : Grabs the metadata for each photo on the flickr servers.
* bin/flickr_apistats : Archive the api usage for future plots.


TODO:
* bin/flickr_dups : determine duplicates from website or files.
* bin/flickr_backup : Backup of archived files to flickr without dups.
* Automate graph making

