#!/usr/bin/python3 -u
## The -u option turns off block buffering of python output. This assures
## that error messages get printed to the log file as they happen.
#  
# Module: createPressureRrd.py
#
# Description: This module creates a round robin database.
#
# Note: _rrdtool_ must be installed on the host running this program.
#
# Install rrdtool on the raspberry pi by running
#
#     sudo apt-get install rrdtool
# 
# Create a directory /home/$USER/database for the rrdtool database.
# For more information on rrdtool see http://oss.oetiker.ch/rrdtool
#       
# Revision History
#   * v10 - 05 Nov 2018 by J L Owrey; first release

def createRrdDatabase(fPath, dbUpateInterval=10, dbSizeDays=366):
    """
    Creates a rrdtool round robin database.  The database when
    first created does not contain any data.  The database will be
    created in the /home/$USER/database folder.
    Parameters: none
    Returns: true, if successful, false otherwise
    """
    import subprocess

    # Creating a database wipes out any previous database with the
    # same name, in the same location.  Require an existing database
    # to be manually deleted before creating a new database.
    if os.path.exists(fPath):
        print("rrdtool altimeter database already exists!")
        user_input = input('Create a new database (yes/no): ')
        if user_input.lower() == 'no':
          return False
        elif user_input.lower() == 'yes':
          backup_database(fPath)
        else:
          return False
    # Calculate the database size
    heartBeat = 2 * dbUpateInterval
    rrdNumRows = int(dbSizeDays * round(86400 / dbUpateInterval))
       
    # Format the rrdtool create database command.
    strFmt = ("rrdtool create %s --step %s "
             "DS:altitude:GAUGE:%s:U:U DS:pressure:GAUGE:%s:U:U "
             "DS:temperature:GAUGE:%s:U:U "
             "RRA:AVERAGE:0.5:1:%s")

    strCmd = strFmt % (fPath, dbUpateInterval, \
                 heartBeat, heartBeat, heartBeat, rrdNumRows)
    
    print("creating rrdtool database...\n\n%s\n" % strCmd) # DEBUG

    # Run the formatted command in a subprocess.
    try:
        subprocess.check_output(strCmd, stderr=subprocess.STDOUT, \
                                shell=True)
    except subprocess.CalledProcessError as exError:
        print("rrdtool create failed: %s" % exError.output)
        return False
    else:
        print('database creation successful\n')
    return True
## end def

def backup_database( path ):
      dPath, file_name = os.path.split(path)
      name, ext = os.path.splitext(file_name)
      bak_file = name + '_bak' + ext
      bak_path = dPath + '/' + bak_file
      print('saving existing database as %s\n' % bak_path)
      shutil.copy(path, bak_path)
## end def

if __name__ == '__main__':
    import os
    import shutil
    _USER = os.environ['USER']
    _RRD_FILE = '/home/%s/database/altimeterData.rrd' % _USER
    _DATABASE_UPDATE_INTERVAL = 30
    _DATABASE_SIZE_IN_DAYS = 180

    createRrdDatabase(_RRD_FILE, _DATABASE_UPDATE_INTERVAL,
                      _DATABASE_SIZE_IN_DAYS)

## end module
