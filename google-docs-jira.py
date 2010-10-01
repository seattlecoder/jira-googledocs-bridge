#!/usr/bin/python

import gdata.docs.data
import gdata.docs.client
import SOAPpy
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
  entry = client.Upload(media=path, title=file, folder_or_uri=getFolderUri('GoogleDocsJira'), content_type='text/plain')

  print 'Document \'%s\' uploaded.' % file

### download
## resourceid: google document id
def download(resourceid):
  entry = client.GetDoc(resourceid)

  # download with tmp extension
  client.Download(entry,file_path='%s.tmp'%entry.title.text)

  print 'Document \'%s\' downloaded as \'%s.tmp\'.' % (entry.title.text, entry.title.text)

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
def getContentFromFile(fname):
  lt = '&lt;'
  gt = '&gt;'

  # read file
  file = open(fname,'r')
  str = file.read()
  file.close()

  # get start / end index of content
  start = str.index(lt)
  end = str.rindex(gt) + 4

  # replace html entity
  substr = str[start:end]
  substr = substr.replace(lt,'<')
  substr = substr.replace(gt,'>')

  return substr

### test update content
def updateContent(content):
  # soap authentication
  soap = SOAPpy.WSDL.Proxy('http://jira.futuregrid.org/rpc/soap/jirasoapservice-v2?wsdl')

  # read jira user name from file
  file = open('jira-username','r')
  jira_username = file.read()
  file.close()

  # read jira password from file
  file = open('jira-passwd','r')
  jira_passwd = file.read()
  file.close()

  auth = soap.login(jira_username, jira_passwd)


  print 'original content: '+content
  issuekey = ''
  query = ''

  # get key value
  testContent = '<issue><jira>FG-111</jira><jira>FG-101</jira><jiralist>summary ~ portal</jiralist></issue>'
  dom = parseString(testContent)
  jiras = dom.getElementsByTagName('jira')
  for jira in jiras:
    print 'node name: '+jira.nodeName
    nodes = jira.childNodes
    for node in nodes:
      if node.nodeType == node.TEXT_NODE:
        print 'node data: '+node.data
        issuekey = node.data
        
        issue = soap.getIssue(auth, issuekey)

        #print issue key
        jiraIssue = issue.key+':'+issue.summary+' '+issue.priority+' '+issue.assignee+' Due:'+str(issue.duedate[0:3])
        print jiraIssue
        testContent = testContent.replace(issuekey, jiraIssue)

  # get query
  jiralists = dom.getElementsByTagName('jiralist')
  for jiralist in jiralists:
    print 'node name: '+jiralist.nodeName
    nodes = jiralist.childNodes
    for node in nodes:
      if node.nodeType == node.TEXT_NODE:
        print 'node data: '+node.data
        query = node.data

        issues = soap.getIssuesFromJqlSearch(auth, query, 3)
        #print issues
        #cf = soap.getCustomFields(auth)
        #print cf

        format = '%3s %6s %11s %-20s %2s %2s %15s %2s %8s %10s'
        jiraIssueList = ' No    Key         WBS          Summary      S Pri    Duedate   % R  Assignee\n'
        issueNum = 0

        for issue in issues:
          customFields = issue.customFieldValues
          issueNum = issueNum + 1
          no = str(issueNum)
          key = issue.key
          wbs = 'wbs'
          summary = issue.summary
          status = issue.status
          priority = issue.priority
          duedate = issue.duedate[0:3]
          #progress = issue.progress
          resolution = issue.resolution
          assignee = issue.assignee

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

        testContent = testContent.replace(query, jiraIssueList)

  print 'updated content: '+testContent
  print 'Content updated.'

  return content

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
gmail = file.read()
file.close()

# read google password from file
file = open('gpasswd','r')
gpasswd = file.read()
file.close()

client.ClientLogin(gmail, gpasswd, client.source, 'writely')


#createDoc('file-edit')
#downloadDoc('file-edit')
content = getContentFromFile('file-edit.tmp')
content = updateContent(content) # this is test
#writeContent(content, 'file-view')
#uploadDoc('file-view')
