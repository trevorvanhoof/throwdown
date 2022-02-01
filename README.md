# Throwdown

Taking the fight to the establishment.

### Wat?
I wanted a simple markdown interpreter in python and/or javascript to output html for my website. Python does not have a bug-free official distribution, javascript only has things you install through npm and I don't want to have anything to do with node and the 100 MB of dependencies you end up uploading to your FTP server in order to do the most basic tasks.

So writing my own parser it is then eh? I tried to trudge through the commonmark markdown spec and had a heart attack at the complexity. 24722 words and 181 pages of complicated language explaining features I absolutely don't need.

I just want minimal, well defined, syntactical elements with maximum payoff, so here is **throwdown**. Taking the fight to the establishment to have a stupidly minimal markup language in both definition and capability.

### Goals
Keep it a subset for markdown so we can use existing IDEs & plugins.
Support HTML tags in line with text.
Write a well defined  language spec in the manual to ease creating new interpreters for it.

### The spec

#### Tokenization
Given a piece of text we tokenize the following concepts (these are regular expressions using DOTALL and MULTILINE modifiers):
```
blank_line(s): (\r | \n | \r\n){2,}
html tag: <.*?>
code: ```.*?```
unescaped italic: ^_|(?<!\\)_
unescaped bold: ^\*|(?<!\\)\*
heading: ^#+[ ]
```
any characters inbetween matching tokens are flagged _content_.

Content itself gets an additional treatment where we replace this regex
```
\\(?)
```
for escaped characters, with whatever was in the matched group.
I currently do this in the generation stage but it could move to any stage.

I am not sure if in the UTF8 2/3/4 byte characters any of these elements may match, so make sure to perform these single-characetr checks per unicode char, not per byte.

#### Parsing
We then have a parsing pass that tries to group matching tokens:

In this example:
```
This *word* is bold but this* is wrong.
```
We have the following tokens:
```
content, bold, content, bold, content, bold, content
```
The parser simply finds any content block surrounded by matching code|italic|bold neighbours, and then 'consumes' these neighbours so they can not be picked up more than once.
Reading from left to right this means we get (note we search outwards from content recursively to support `*_content_*` notations, instead of holding on to the boundary tokens as soon as we encounter them):
```
content group content bold content
```
Then, any token outside of a group gets merged into it's content, any consecutive content gets merged into 1 content. The first step reduced the bold into it's left neighbour:
```
content group content content
```
The next step reduces the two content blocks into one:
```
content group content
```
The above step should include html tags.

A final step is to remove the blank line tokens, but first we must make sure to merge consecutive group and content blocks,
because after this any consecutive content and/or group tokens are known unique paragraphs (or headers) so the blank 
lines are no longer necessary to imply this separation.

#### Generation
Then there is the generation step. We simply walk the resulting tokens and output a html document.
- If a `content` group is preceded by a `heading`, the node gets wrapped into &lt;hn&gt; tags where n is the number of #.
- Every other `content` node gets wrapped into &lt;p&gt; tags.
- Every `group` gets wrapped based on the first and last tokens (which are identical).
  - italic becomes &lt;i&gt; In this case the wrapping is recursive, a bold group in an intalic group may exist. 
  - bold becomes &lt;b&gt;  In this case the wrapping is recursive, an italic group in a bold group may exist.
  - code becomes &lt;code&gt;

Write &lt;br/&gt; to insert single line breaks manually.

### TODO:

Consider bullet points and numbered lists, though the html is not super invasive.