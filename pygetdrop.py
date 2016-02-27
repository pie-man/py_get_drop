#!/usr/bin/python

import subprocess
import exifread
import time
import os, errno, subprocess, filecmp
import sys, getopt
import pickle

# Location of dropbox_uploader script.
drop_uploader = "/home/pi/Dropbox-Uploader/dropbox_uploader.sh"
# Max no. of trys to execute commands with dropbox_uploader.
max_trys = 3

# list of directories to get.
#check_dir_list = ["Photos","R.Photos"]
check_dir_list = ["R.Photos"]
download_dir = "/home/pi/Dropbox-Uploader/Photos_temp"
wait_list_file = "file_list_4_dropbox"

archives = []

# Setup place to backup to...
    
class DB_File(object):
    """Object of convenience. Gives me somewhere to stuff all the bits that relate
       to each file on Dropbox and allows easy storage of them in a list."""

    def __init__(self, db_name, db_path, db_size,
                 local_name=None, local_path=None):
        self.db_name = db_name
        self.db_path = db_path
	self.size = db_size
        self.local_name = local_name
        self.local_path = local_path
	#self.backup_a = False
	#self.backup_b = False
	self.backup_dict = {}
	for archive in archives:
	    self.backup_dict[archive['host']] = False
	# Okay, thinking about this - init only gets run when creating a new file
	# object - I need to clean out this garbage from the files loaded in from
	# previous runs. Had better work out where ot move this block to.
	# Just check there are no unwanted hosts left in backup dict
	for host in self.backup_dict.keys():
            found = False
	    for archive in archives:
	        if host == archive['host']:
		    found = True
            if not found:
	        print("Removing redundent host {0:s} for file object".format(
		    host))
	        del self.backup_dict[host]

    def get_size(self):
        return self.size

    def backup_ok(self, host):
        print ("registering backup, to system {0:s}, of {1:s}/{2:s}".format(
	                         host, self.local_path, self.local_name))
	self.backup_dict[host] = True

    def check_backup(self, host):
        check = False
	if host in self.backup_dict:
	    check = self.backup_dict[host]
	return check

    def check_all_backups(self):
        if all(self.check_backup(archive['host']) for archive in archives):
            print("{0:s}/{1:s} claims to have backed up to all hosts".format
	                               (self.local_path, self.local_name))
            all_backups = True
	else:
            print("{0:s}/{1:s} claims NOT to have backed up to all hosts".format
	                               (self.local_path, self.local_name))
	    all_backups = False
	return all_backups


    def a_backup_ok(self):
        print ("registering backup, to system A, of {0:s}/{1:s}".format(
	                               self.local_path, self.local_name))
	self.backup_a = True

    def b_backup_ok(self):
        print ("registering backup, to system B, of {0:s}/{1:s}".format(
	                               self.local_path, self.local_name))
	self.backup_b = True

    def change_local_locn(self, local_path, local_name):
        print("Registering new location of {0:s}/{1:s}\n".format(
	         self.local_path, self.local_name) +
              "As {0:s}/{1:s}".format(local_path, local_name))
	self.local_path = local_path
	self.local_name = local_name

    def get_key_local(self):
        return (self.local_path, self.local_name)

    def get_key_db(self):
        return (self.db_path, self.db_name)

def det_gropbox_listing(path = ""):
    """Given an optional path, retireves a listing from Dropbox for that path.
       Returns two arrays. The first is a list of directory names, the second
       a list of tuples giving the the filename and size. All names are
       relative to path."""
    DB_TYPE = 0
    DB_SIZE = 1
    DB_NAME = 2

    files = []
    dirs = []
    dropbox_cmd = [drop_uploader, "list", path]
    droplist = subprocess.check_output(dropbox_cmd)
    for line in droplist.split("\n"):
        line = line.strip()
        elements = [doodah.strip() for doodah in line.split(' ',2)]
        if elements[DB_TYPE] == "[D]":
            dirs += [elements[DB_NAME]]
        if elements[DB_TYPE] == "[F]":
            files += [(elements[DB_NAME],elements[DB_SIZE])]
    return dirs,files

def exif_date_to_path(file_name):
    """Takes a filename, for an image file. Retrieves the EXIF data from
       the file and returns a path string of <year>/<month>/<day>"""
    f = open(file_name, 'rb')
    tags = exifread.process_file(f, details=False, stop_tag='DateTimeOriginal')
    #for tag in tags.keys():
    #    if tag not in ('JPEGThumbnail', 'TIFFThumbnail', 'Filename', 'EXIF MakerNote'):
    #        print "Key: %s, value %s" % (tag, tags[tag])
    date_time = tags["EXIF DateTimeOriginal"]
    print date_time
    phototime = time.strptime(str(date_time), "%Y:%m:%d %H:%M:%S")
    newpath = time.strftime("%Y/%m/%d", phototime)
    print "newpath is : ",newpath
    return newpath

def mkdir_p(path):
    try:
        os.makedirs(path)
    except OSError as exc: # Python >2.5
        if exc.errno == errno.EEXIST and os.path.isdir(path):
            pass
        else:
	    raise

def save_obj(obj, name ):
    with open(name + '.pkl', 'wb') as f:
        pickle.dump(obj, f, 0)
        #pickle.dump(obj, f, pickle.HIGHEST_PROTOCOL)

def load_obj(name ):
    with open(name + '.pkl', 'rb') as f:
        return pickle.load(f)

def move_file(filename, newpath, attempt = 0):
    """Takes a filename, a path and an optional attempt number.
       Checks if file exists at path. If it doesn't the file is
       moved to path. If it does the attempt number is incremented
       by 1 and added to the filename. The move is then reattempted
       Returns the new path/filename of the file."""
    old_path = os.path.dirname(filename)
    name = os.path.basename(filename)
    base, extension = os.path.splitext(name)
    filetry = name
    print "attemp no. ", attempt
    while os.path.exists( newpath +"/"+ filetry):
        if filecmp.cmp(filename, newpath +"/"+ filetry):
	    print "Making no move - file is identical to one in place"
	    os.remove(filename)
	    return (newpath, filetry)
        attempt += 1
        print "attemp no. ", attempt
        filetry = base + "_" + str(attempt) + extension
    os.rename(filename, newpath +"/"+filetry)
    return  (newpath, filetry)


def seek(target, domain):
    index = 0
    pos_list = []
    while target in domain[index:]:
        loc = index + domain[index:].index(target)
	print "found {0:}  at index {1:d}".format(target,loc)
	index = loc + 1
	pos_list.append(loc)
    return pos_list


def main():
    # Open list of files waiting sync (filename, size, and date of download)
    # Each record should have :
    #    dropbox_dir, dropbox_filename, size, new_filename_inc_path, date_of_download
    # perhaps read into a dictionary with new_filename_inc_path as key ?
    # Actually it has be keyed on dir + dropbox_filename for size check...

    try:
        setup_file = os.path.expanduser("~/.pygetdrop.rc")
        print "Getting setup file :" + setup_file + ".pkl"
    #    wait_list_file = open(list_of_files_waiting)
        archives = load_obj(setup_file)
    except IOError:
        # If not exists, PANIC
        print "Couldn't find file :" + setup_file + ".pkl"
        print "Try running {0:s} -s to create a setup file."
        sys.exit(7)

    try:
        print "Getting wait list file :" + wait_list_file + ".pkl"
    #    wait_list_file = open(list_of_files_waiting)
        wait_list = load_obj(wait_list_file)
    except IOError:
        # If not exists, create the file
        print "Couldn't find file :" + wait_list_file
        wait_list = []

    # Get listing for Dropbox root dir
    dirs, files = det_gropbox_listing()

    # Check if any dirs present are on the 'check' list and get file listing
    # Which includes file sizes
    files_to_get = []
    for dir in dirs:
        if dir in check_dir_list:
            subdirs, subfiles = det_gropbox_listing(dir)

            print "subdirs are : \n " + "\n ".join(subdirs)
            print "subfiles are : \n " + "\n ".join(
	                               "{0:>30s} - {1:s}".format(name, size)
		                       for name, size in subfiles)
	    got_it_list = []
            for thing in wait_list:
	        got_it_list.append((thing.get_key_db()))
            for db_file, db_size in subfiles:
                file_key = (dir ,db_file)
                if file_key in got_it_list:
		    # FUTURE UPGRADE - look for multiple files of same name
		    # check by size. Move file will give them unique names
		    # locally. So re-index by them for deletion....
		    #positions = seek(file_key, got_it_list)
		    pos_in_list = got_it_list.index(file_key)
		    print "It's the {0:d}'th element in the list".format(pos_in_list)
                    if wait_list[pos_in_list].get_size == int(db_size):
                        print "Skipping download of " + db_file
                    else:
                        print "Got myself a file size mismatch....."
                        print "Don't know what to do with " + db_file
                else:
                    files_to_get += [(dir, db_file, int(db_size)) ]
                    print "gonna get : ",files_to_get[-1]

    # Check to see if files exist @ same size - if not download
    for directory, db_filename, size in files_to_get:
        newname = db_filename.replace(" ","_")
	new_fullpath = "{0:s}/{1:s}".format(download_dir, newname)
        print ("getting file : " + directory + "/" + db_filename + " => " +
	       new_fullpath)
        dropbox_cmd = [drop_uploader,"download", directory +"/"+ db_filename,
	               new_fullpath, "-s"]
        # Allow max_trys trys as Dropbox command sometimes times out on slow
	# internet days....
	no_trys = 0
        while no_trys < max_trys:
	    try:
                results =  subprocess.check_output(dropbox_cmd)
	        thing = DB_File(db_filename, directory, size,
	                        local_path=download_dir,
	       	                local_name=newname)
                print results
	        wait_list.append(thing)
	        break
	    except:
	        print "Big fat BUM. Something's gone up spout like...."
		no_trys += 1
		#raise

        if no_trys == max_trys:
	    print("Giving up on {0:s}/{1:s}".format(directory, db_filename))
	    continue
        newpath = download_dir +"/"+ exif_date_to_path(new_fullpath)
        mkdir_p(newpath)
        newnewpath, newnewname = move_file(new_fullpath, newpath)
        print("moved {0:s} to {1:s}/{2:s}".format(newname,
	                                          newnewpath, newnewname))
        thing.change_local_locn(newnewpath, newnewname)

    source_dir = download_dir +'/'
    arguments=["--verbose", "--recursive", "--human-readable",
               "--no-owner", "--no-group", "--no-perms", "--no-acls",
               "--times"]

    for archive in archives:
        destination = (archive['user'] +'@' + archive['host'] +
	               archive['target_dir'])
        env_d = dict(os.environ)
	if archive['password'] is not None:
	    #password = "--password-file=".format(archive['password'])
	    #args = arguments + [password, source_dir, destination]
	    args = arguments + [source_dir, destination]
	    print "setting password"
	    env_d['RSYNC_PASSWORD'] = archive['password']
	else:
	    args = arguments + [source_dir, destination]
        returncode = subprocess.call(["rsync"] + args, env=env_d)
        if returncode == 0:
            print "sync successfull"
	    for thing in wait_list:
	        thing.backup_ok(archive['host'])
        else:
            print "error during rsync"


    got_it_list = []
    kill_list = []
    print "There are ",len(wait_list)," things in wait_list"
    for count, thing in enumerate(wait_list):
        local_key = thing.get_key_local()
        local_path = local_key[0]
	local_name = local_key[1]
        print "looking at {0:d}: {1:s}/{2:s}".format(count, local_path, local_name)
        got_it_list.append(local_key)
	#if thing.backup_a:
	if thing.check_all_backups():
	    print "should delete {0:s}/{1:s}".format(local_path, local_name)
	    kill_list.append(local_key)
    for local_key in kill_list:
        loc = got_it_list.index(local_key)
	db_key = wait_list[loc].get_key_db()
	try:
	    # Remove from index lists
	    print("removing {0:s} from location {1:d} in wait_list".format(
	          local_key,loc))
	    got_it_list[loc:loc+1] = []
	    wait_list[loc:loc+1] = []
	    # remove Dropbox copy
	    db_file = "{0:s}/{1:s}".format(db_key[0],db_key[1])
            dropbox_cmd = [drop_uploader, "delete", db_file]
	    print("Deleting dropbox file : {0:s}".format(db_file))
            result = subprocess.check_output(dropbox_cmd)
	    # remove local copy
	    local_file = "{0:s}/{1:s}".format(local_key[0],local_key[1])
	    print("Deleting local file : {0:s}".format(local_file))
	    os.remove(local_file)
	except:
	    print "Error removing ",db_key, "somehow"
	    raise


    save_obj(wait_list, wait_list_file)

def start_setup():
    print "Nice try..."
    setup_file = os.path.expanduser("~/.pygetdrop.rc")
    try:
    #    wait_list_file = open(list_of_files_waiting)
        wait_list = load_obj(setup_file)
    except IOError:
        # If not exists, create the file
        print "Couldn't find file :" + setup_file
        setup = []
    
    another = True
    added = 0
    while another:
        host = raw_input("What host would you like to back up to ?")
        user = raw_input("Please provide the username ?")
        password = raw_input("And the password ?")
	if password == '':
	    password = None
        target_dir = raw_input("Finally, what's the intended directory ?")
	print("Is this what you intended ?")
	print("Host     : {0:s}").format(host)
	print("User     : {0:s}").format(user)
	print("Password : {0:s}").format(password)
	print("Target dir : {0:s}").format(target_dir)
	confirm = raw_input("Please confirm Y/N")
	if confirm[0].lower() == 'y':
            setup.append( { 'host' : host,
                            'user' : user,
                            'password' : password,
                            'target_dir' : target_dir
                          } )
            added += 1
	else:
	    print("Abandoned adding that entry...")
	confirm = raw_input("Would you like to add another ?")
	if confirm[0].lower() == 'y':
	    another = True
	else:
	    another = False
    if added > 0:
	print("Saving new host configs.")
        save_obj(setup, setup_file)
    sys.exit()

if __name__ == "__main__":
    try:
        opts, args = getopt.getopt(sys.argv[1:],"hs",["setup"])
    except getopt.GetoptError:
        print "{0:s} [-s|--setup]".format(sys.argv[0])
	sys.exit(2)
    for opt, arg in opts:
        print "option is ",opt
        if opt == '--h':
            print "{0:s} [-s|--setup]".format(sys.argv[0])
	    sys.exit()
	elif opt in ("-s","--setup"):
	    start_setup()
    main()
