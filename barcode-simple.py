import argparse
from hashlib import md5
import uuid
import glob
from datetime import datetime
import re
import csv
import os
import platform
#import pickle
#import sqlite3 as lite
from pyzbar.pyzbar import decode
#from PIL import Image
#import cv2
#import features


# File extensions that are scanned and logged
INPUT_FILE_TYPES = ('.jpg', '.jpeg', '.JPG', '.JPEG')
# File type extensions that are logged when filename matches a scanned input file
ARCHIVE_FILE_TYPES = ('.CR2', '.cr2', '.RAW', '.raw')
# Barcode symbologies accepted, others ignored
ACCEPTED_SYMBOLOGIES = ['CODE39']
#TODO add accepted barcode string patterns
FIELD_DELIMITER = ',' # delimiter used in output CSV
PROJECT_IDS = ['TX','ANHC','VDB','TEST', 'TCN-Ferns']

def md5hash(fname):
    # from https://stackoverflow.com/questions/3431825/generating-an-md5-checksum-of-a-file
    # using this approach to ensure larger files can be read into memory
    #hash_md5 = hashlib.md5()
    hash_md5 = md5()
    with open(fname, "rb") as f:
        for chunk in iter(lambda: f.read(4096), b""):
            hash_md5.update(chunk)
    return hash_md5.hexdigest()

def creation_date(path_to_file):
    # From https://stackoverflow.com/a/39501288
    """
    Try to get the date that a file was created, falling back to when it was
    last modified if that isn't possible.
    See http://stackoverflow.com/a/39501288/1709587 for explanation.
    """
    if platform.system() == 'Windows':
        return os.path.getctime(path_to_file)
    else:
        stat = os.stat(path_to_file)
        try:
            return stat.st_birthtime
        except AttributeError:
            # We're probably on Linux. No easy way to get creation dates here,
            # so we'll settle for when its content was last modified.
            return stat.st_mtime

# Attempts to get actual path of files with correct case
def get_actual_filename(name):
    # From https://stackoverflow.com/a/14742779
    dirs = name.split('\\')
    # disk letter
    test_name = [dirs[0].upper()]
    for d in dirs[1:]:
        test_name += ["%s[%s]" % (d[:-1], d[-1])]
    res = glob.glob('\\'.join(test_name))
    if not res:
        #File not found
        return None
    return res[0]

def casedpath(path):
    # from https://stackoverflow.com/a/35229734
    r = glob.glob(re.sub(r'([^:/\\])(?=[/\\]|$)', r'[\1]', path))
    return r and r[0] or path

def log_file_data(batch_id=None, batch_path=None, batch_flags=None, closest_model=None,\
    image_event_id=None, barcodes=None, image_classifications=None, \
    image_path=None, file_uuid=None, derived_from_file=None):
    basename = os.path.basename(image_path)
    file_name, file_extension = os.path.splitext(basename)
    # Get file creation time
    file_creation_time = datetime.fromtimestamp(creation_date(image_path))
    #generate MD5 hash
    file_hash = md5hash(image_path)
    datetime_analyzed = datetime.now()

    # clean up values for writing to SQLite (doesn't like dicts)
    if barcodes:
        barcodes = str(barcodes)
    else:
        barcodes = ''
    if closest_model:
        closest_model = str(closest_model)
    else:
        closest_model = ''

    reportWriter.writerow([\
    batch_id, batch_path, batch_flags, project_id, \
    image_event_id, datetime_analyzed, barcodes, image_classifications, closest_model, \
    image_path, basename, file_name, file_extension, file_creation_time, file_hash, file_uuid, derived_from_file])

# set up argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--source", required=True, \
    help="Path to the directory that contains the images to be analyzed.")
ap.add_argument("-p", "--project", required=True, choices=PROJECT_IDS, \
    help="Project name for filtering in database")
ap.add_argument("-b", "--batch", required=False, \
    help="Flags written to batch_flags")
ap.add_argument("-o", "--output", required=False, \
    help="Path to the directory where log file is written.")
args = vars(ap.parse_args())

# set up database
conn = lite.connect('workflow.db')
cur = conn.cursor()
try:
    cur.execute('''CREATE TABLE images (id INTEGER PRIMARY KEY, \
        batch_id text, batch_path text, batch_flags text, project_id text, \
        image_event_id text, datetime_analyzed text, \
        barcodes text, image_classifications text, closest_model text, \
        image_path text, basename text, file_name text, file_extension text, \
        file_creation_time text, file_hash text, file_uuid text, derived_from_file text)''')
except lite.Error as e:
    print(e)

analysis_start_time = datetime.now()
batch_id = str(uuid.uuid4())
batch_path = os.path.realpath(args["source"])
project_id = args["project"]
# load models from pickle file
if args["models"]:
    print('Loading model histograms.')
    models = pickle.load(open(args["models"], "rb"))

if args["batch"]:
    batch_flags = args["batch"]
    print('Batch flags:', batch_flags)
else:
    batch_flags=None

# Create file for results
log_file_name = analysis_start_time.date().isoformat() + '_' + batch_id + '.csv'
# Test output path
if args["output"] is not None:
    output_directory = os.path.realpath(args["output"])
    print('output_directory:', output_directory)
    #TODO make sure directory exists and is writeable
    log_file_path = os.path.join(output_directory, log_file_name)
    reportFile = open(log_file_path, "w")
else:
    reportFile = open(log_file_name, "w") # will default to write in location where script is executed

reportWriter = csv.writer(reportFile, delimiter=FIELD_DELIMITER, escapechar='#')
# write header
reportWriter.writerow([\
    "batch_id", "batch_path", "batch_flags", "project_id", \
    "image_event_id", "datetime_analyzed", "barcodes", "image_classifications", "closest_model",\
    "image_path", "basename", "file_name", "file_extension", "file_creation_time", "file_hash", "file_uuid", "derived_from_file"])
    #"ImagePath", "DirPath" , "BaseName", "FileName", "FileExtension", "Code", "CodeType" , "Scan time"])

#TODO extract information from directory name (imager, station, etc)
#iterate JPG files in directory passed from args
directory_path = os.path.realpath(args["source"])
files_analyzed = 0
print('Scanning directory:', directory_path)
#TODO change image search to use INPUT_FILE_TYPES
for image_path in sorted(glob.glob(os.path.join(directory_path, '*.JPG')), key=os.path.getmtime): #this file search seems to be case sensitive
    files_analyzed += 1
    scan_start_time = datetime.now()
    image_event_id = str(uuid.uuid4())
    image_classifications = None
    # Gather file data
    #TODO getting basename and file name is done twice, maybe simplify?
    basename = os.path.basename(image_path)
    file_name, file_extension = os.path.splitext(basename)
    # check if a companion archive file exists
    # iterate through potential extensions for archive files
    arch_file_path = None
    for archive_extension in ARCHIVE_FILE_TYPES:
        potential_arch_file_name = file_name + archive_extension
        potential_arch_file_path = os.path.join(directory_path, potential_arch_file_name)
        # test if archive file exists
        # TODO change filename comparison be case-sensitive

        if os.path.exists(potential_arch_file_path):
            arch_file_path = potential_arch_file_path
            #TODO generate hash, uuid, read creation time, etc
            break

    # print filepaths
    print('Image file:', os.path.basename(image_path))
    if arch_file_path is None:
        print('Archive file: NOT FOUND')
    else:
        #print('Archive file:', arch_file_path)
        print('Archive file:', os.path.basename(arch_file_path))
        
    # read barcodes from JPG
    barcodes = decode(Image.open(image_path))
    matching_barcodes = []
    image_classifications = []
    best_match = None
    if barcodes:
        image_classifications.append('barcoded')
        for barcode in barcodes:
            if str(barcode.type) in ACCEPTED_SYMBOLOGIES:
                symbology_type = str(barcode.type)
                data = barcode.data.decode('UTF-8')
                matching_barcodes.append({'type':symbology_type, 'data':data})
                print(symbology_type, data)
    else:
        print('No barcodes found')
        image_classifications.append('folder')
        # compare to folder models
        # save matching models, ranked
        # generate suggested filename? Or should that be done in rename script?
        if args["models"] is None:
            print('No model file provided. No histogram analysis done.')
        else:
            image = cv2.imread(image_path)
            histogram = features.describe(image)
            best_match = closest_histogram(image_histogram=histogram)
            [(model_name, model_similarity)] = best_match.items()
            if 'specimen' in model_name:
                image_classifications.append('ambiguous')
            print('best_match', best_match)

    scan_end_time = datetime.now()
    # TODO report analysis progress and ETA

    image_classifications_string = ",".join(image_classifications)
    #log CR2 data
    if arch_file_path:
        arch_file_uuid = str(uuid.uuid4())
        log_file_data(batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, closest_model=best_match,\
            image_event_id=image_event_id, barcodes=matching_barcodes, image_classifications=image_classifications_string, \
            image_path=arch_file_path, file_uuid=arch_file_uuid)
    else:
        arch_file_uuid = None

    #log JPG data
    derivative_file_uuid = str(uuid.uuid4())
    log_file_data(batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, closest_model=best_match,\
        image_event_id=image_event_id, barcodes=matching_barcodes, image_classifications=image_classifications_string, \
        image_path=image_path, file_uuid=derivative_file_uuid, derived_from_file=arch_file_uuid)


analysis_end_time = datetime.now()

if conn:
    conn.close()
print('Started:', analysis_start_time)
print('Completed:', analysis_end_time)
print('Files analyized:', files_analyzed)
print('Duration:', analysis_end_time - analysis_start_time)
if files_analyzed > 0:
    print('Time per file:', (analysis_end_time - analysis_start_time)/files_analyzed)
print('Report written to:', log_file_name)
