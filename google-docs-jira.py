#!/usr/bin/python

import platform
import sys

# check Python version before run
version = platform.python_version()
if int(version.replace('.','')) < 270:
  print 'Current Python version: '+version
  sys.exit('You need Python version 2.7.0 or later to run this script.')

import gdata.docs.data
import gdata.docs.client
import SOAPpy
import re
from xml.dom.minidom import parseString
import argparse
import os
import json


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

  print 'Document \'%s\' uploaded.' % path

### download
## documentId: google document id
## f_ext: file extension
def download(documentId, f_ext):
  entry = client.GetDoc(documentId)

  # download with tmp extension
  #client.Download(entry, file_path='%s' % os.path.abspath(entry.title.text)+f_ext)

  file_path = '%s' % os.path.abspath(entry.title.text) + f_ext
  client.Export(entry, file_path)

  print 'Document \'%s\' downloaded as \'%s\'.' % (entry.title.text, entry.title.text+f_ext)

### get document id by given doc title
## title: file name on the Google Docs server.
## this may need to be changed. e.g.> multiple files can have the same name.
def getDocumentId(title):
  feed = client.GetDocList()
  for entry in feed.entry:
    if entry.title.text.encode('UTF-8') == title and entry.GetDocumentType() == 'document':
      return entry.resource_id.text
  return None

### download document by title (file name)
def downloadDoc(title, f_ext):
  documentId = getDocumentId(title)

  if documentId == None:
    sys.exit('File \''+title+'\' does not exists.')

  download(documentId, f_ext)

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
  whitespace = '&nbsp;'
  rdquote = '&rdquo;'
  ldquote = '&ldquo;'

  # replace html entity
  str = str.replace(lt,'<')
  str = str.replace(gt,'>')
  str = str.replace(whitespace,'')
  str = str.replace(ldquote,'\"')
  str = str.replace(rdquote,'\"')

  return str

### get jira key from text contents (jiratree tag)
def getKeyIssueListForJiratreeTag(string):
  rootList = []

  jiraKeyMatchObjs = re.findall(r'&lt;jiratree&gt;FG-\d*&lt;/jiratree&gt;', string)

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
          rootList.append(issuekey.strip())

  return rootList

### get jira key from text contents (jira tag)
def getKeyIssueListForJiraTag(string):
  keyList = []

  jiraMatchObjs = re.findall(r'&lt;jira&gt;FG-\d*&lt;/jira&gt;', string)

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
          keyList.append(issuekey.strip())

  return keyList

### get jira query from text contents
def getQueryListForJiralistTag(string):
  queryList = []
  fieldsList = []
  jiralistMatchObjs = re.findall(r'&lt;jiralist.*?&gt;.*?&lt;/jiralist&gt;', string)

  for match in jiralistMatchObjs:
    match = re.sub(r'<.*?>', '', match)
    match = replaceHtmlEntity(match)

    dom = parseString(match)
    jiralists = dom.getElementsByTagName('jiralist')
    for jiralist in jiralists:
      # get fields
      if jiralist.hasAttribute('fields'):
        fields = jiralist.getAttribute('fields')
        fieldsList.append(fields.strip())
      else:
        fieldsList.append('')
      # get query
      nodes = jiralist.childNodes
      for node in nodes:
        if node.nodeType == node.TEXT_NODE:
          query = node.data
          queryList.append(query.strip())

  jiraQueryFieldsList = [queryList, fieldsList]

  return jiraQueryFieldsList

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
    jiraIssue = issue.key+': '+issue.summary+' '+priority+' '+issue.assignee+' Due:'+duedate

  return jiraIssue

### make tree display format
def makeTreeOutput(root, depth, indentChar, leaves, levels, priorities, info, soap, auth, link, listItem):
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

  levelseq = []
  levelstack = []
  while len(stack) > 0:
    node = stack.pop()
    wbsNum = 0
    wbsHead = ''

    if levels.has_key(node.key):
      level = levels[node.key]

      # format unordered list items based on tree level
      if listItem == True:
        levelseq.append(level)
        size = len(levelseq)
        diff = 0
        if len(levelseq) > 1:
          diff = levelseq[size-1] - levelseq[size-2]
        if diff == 1:
          levelstack.append(level)
          output = output + '<ul>'
        elif diff < 0:
          i = diff
          while i < 0:
            levelstack.pop()
            output = output + '</ul>'
            i = i+1
      
      # format issue data
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
      
      # set different color based on Phase
      if p1color != '' and len(phases) == 1 and phases[0].name == 'Phase-I':
        if listItem == True:
          output = output + '<li>' + wbsHead + '<span style=\"background-color:' + p1color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span></li><br />'
        else:
          output = output + indch[level] + wbsHead + '<span style=\"background-color:' + p1color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span><br />'
      elif (p2color!='' and len(phases)==1 and phases[0].name=='Phase-II') or (len(phases)==2 and (phases[0].name=='Phase-II' or phases[1].name=='Phase-II')):
        if listItem == True:
          output = output + '<li>' + wbsHead + '<span style=\"background-color:' + p2color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span></li><br />'
        else:
          output = output + indch[level] + wbsHead + '<span style=\"background-color:' + p2color + '\">' + formatIssue(node, priorities, info, soap, auth, link) + '</span><br />'
      else:
        if listItem == True:
          output = output + '<li>' + wbsHead + formatIssue(node, priorities, info, soap, auth, link) + '</li><br />'
        else:
          output = output + indch[level] + wbsHead + formatIssue(node, priorities, info, soap, auth, link) + '<br />'
      children = leaves[node.key]
      if len(children) != 0:
        children.reverse()
        stack.extend(children)
  if listItem == True:
    while len(levelstack) > 0:
      levelstack.pop()
      output = output + '</ul>'

  return output

### inject data
def updateContents(accountInfo, contents, linkOption, fontsize, listItem):
  # soap authentication
  soap = SOAPpy.WSDL.Proxy('http://jira.futuregrid.org/rpc/soap/jirasoapservice-v2?wsdl')

  auth = soap.login(accountInfo['jira_usrname'], accountInfo['jira_passwd'])
  info = soap.getServerInfo(auth)
  resolutions = soap.getResolutions(auth)
  statuses = soap.getStatuses(auth)
  priorities = soap.getPriorities(auth)

  # get keys and queries
  keys = getKeyIssueListForJiraTag(contents)
  queriesWithFields = getQueryListForJiralistTag(contents)
  queries = queriesWithFields[0]
  fieldsList = queriesWithFields[1]
  roots = getKeyIssueListForJiratreeTag(contents)

  # insert key issue data
  for issuekey in keys:
    issue = soap.getIssue(auth, issuekey)

    jiraIssue = formatIssue(issue, priorities, info, soap, auth, linkOption)

    contents = contents.replace(issuekey, jiraIssue)

  # insert query data
  if len(queries) != len(fieldsList): # query : fields attr should be 1:1
    sys.exit('error')

  listSize = len(queries)
  i = 0
  while i < listSize:
    query = queries[i]
    fields = fieldsList[i]
    fieldValues = []

    issues = soap.getIssuesFromJqlSearch(auth, query, 5)

    # format table columns based on fields attribute
    tableFormat = "<table border='1' cellspacing='0'><tr><th>No.</th>"
    if len(fields) > 0:
      # get field values
      tmpList = fields.split(',')
      for tmp in tmpList:
        value = tmp.strip().title()
        if value == 'Wbs':
          value = 'WBS'
        fieldValues.append(value)
        tableFormat = tableFormat + '<th>' + value + '</th>'
    else:
      tableFormat = tableFormat + "<th>Key</th><th>WBS</th><th>Summary</th><th>Status</th><th>Pri</th><th>Duedate</th><th>Prog.%</th><th>Res</th><th>Assignee</th>"
    tableFormat = tableFormat + "</tr>"

    jiraIssueList = tableFormat

    # get data
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
        duedate = str(issue.duedate[0:3])
      resolution = 'UNRESOLVED'
      if issue.resolution != None:
        res = findId(resolutions, issue.resolution)
        if res != None:
          resolution = res.name
      assignee = '-'
      if issue.assignee != None:
        assignee = soap.getUser(auth, issue.assignee)

      keyColumn = ''
      if linkOption == True:
        keyColumn = '<td><a href=\"'+info.baseUrl+'/browse/'+key+'\">'+key+'</a></td>'
      else:
        keyColumn = '<td>' + key + '</td>'

      # fill table based on fields attribute
      if len(fields) > 0:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td>'
        for fvalue in fieldValues:
          if fvalue.lower() == 'key':
            jiraIssueList = jiraIssueList + keyColumn
          elif fvalue.lower() == 'wbs':
            jiraIssueList = jiraIssueList + '<td>' + wbs + '</td>'
          elif fvalue.lower() == 'summary':
            jiraIssueList = jiraIssueList + '<td>' + summary + '</td>'
          elif fvalue.lower() == 'status':
            jiraIssueList = jiraIssueList + '<td>' + status + '</td>'
          elif fvalue.lower() == 'pri' or fvalue.lower() == 'priority':
            jiraIssueList = jiraIssueList + '<td>' + priority + '</td>'
          elif fvalue.lower() == 'duedate':
            jiraIssueList = jiraIssueList + '<td>' + duedate + '</td>'
          elif fvalue.lower() == 'prog' or fvalue.lower() == 'progress':
            jiraIssueList = jiraIssueList + '<td>' + progress + '</td>'
          elif fvalue.lower() == 'res' or fvalue.lower() == 'resolution':
            jiraIssueList = jiraIssueList + '<td>' + resolution + '</td>'
          elif fvalue.lower() == 'assignee':
            jiraIssueList = jiraIssueList + '<td>' + assignee.fullname + '</td>'
        jiraIssueList = jiraIssueList + '</tr>'
      else:
        jiraIssueList = jiraIssueList + '<tr><td>'+no+'</td>'+keyColumn+'<td>'+wbs+'</td><td>'+summary+'</td><td>'+status+'</td><td>'+priority+'</td><td>'+duedate+'</td><td>'+progress+'</td><td>'+resolution+'</td><td>'+assignee.fullname+'</td></tr>'

    jiraIssueList = jiraIssueList + '</table>'

    contents = contents.replace(query, jiraIssueList)
    i = i + 1

  # tree display
  for rootKey in roots:
    leaves = {}
    levels = {}
    indentChar = '&nbsp;&nbsp;&nbsp;'
    depth = 99

    root = soap.getIssue(auth, rootKey)
    
    buildTree(root, depth, soap, auth, leaves, levels)
    tree = makeTreeOutput(root, depth, indentChar, leaves, levels, priorities, info, soap, auth, linkOption, listItem)
    contents = contents.replace(rootKey, tree)

  # remove tags
  contents = re.sub(r'&lt;jira&gt;|&lt;/jira&gt;|&lt;jiralist.*?&gt;|&lt;/jiralist&gt;|&lt;jiratree&gt;|&lt;/jiratree&gt;', '', contents)

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
  fpath = os.path.abspath(file)
  upload(fpath, file, folderName)

### delete file
def delete(file):
  fpath = os.path.abspath(file)
  os.remove(fpath)
  print 'File \'%s\' removed.' % fpath

## delete document
def deleteDoc(title):
  documentId = getDocumentId(title)

  if documentId == None:
    sys.exit('No \''+title+'\' is found.')

  entry = client.GetDoc(documentId)
  rm_doc = entry.title.text
  client.Delete(entry.GetEditLink().href + '?delete=true', force=True)

  print 'Document \'' + rm_doc + '\' removed.'

### copy document
def copy(source, destination):
  doc_id = getDocumentId(source)
  doc_entry = client.GetDoc(doc_id)
  copied_title = destination

  print 'Copying \''+doc_entry.title.text + '\' to \'' + copied_title + '\''
  client.Copy(doc_entry, copied_title)

### move document to folder
def move(source, dest_folder):
  dest_folder_entry = None
  feed = client.GetDocList(uri='/feeds/default/private/full/-/folder')

  for f in feed.entry:
    if f.title.text == dest_folder:
      dest_folder_entry = client.GetDoc(f.resource_id.text)

  # create a folder if the destination folder does not exist
  if dest_folder_entry == None and dest_folder != None:
    dest_folder_entry = client.Create(gdata.docs.data.FOLDER_LABEL, dest_folder)

  src_entry = client.GetDoc(getDocumentId(source))
  print 'Moving \'' + src_entry.title.text + '\' to folder ' + dest_folder_entry.title.text
  client.Move(src_entry, dest_folder_entry)

### get google and jira account information from a file (json format)
def getAccountInfo():
  file = open('jirabridge','r')
  jsonFormatData = file.read()
  file.close()

  return json.loads(jsonFormatData)


### main ###

# create parser
parser = argparse.ArgumentParser()

parser.add_argument('-l', '--link', action='store_true', default=False, dest='link', help='add a link to JIRA Key value')
parser.add_argument('-d', '--document', action='store', dest='docname', help='specify a document name to download')
parser.add_argument('-f', '--folder', action='store', dest='srcfolder', help='specify a folder to update all documents in it')
parser.add_argument('-s', '--font-size', action='store', dest='fontsize', type=int, help='set font size')
parser.add_argument('-ul', '--unordered-list', action='store_true', default=False, dest='useli', help='use unordered list in tree view')
parser.add_argument('-t', '--to-folder', action='store', dest='destfolder', help='specify a folder to upload documents')

# parse
options = parser.parse_args()
#print options
linkOption = options.link
doc_name = options.docname
src_folder = options.srcfolder
dest_folder = options.destfolder
font_size = options.fontsize
li = options.useli

if (src_folder != None and doc_name != None):
  sys.exit('Error: option \'-d, --document\' and \'-f, --folder\' cannot be set together.')

# establish connection
client = gdata.docs.client.DocsClient(source='fg-issue-v1')
client.ssl = True  # force to use HTTPS for all API requests
client.http_client.debug = False  # option for HTTP requests debugging

# read google and jira account information
accountInfo = getAccountInfo()

client.ClientLogin(accountInfo['gmail'], accountInfo['gpasswd'], client.source, 'writely')

# get list of documents to update
docList = []
if src_folder != None:
  feed = client.GetDocList(uri='/feeds/default/private/full/-/folder')

  for entry in feed.entry:
    if entry.title.text == src_folder:
      f = client.GetDocList(entry.content.src)
      for doc in f.entry:
        docList.append(doc.title.text)
elif doc_name != None:
  docList.append(doc_name)

file_ext = '.tmp'

for document in docList:
  downloadDoc(document, file_ext)
  content = getContentsFromFile(document+file_ext)
  content = updateContents(accountInfo, content, linkOption, font_size, li)
  delete(document+file_ext) # remove temporary file

  # edit document title before upload
  document = document.replace('-edit','')
  if linkOption == True:
    document = document + '-link'
  if font_size != None:
    document = document + '-'+str(font_size)+'ft'
  if li == True:
    document = document + '-ul'

  writeContent(content, document)
  uploadDoc(document, dest_folder)
  copy(document, document+'-view') # this changes sharing permission to 'not shared.'
  if dest_folder != None:
    move(document+'-view', dest_folder)
  delete(document) # clean up file
  deleteDoc(document)
