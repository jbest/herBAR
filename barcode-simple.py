import argparse
from hashlib import md5
import uuid
import glob
from datetime import datetime
import re
import csv
import os
import platform
from PIL import Image
import os
from pathlib import Path
from pyzbar.pyzbar import decode

# File extensions that are scanned and logged
INPUT_FILE_TYPES = ['.jpg', '.jpeg', '.JPG', '.JPEG']
# File type extensions that are logged when filename matches a scanned input file
ARCHIVE_FILE_TYPES = ['.CR2', '.cr2', '.RAW', '.raw']
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
        # File not found
        return None
    return res[0]

def casedpath(path):
    # from https://stackoverflow.com/a/35229734
    r = glob.glob(re.sub(r'([^:/\\])(?=[/\\]|$)', r'[\1]', path))
    return r and r[0] or path

def log_file_data(batch_id=None, batch_path=None, batch_flags=None, \
    image_event_id=None, barcodes=None, barcode=None, image_classifications=None, \
    image_path=None, new_path=None, file_uuid=None, derived_from_file=None):
    basename = os.path.basename(image_path)
    file_name, file_extension = os.path.splitext(basename)
    # Get file creation time
    file_creation_time = datetime.fromtimestamp(creation_date(image_path))
    # generate MD5 hash
    file_hash = md5hash(image_path)
    datetime_analyzed = datetime.now()

    # clean up values for writing to SQLite (doesn't like dicts)
    if barcodes:
        barcodes = str(barcodes)
    else:
        barcodes = ''
    # TODO log batch flags, barcode
    log_writer.writerow({'batch_id': batch_id, 'batch_path': batch_path, 'project_id': project_id, \
        'image_event_id': image_event_id, 'datetime_analyzed': datetime_analyzed, \
        'image_path': image_path, 'basename': basename, 'file_name': file_name, 'new_path': new_path, \
        'file_creation_time': file_creation_time, \
        'file_hash': file_hash, 'file_uuid': file_uuid, 'derived_from_file': derived_from_file, 'barcodes': barcodes, 'barcode': barcode})

# set up argument parser
ap = argparse.ArgumentParser()
ap.add_argument("-s", "--source", required=True, \
    help="Path to the directory that contains the images to be analyzed.")
ap.add_argument("-p", "--project", required=False, choices=PROJECT_IDS, \
    help="Project name for filtering in database")
ap.add_argument("-b", "--batch", required=False, \
    help="Flags written to batch_flags, can be used for filtering downstream data.")
ap.add_argument("-o", "--output", required=False, \
    help="Path to the directory where log file is written.")
ap.add_argument("-n", "--no_rename", required=False, action='store_true', \
    help="Files will not be renamed, only log file generated.")
args = vars(ap.parse_args())
#TODO add test run option

analysis_start_time = datetime.now()
batch_id = str(uuid.uuid4())
batch_path = os.path.realpath(args["source"])
project_id = args["project"]

if args["batch"]:
    batch_flags = args["batch"]
    print('Batch flags:', batch_flags)
else:
    batch_flags=None

no_rename = args["no_rename"]

# Create file for results
log_file_name = analysis_start_time.date().isoformat() + '_' + batch_id + '.csv'
# Test output path
if args["output"] is not None:
    output_directory = os.path.realpath(args["output"])
    print('output_directory:', output_directory)
    #TODO make sure directory exists and is writeable
    log_file_path = os.path.join(output_directory, log_file_name)
    #log_file = open(log_file_path, "w")
else:
    #log_file = open(log_file_name, "w") # will default to write in location where script is executed
    log_file_path = log_file_name

#with open(log_file_path, 'w', newline='') as csvfile:
csvfile = open(log_file_path, 'w', newline='')
# write header
fieldnames = ['batch_id', 'batch_path', 'batch_flags', 'project_id', \
    'image_event_id', 'datetime_analyzed', 'barcodes', 'barcode', \
    'image_path', 'basename', 'file_name', 'file_extension', 'new_path', \
     'file_creation_time', \
    'file_hash', 'file_uuid', 'derived_from_file']
log_writer = csv.DictWriter(csvfile, fieldnames=fieldnames)
log_writer.writeheader()

#TODO extract information from directory name (imager, station, etc)
#iterate JPG files in directory passed from args
directory_path = os.path.realpath(args["source"])
files_analyzed = 0
print('Scanning directory:', directory_path)
#TODO change image search to use INPUT_FILE_TYPES

def process(file_path=None, new_stem=None, uuid=None ,barcode=None, barcodes=None, image_event_id=None):
    print('Processing:', file_path.name)
    rename_status, new_path = rename(file_path=file_path, new_stem=new_stem)
    if rename_status:
        # log success
        print('log success:', barcode)
        # TODO log derivative_file_uuid and arch_file_uuid into file_uuid and derived_from_file
        # TODO log success or fail
        log_file_data(batch_id=batch_id, batch_path=batch_path, batch_flags=batch_flags, \
            image_event_id=image_event_id, barcode=barcode, barcodes=barcodes, \
            image_path=file_path, new_path=new_path, \
            file_uuid=None, derived_from_file=None)
    else:
        # log fail
        print('log fail')

def rename(file_path=None, new_stem=None):
    #current_path = os.path.join(current_working_path, original_basename)
    parent_path = file_path.parent
    file_extension = file_path.suffix
    new_file_name = new_stem + file_extension
    #print('new_file_name:', new_file_name)
    new_path = parent_path.joinpath(new_file_name)
    #print('new_path:', new_path)

    if file_path.exists():
        print('Exists:', file_path)
        if new_path.exists():
            print('ALERT - file exists, can not overwrite:')
            print(new_path)
        else:
            try:
                #os.rename(current_path, new_path)
                if no_rename:
                    # don't rename but return True to simulate for logging
                    return True, file_path
                else:
                    file_path.rename(new_path)
                    return True, new_path
            except OSError:
                # Possible problem with character in new filename
                print('ALERT - OSError. new_path:', new_path, 'file_path:', file_path )
                return False, None
            except Error as e:
                print("Unexpected error:", e)
                raise

def get_barcodes(file_path=None):
    # read barcodes from JPG
    barcodes = decode(Image.open(file_path))
    matching_barcodes = []
    if barcodes:
        for barcode in barcodes:
            if str(barcode.type) in ACCEPTED_SYMBOLOGIES:
                symbology_type = str(barcode.type)
                data = barcode.data.decode('UTF-8')
                matching_barcodes.append({'type':symbology_type, 'data':data})
                print(symbology_type, data)
        return matching_barcodes
    else:
        print('No barcodes found')
        return None

def walk(path=None):
    scan_start_time = datetime.now()
    for root, dirs, files in os.walk(path):
        for file in files:
            # files_analyzed += 1
            file_path_string = os.path.join(root, file)
            file_path = Path(file_path_string)
            #print(file_path.suffix)
            if file_path.suffix in INPUT_FILE_TYPES:
                #print(file_path.name)
                # Get barcodes
                barcodes = get_barcodes(file_path=file_path)
                #print('barcodes:', barcodes)
                # get file stem
                if barcodes:
                    file_stem = file_path.stem
                    #print(file_stem)
                    # find archive files matching stem
                    arch_file_path = None
                    for archive_extension in ARCHIVE_FILE_TYPES:
                        potential_arch_file_name = file_stem + archive_extension
                        potential_arch_file_path_string = os.path.join(directory_path, potential_arch_file_name)
                        potential_arch_file_path = Path(potential_arch_file_path_string)
                        # test if archive file exists
                        # TODO change filename comparison be case-sensitive

                        # if os.path.exists(potential_arch_file_path):
                        if potential_arch_file_path.exists():
                            # This is using case insensitive matching on Mac
                            arch_file_path = potential_arch_file_path
                            #TODO generate hash, uuid, read creation time, etc
                            #print('matching achive file:', arch_file_path)
                            # stop looking for archive file, go with first found
                            break
                    image_event_id = str(uuid.uuid4())
                    arch_file_uuid = str(uuid.uuid4())
                    derivative_file_uuid = str(uuid.uuid4())
                    # assume first barcode
                    # TODO check barcode pattern
                    barcode = barcodes[0]['data']

                    # process JPEG
                    # TODO add derived from uuid
                    process(file_path=file_path, new_stem=barcode, uuid=derivative_file_uuid ,barcode=barcode, barcodes=barcodes, image_event_id=image_event_id)
                    # process archival
                    process(file_path=arch_file_path, new_stem=barcode, uuid=arch_file_uuid, barcode=barcode, barcodes=barcodes, image_event_id=image_event_id)

# old()

print('walking:', batch_path)
walk(path=batch_path)

# Close CSV log file
csvfile.close()

analysis_end_time = datetime.now()

print('Started:', analysis_start_time)
print('Completed:', analysis_end_time)
print('Files analyzed:', files_analyzed)
print('Duration:', analysis_end_time - analysis_start_time)
if files_analyzed > 0:
    print('Time per file:', (analysis_end_time - analysis_start_time)/files_analyzed)
print('Report written to:', log_file_name)
