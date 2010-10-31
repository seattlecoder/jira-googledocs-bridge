## Description:

The google-docs-jira file is a python script that retrieves information from the
Future Grid JIRA server and put the information into a Google Docs document.


## Before you run the script:

It requires Python version 2.7 or later.

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
- Create a file named 'jirabridge' and write your user names and passwords in 
  the json format in the directory where the 'google-docs-jira.py' script is.
  * Follow this format:
    {"gmail" : "your google account",
     "gpasswd":"your google password",
     "jira_usrname":"your jira account",
     "jira_passwd":"your jira password"}


## Usage:

google-docs-jira.py [-h] [-l] -d DOCNAME [-f SRCFOLDER] [-s FONTSIZE] [-ul]
               [-t DESTFOLDER]

optional arguments:
  -h, --help            show this help message and exit
  -l, --link            add a link to JIRA Key value
  -d DOCNAME, --document DOCNAME
                        specify a document name to download
  -f SRCFOLDER, --folder SRCFOLDER
                        specify a folder to update all documents in it
  -s FONTSIZE, --font-size FONTSIZE
                        set font size
  -ul, --unordered-list
                        use unordered list in tree view
  -t DESTFOLDER, --to-folder DESTFOLDER
                        specify a folder to upload documents

The script download a file as '<filename>.tmp' and replaces jira keys and 
quries to the corresponding information (not directly in the downloaded file 
but in memory). The updated contents are written to a file '<filename>[-link]
[-<fontsize>][-list]-view.' If the DESTFOLDER does not exist, it is created.