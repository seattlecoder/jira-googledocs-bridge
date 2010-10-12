#!/usr/bin/python

import gdata.docs.data
import gdata.docs.client
import SOAPpy
import re
from xml.dom.minidom import parseString
import argparse
import sys


### get folder uri
def getFolderUri(folderName):
  # retrieve a list of folders
  feed = client.GetDocList(uri='/feeds/default/private/full/-/folder')

  # get folder uri: this uri is required to upload a file to the folder
  folderUri = None
  for folder in feed.entry:
    if folder.title.text == folderName:
      folderUri = folder.content.src

  return folderUri

### upload
## path: file path in the local machine
## file: file name
def upload(path, file, folderName):
  folder_uri = getFolderUri(folderName)
  entry = client.Upload(media=path, title=file, folder_or_uri=folder_uri, content_type='application/msword')

  print 'Document \'%s\' uploaded.' % file

### download
## resourceid: google document id
def download(resourceid):
  #print resourceid
  entry = client.GetDoc(resourceid)

  # download with tmp extension
  #client.Download(entry, file_path='%s' % entry.title.text+file_ext)

  file_path = '%s' % entry.title.text+file_ext
  client.Export(entry, file_path)

  print 'Document \'%s\' downloaded as \'%s\'.' % (entry.title.text, entry.title.text+file_ext)

### create a document with content and upload it to google docs
## fname: file name
#def createDoc(fname):
#  file = open(fname,'w')
#  file.write('<jira>FG-101</jira>')
#  file.close()
#
#  print 'Document \'%s\' created with contents.' % fname
#
#  fpath = fname
#  upload(fpath, fname)

### get resource id by given doc title
## title: file name on the Google Docs server.
## this may need to be changed. e.g.> multiple files can have the same name.
def getResourceId(title):
  feed = client.GetDocList()
  for entry in feed.entry:
    if entry.title.text.encode('UTF-8') == title and entry.GetDocumentType() == 'document':
      return entry.resource_id.text
  return None

### download document by title (file name)
def downloadDoc(title):
  resourceId = getResourceId(title)

  if resourceId == None:
    sys.exit('File \''+title+'\' does not exists.')

  download(resourceId)

### get content from html format
def getContentsFromFile(fname):
  # read file
  file = open(fname,'r')
  str = file.read()
  file.close()

  return str

### replace html entity
def replaceHtmlEntity(str):
  lt = '&lt;'
  gt = '&gt;'

  # get start / end index of content
  start = str.index(lt)
  end = str.rindex(gt) + 4

  # replace html entity
  substr = str[start:end]
  substr = substr.replace(lt,'<')
  substr = substr.replace(gt,'>')

  return substr

### get jira key from text contents
def getKeyList(string):
  keyList = []

  jiraMatchObj = re.findall(r'&lt;jira&gt;FG-\d*&lt;/jira&gt;', string)

  if jiraMatchObj:
    for match in jiraMatchObj:
      match = re.sub(r'<.*?>', '', match)
      match = replaceHtmlEntity(match)

      dom = parseString(match)
      jiras = dom.getElementsByTagName('jira')
      for jira in jiras:
        nodes = jira.childNodes
        for node in nodes:
          if node.nodeType == node.TEXT_NODE:
            issuekey = node.data
            keyList.append(issuekey)

  return keyList

### get jira query from text contents
def getQueryList(string):
  queryList = []
  jiralistMatchObj = re.findall(r'&lt;jiralist&gt;.*?&lt;/jiralist&gt;', string)
  
  if jiralistMatchObj:
    for match in jiralistMatchObj:
      match = re.sub(r'<.*?>', '', match)
      match = replaceHtmlEntity(match)

      dom = parseString(match)
      jiralists = dom.getElementsByTagName('jiralist')
      for jiralist in jiralists:
        nodes = jiralist.childNodes
        for node in nodes:
          if node.nodeType == node.TEXT_NODE:
            query = node.data
            queryList.append(query)

  return queryList

### find id
def findId(list, id):
  for e in list:
    if e.id == id:
      return e
  return None

### test update content
def updateContent(contents, linkOption):
  # soap authentication
  soap = SOAPpy.WSDL.Proxy('http://jira.futuregrid.org/rpc/soap/jirasoapservice-v2?wsdl')

  # read jira user name from file
  file = open('jira-username','r')
  jira_username = file.readline().rstrip()
  file.close()

  # read jira password from file
  file = open('jira-passwd','r')
  jira_passwd = file.readline().rstrip()
  file.close()

  auth = soap.login(jira_username, jira_passwd)
  info = soap.getServerInfo(auth)
  resolutions = soap.getResolutions(auth)
  statuses = soap.getStatuses(auth)
  priorities = soap.getPriorities(auth)
  #customFields = soap.getCustomFields(auth)
  #print customFields

  keys = getKeyList(contents)
  queries = getQueryList(contents)

  # get key value
  for issuekey in keys:
    issue = soap.getIssue(auth, issuekey)

    #print issue key
    priority = '-'
    if issue.priority != None:
      pri = findId(priorities, issue.priority)
      if pri != None:
        priority = pri.name

    assignee = '-'
    if issue.assignee != None:
      assignee = soap.getUser(auth, issue.assignee)

    if linkOption == True:
      jiraIssue = '<a href=\"'+info.baseUrl+'/browse/'+issue.key+'\">'+issue.key+'</a>'+': '+issue.summary+' '+priority+' '+assignee.fullname+' Due:'+str(issue.duedate[0:3])
    else:
      jiraIssue = issue.key+': '+issue.summary+' '+priority+' '+assignee.fullname+' Due:'+str(issue.duedate[0:3])
    contents = contents.replace(issuekey, jiraIssue)

  # get query
  for query in queries:
    issues = soap.getIssuesFromJqlSearch(auth, query, 5)

    jiraIssueList = "<table border='1' cellspacing='0'><tr><th>No.</th><th>Key</th><th>WBS</th><th>Summary</th><th>Status</th><th>Pri</th><th>Duedate</th><th>Prog.%</th><th>Res</th><th>Assignee</th></tr>"
    issueNum = 0

    for issue in issues:
      customFields = issue.customFieldValues
      issueNum = issueNum + 1
      no = str(issueNum)
      key = issue.key
      wbs = 'wbs'
      summary = '-'
      if issue.summary != None:
        summary = issue.summary
      status = '-'
      if issue.status != None:
        stat = findId(statuses, issue.status)
        if stat != None:
          status = stat.name
      priority = '-'
      if issue.priority != None:
        pri = findId(priorities, issue.priority)
        if pri != None:
          priority = pri.name
      duedate = '-'
      if issue.duedate != None:
        duedate = issue.duedate[0:3]
      #progress = issue.progress
      resolution = 'UNRESOLVED'
      if issue.resolution != None:
        res = findId(resolutions, issue.resolution)
        if res != None:
          resolution = res.name
      assignee = '-'
      if issue.assignee != None:
        assignee = soap.getUser(auth, issue.assignee)

      if linkOption == True:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td><td><a href=\"'+info.baseUrl+'/browse/'+key+'\">'+key+'</a></td><td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td>'+priority+'</td><td>'+str(duedate)+'</td><td>'+'</td><td>'+resolution+'</td><td>'+assignee.fullname+'</td></tr>'
      else:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td><td>'+key+'</a></td><td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td>'+priority+'</td><td>'+str(duedate)+'</td><td>'+'</td><td>'+resolution+'</td><td>'+assignee.fullname+'</td></tr>'

    jiraIssueList = jiraIssueList + '</table>'
    contents = contents.replace(query, jiraIssueList)

  contents = re.sub(r'&lt;jira&gt;|&lt;/jira&gt;|&lt;jiralist&gt;|&lt;/jiralist&gt;', '', contents)

  #print 'updated contents: '+contents
  print 'Contents updated.'

  return contents

### write content into a file
def writeContent(content, file_name):
  file = open(file_name,'w')
  file.write(content)
  file.close()

  print 'Updated content has been written to Document \'%s\'.' % file_name

### upload document
def uploadDoc(file, folderName):
  fpath = file
  upload(fpath, file, folderName)


### main ###
parser = argparse.ArgumentParser()
parser.add_argument('-l', '--link', action='store_true', default=False, dest='link', help='add a link to JIRA Key value')
parser.add_argument('-f', '--filename', action='store', dest='filename', help='specify a file name to download')
parser.add_argument('-d', '--directory', action='store', default='GoogleDocsJira', dest='folder', help='specify folder to upload a file')
options = parser.parse_args()
print options
linkOption = options.link
file_name = options.filename
folder = options.folder

if file_name == None:
  parser.print_help()
  sys.exit('Please specify file name with option \'-f\'.')

client = gdata.docs.client.DocsClient(source='fg-issue-v1')
client.ssl = True  # Force all API requests through HTTPS
client.http_client.debug = False  # Set to True for debugging HTTP requests

# read google email from file
file = open('gmail','r')
gmail = file.readline().rstrip()
file.close()

# read google password from file
file = open('gpasswd','r')
gpasswd = file.readline().rstrip()
file.close()

client.ClientLogin(gmail, gpasswd, client.source, 'writely')

###createDoc('file-edit') ## not used

file_ext = '.tmp'

downloadDoc(file_name)
content = getContentsFromFile(file_name+file_ext)
content = updateContent(content, linkOption)
writeContent(content, file_name+'-view')
uploadDoc(file_name+'-view', folder)
