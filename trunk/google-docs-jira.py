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
def download(resourceid, f_ext):
  #print resourceid
  entry = client.GetDoc(resourceid)

  # download with tmp extension
  #client.Download(entry, file_path='%s' % entry.title.text+f_ext)

  file_path = '%s' % entry.title.text+f_ext
  client.Export(entry, file_path)

  print 'Document \'%s\' downloaded as \'%s\'.' % (entry.title.text, entry.title.text+f_ext)

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
def downloadDoc(title, f_ext):
  resourceId = getResourceId(title)

  if resourceId == None:
    sys.exit('File \''+title+'\' does not exists.')

  download(resourceId, f_ext)

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

### get jira key from text contents (jiratree tag)
def getKeyIssueListForJiratreeTag(string):
  rootList = []

  jiraKeyMatchObjs = re.findall(r'&lt;jiratree&gt;FG-\d*&lt;/jiratree&gt;', string)

  if jiraKeyMatchObjs:
    for match in jiraKeyMatchObjs:
      match = re.sub(r'<.*?>', '', match)
      match = replaceHtmlEntity(match)

      dom = parseString(match)
      treeRoots = dom.getElementsByTagName('jiratree')
      for rootElement in treeRoots:
        nodes = rootElement.childNodes
        for node in nodes:
          if node.nodeType == node.TEXT_NODE:
            issuekey = node.data
            rootList.append(issuekey)

  return rootList

### get jira key from text contents (jira tag)
def getKeyIssueListForJiraTag(string):
  keyList = []

  jiraMatchObjs = re.findall(r'&lt;jira&gt;FG-\d*&lt;/jira&gt;', string)

  if jiraMatchObjs:
    for match in jiraMatchObjs:
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
def getQueryListForJiralistTag(string):
  queryList = []
  jiralistMatchObjs = re.findall(r'&lt;jiralist&gt;.*?&lt;/jiralist&gt;', string)
  
  if jiralistMatchObjs:
    for match in jiralistMatchObjs:
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

### find correct object by id
def findId(list, id):
  for e in list:
    if e.id == id:
      return e
  return None

### change font size
def changeFontSize(contents, size):
  matchObjs = re.findall(r'font-size:\d*pt', contents);
  contents = re.sub(r'font-size:\d*pt','font-size:'+str(size)+'pt', contents)

  return contents

### build tree
def buildTree(root, depth, soap, auth, leaves, levels):
  visitingNodes = [root]
  tmp = []

  currentDepth = 0
  while currentDepth <= depth:
    visitingNodes.extend(tmp)
    tmp = []
    for node in visitingNodes:
      nodeKey = node.key
      levels[nodeKey] = currentDepth
      children = soap.getIssuesFromJqlSearch(auth, 'issue in linkedissues(\''+nodeKey+'\', \'is parent of\') ORDER BY key ASC', 1000)
      leaves[nodeKey] = children
      tmp.extend(children)
    visitingNodes = []
    currentDepth = currentDepth + 1

### format issue
def formatIssue(issue, priorities, info, soap, auth, link):
  priority = '-'
  if issue.priority != None:
    pri = findId(priorities, issue.priority)
    if pri != None:
      priority = pri.name

  #assignee = '-'
  #if issue.assignee != None:
  #  assignee = soap.getUser(auth, issue.assignee)
  summary = '-'
  if issue.summary != None:
    summary = issue.summary
  duedate = '-'
  if issue.duedate != None:
    duedate = str(issue.duedate[0:3])

  if link == True:
    jiraIssue = '<a href=\"'+info.baseUrl+'/browse/'+issue.key+'\">'+issue.key+'</a>'+': '+summary+' '+priority+' '+issue.assignee+' Due:'+duedate
  else:
    jiraIssue = issue.key+': '+issue.summary+' '+priority+' '+issue.assignee+' Due:'+str(issue.duedate[0:3])

  return jiraIssue

### make tree display format
def makeTreeOutput(root, depth, indentChar, leaves, levels, priorities, info, soap, auth, link):
  stack = [root]
  indch = {0:''}
  p1color = 'orange'
  p2color = 'yellow'
  p3color = ''
  output = ''

  i = 1
  while i <= depth:
    indch[i] = indch[i-1] + indentChar
    i = i + 1

  i = 1
  while i <= depth:
    indch[i] = indch[i] + '&middot;&nbsp;'
    i = i + 1

  while len(stack) > 0:
    node = stack.pop()
    wbsNum = 0
    wbsHead = ''

    if levels.has_key(node.key):
      level = levels[node.key]
      cFields = node.customFieldValues
      isNsfWbs = 0
      for cField in cFields:
        if cField.customfieldId == 'customfield_10040':
          values = cField.values
          if values[0] == 'yes':
            isNsfWbs = 1
        elif cField.customfieldId == 'customfield_10000':
          values = cField.values
          wbsNum = values[0]
      if isNsfWbs != 0:
        wbsHead = str(wbsNum) + '|'
      else:
        wbsHead = ''
      phases = node.affectsVersions

      if p1color != '' and len(phases) == 1 and phases[0].name == 'Phase-I':
        output = output + indch[level] + wbsHead + '<span style=\"background-color:' + p1color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span><br />'
      elif (p2color!='' and len(phases)==1 and phases[0].name=='Phase-II') or (len(phases)==2 and (phases[0].name=='Phase-II' or phases[1].name=='Phase-II')):
        output = output + indch[level] + wbsHead + '<span style=\"background-color:' + p2color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span><br />'
      else:
        output = output + indch[level] + wbsHead + formatIssue(node, priorities, info, soap, auth, link) + '<br />'
      children = leaves[node.key]
      if len(children) != 0:
        children.reverse()
        stack.extend(children)

  return output

### test update content
def updateContent(contents, linkOption, fontsize):
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

  # get keys and queries
  keys = getKeyIssueListForJiraTag(contents)
  queries = getQueryListForJiralistTag(contents)
  roots = getKeyIssueListForJiratreeTag(contents)

  # insert key data
  for issuekey in keys:
    issue = soap.getIssue(auth, issuekey)

    jiraIssue = formatIssue(issue, priorities, info, soap, auth, linkOption)

    contents = contents.replace(issuekey, jiraIssue)

  # insert query data
  for query in queries:
    issues = soap.getIssuesFromJqlSearch(auth, query, 5)

    jiraIssueList = "<table border='1' cellspacing='0'><tr><th>No.</th><th>Key</th><th>WBS</th><th>Summary</th><th>Status</th><th>Pri</th><th>Duedate</th><th>Prog.%</th><th>Res</th><th>Assignee</th></tr>"
    issueNum = 0

    for issue in issues:
      customFields = issue.customFieldValues
      issueNum = issueNum + 1
      no = str(issueNum)
      key = issue.key
      wbs = '-'
      progress = '0'
      for customField in customFields:
        if customField.customfieldId == 'customfield_10000':
          values = customField.values
          wbs = values[0]
        if customField.customfieldId == 'customfield_10006':
          values = customField.values
          progress = values[0]
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
      resolution = 'UNRESOLVED'
      if issue.resolution != None:
        res = findId(resolutions, issue.resolution)
        if res != None:
          resolution = res.name
      assignee = '-'
      if issue.assignee != None:
        assignee = soap.getUser(auth, issue.assignee)

      if linkOption == True:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td><td><a href=\"'+info.baseUrl+'/browse/'+key+'\">'+key+'</a></td><td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td>'+priority+'</td><td>'+str(duedate)+'</td><td>'+progress+'</td><td>'+resolution+'</td><td>'+assignee.fullname+'</td></tr>'
      else:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td><td>'+key+'</a></td><td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td>'+priority+'</td><td>'+str(duedate)+'</td><td>'+progress+'</td><td>'+resolution+'</td><td>'+assignee.fullname+'</td></tr>'

    jiraIssueList = jiraIssueList + '</table>'
    contents = contents.replace(query, jiraIssueList)

  # tree display
  for rootKey in roots:
    leaves = {}
    levels = {}
    indentChar = '&nbsp;&nbsp;&nbsp;'
    depth = 99

    root = soap.getIssue(auth, rootKey)
    
    buildTree(root, depth, soap, auth, leaves, levels)
    tree = makeTreeOutput(root, depth, indentChar, leaves, levels, priorities, info, soap, auth, linkOption)
    contents = contents.replace(rootKey, tree)

  # remove tags
  contents = re.sub(r'&lt;jira&gt;|&lt;/jira&gt;|&lt;jiralist&gt;|&lt;/jiralist&gt;|&lt;jiratree&gt;|&lt;/jiratree&gt;', '', contents)

  # change font size
  if fontsize != None:
    contents = changeFontSize(contents, fontsize)

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

# create parser
parser = argparse.ArgumentParser()
parser.add_argument('-l', '--link', action='store_true', default=False, dest='link', help='add a link to JIRA Key value')
parser.add_argument('-f', '--filename', action='store', dest='filename', help='specify a file name to download')
parser.add_argument('-d', '--directory', action='store', default='GoogleDocsJira', dest='folder', help='specify folder to upload a file')
parser.add_argument('-s', '--fontsize', action='store', dest='fontsize', type=int, help='set font size')

options = parser.parse_args()
#print options
linkOption = options.link
file_name = options.filename
folder = options.folder
font_size = options.fontsize

if file_name == None:
  parser.print_help()
  sys.exit('Please specify file name with option \'-f\'.')

# establish connection
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
'''
feed = client.GetDocList(uri='/feeds/default/private/full/-/document')
# get resource id by title (file name)
acl_feed = client.GetAclPermissions(feed.entry[0].resource_id.text)
# change acl_feed permission to reader ac.role.value = 'reader'
# update updated_acl = client.Update(acl_entry)
print feed.entry[0].resource_id.text, feed.entry[0].title.text
for acl in acl_feed.entry:
  print '%s (%s) is %s' % (acl.scope.value, acl.scope.type, acl.role.value)

###createDoc('file-edit') ## not used
'''
file_ext = '.tmp'

downloadDoc(file_name, file_ext)
content = getContentsFromFile(file_name+file_ext)
content = updateContent(content, linkOption, font_size)

file_name = file_name.replace('-edit','')
if linkOption == True:
  file_name = file_name + '-link'
if font_size != None:
  file_name = file_name + '-'+str(font_size)+'ft'
file_name = file_name + '-view'

writeContent(content, file_name)
uploadDoc(file_name, folder)
