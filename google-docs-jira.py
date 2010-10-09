#!/usr/bin/python

import gdata.docs.data
import gdata.docs.client
import SOAPpy
import re
from xml.dom.minidom import parseString


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
def upload(path, file):
  entry = client.Upload(media=path, title=file, folder_or_uri=getFolderUri('GoogleDocsJira'), content_type='application/msword')
  #entry = client.Upload(media=path, title=file, content_type='application/msword')

  print 'Document \'%s\' uploaded.' % file

### download
## resourceid: google document id
def download(resourceid):
  file_ext = '.tmp'
  print resourceid
  entry = client.GetDoc(resourceid)

  # download with tmp extension
  #client.Download(entry, file_path='%s' % entry.title.text+file_ext)

  file_path = '%s' % entry.title.text+file_ext
  client.Export(entry, file_path)

  print 'Document \'%s\' downloaded as \'%s\'.' % (entry.title.text, entry.title.text+file_ext)

### create a document with content and upload it to google docs
## fname: file name
def createDoc(fname):
  file = open(fname,'w')
  file.write('<jira>FG-101</jira>')
  file.close()

  print 'Document \'%s\' created with contents.' % fname

  fpath = fname
  upload(fpath, fname)

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

### test update content
def updateContent(contents):
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

  keys = getKeyList(contents)
  queries = getQueryList(contents)

  # get key value
  for issuekey in keys:
    issue = soap.getIssue(auth, issuekey)

    #print issue key
    jiraIssue = issue.key+':'+issue.summary+' '+issue.priority+' '+issue.assignee+' Due:'+str(issue.duedate[0:3])
    contents = contents.replace(issuekey, jiraIssue)

  # get query
  for query in queries:
    issues = soap.getIssuesFromJqlSearch(auth, query, 3)
    #print issues
    #cf = soap.getCustomFields(auth)
    #print cf

    format = '%3s %6s %11s %-20s %2s %2s %15s %2s %8s %10s'
    #jiraIssueList = ' No    Key         WBS          Summary      S Pri    Duedate   % R  Assignee\n'
    jiraIssueList = "<table border='1' cellspacing='0'><tr><th>No.</th><th>Key</th><th>WBS</th><th>Summary</th><th>Status</th><th>Pri</th><th>Duedate</th><th>Prog.%</th><th>Res</th><th>Assignee</th></tr>"
    issueNum = 0

    for issue in issues:
      customFields = issue.customFieldValues
      issueNum = issueNum + 1
      no = str(issueNum)
      key = issue.key
      wbs = 'wbs'
      if issue.summary != None:
        summary = issue.summary
      else:
        summary = '-'
      if issue.status != None:
        status = issue.status
      else:
        status = '-'
      if issue.priority != None:
        priority = issue.priority
      else:
        priority = '-'
      if issue.duedate != None:
        duedate = issue.duedate[0:3]
      else:
        duedate = '-'
      #progress = issue.progress
      if issue.resolution != None:
        resolution = issue.resolution
      else:
        resolution = '-'
      if issue.assignee != None:
        assignee = issue.assignee
      else:
        assignee = '-'

      '''
      # make summary multiple lines
      list = []
      list.append(summary[0:20])
      length = len(summary)
      summary = summary[20:length]
      while length > 20:
        list.append(summary[0:20])
        length = len(summary)
        summary = summary[20:length]

      jiraIssueList = jiraIssueList + format % (str(issueNum), key, wbs, list[0], status, priority, duedate, 'p', resolution, assignee) + '\n'
      if len(list) > 1:
        idx = 1
        while idx < len(list):
          jiraIssueList = jiraIssueList + format % ('', '', '', list[idx], '', '', '', '', '', '') + '\n'
          idx = idx + 1
      '''
      jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td><td><a href=\"'+info.baseUrl+'/browse/'+key+'\">'+key+'</a></td><td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td><img src=\"$priorityicon\" alt=\"$priority\" /></td><td>'+str(duedate)+'</td><td>'+'</td><td>'+resolution+'</td><td>'+assignee+'</td></tr>'

    jiraIssueList = jiraIssueList + '</table>'
    contents = contents.replace(query, jiraIssueList)

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
def uploadDoc(file):
  fpath = file
  upload(fpath, file)


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


#createDoc('file-edit')

#downloadDoc('myTest')
content = getContentsFromFile('myTest.tmp')
content = updateContent(content) # this is test
#writeContent(content, 'myTest-view')
#uploadDoc('myTest-view')
