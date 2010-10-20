## Description:

The google-docs-jira file is a python script that retrieves information from the
Future Grid JIRA server and put the information into a Google Docs document.


## Before you run the script:

!! You need two accounts for Google and Future Grid JIRA !!

You need to install a number of python modules if you have not.
- You need the gdata module for Google Docs List APIs.
  + install gdata
- You need the SOAPpy module for the JIRA interface.
  + install PyXML, fpconst, and SOAPpy
    *NOTE: You will get errors when you install the SOAPpy module.
           Modify file Client.py Types.py and Server.py in the SOAPpy directory.
           In the files, move the line 'from future import nested_scope'
           to the beginning of the code.
- Create files named 'jira-username', 'jira-passwd', 'gmail', and 'gpasswd' and 
  write your corresponding user names and passwords to those files where the 
  'google-docs-jira' script is.


## Usage:

google-docs-jira.py [-h] [-l] [-f FILENAME] [-d FOLDER] [-s FONTSIZE] [-i]

optional arguments:
  -h, --help            show this help message and exit
  -l, --link            add a link to JIRA Key value
  -f FILENAME, --filename FILENAME
                        specify a file name to download
  -d FOLDER, --directory FOLDER
                        specify folder to upload a file
  -s FONTSIZE, --fontsize FONTSIZE
                        set font size
  -i, --useli           use list items

The script download a file as '<filename>.tmp' and replaces jira keys and 
quries to the corresponding information (not directly in the downloaded file 
but in memory). The updated contents are written to a file '<filename>[-link]
[-<fontsize>]-view.' The file '<filename>-view' is uploaded to the Google Docs 
folder. If the folder name is given, the file is uploaded to the folder. The 
default folder is 'GoogleDocsJira.'
