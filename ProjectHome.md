The purpose of this project is to take a google docs document called `<file>-edit` and replace all occurrences of jira tags with contents directly fetched from a jira server. This can than be used to augment the document. The modified document is than uploaded with writing disabled as `<file>`.

The supported tags are
`<jira>PRJ-#</jira>`

resulting in a single summary line about the issue, and

`<jiralist>query</jiralist>`

resulting in a table listing matching jira issues from the query. The query is not just a simple query.

The project home page is https://sites.google.com/site/jiradocsbridge/