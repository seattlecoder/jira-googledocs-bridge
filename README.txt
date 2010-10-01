Description:

The google-docs-jira.py file is a python script that retrieves information from 
the future grid JIRA server and put the information into a Google Docs document.


Before you run the script:

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


How to run (currently, it is a test version):

> python google-docs-jira.py
or
>./google-docs-jira.py

The current script will do the following at once:
1. create/upload file-edit
2. download (export) file-edit as file-edit.tmp.
3. edit the contents in file-edit.tmp
4. write the update into a new file file-view
5. print out some issues
6. upload file-view

After you run the script, you will see file-edit and file-view in the Google 
DocsJira folder.


Current Status:

tested with multiple tags (file-edit). but not yet tested with actual files.

tested contents = <issue><jira>FG-111</jira><jira>FG-101</jira><jiralist>
summary ~ portal</jiralist></issue>

FG-111 and FG-101 are replaced with actual issue data.
The query 'summary ~ portal' is replaced with actual issues.


Problems:

*if the number (3rd argument of method getIssueFromJqlSearch()) is 10, it fails.

error message:

Traceback (most recent call last):
  File "jira.py", line 219, in <module>
    content = updateContent(content) # this is test
  File "jira.py", line 157, in updateContent
    duedate = issue.duedate[0:3]
TypeError: 'NoneType' object is not subscriptable

*method getCustomFields() call fails.

error message:

com.atlassian.jira.rpc.exception.RemotePermissionException: Remote custom fields
can only be retrieved by an administrator.

*SOAP (JIRA) authentication fails if username & password are read from files.
(hardcoded username & password does not fail.)
However, Google authentication has no problem with files.
