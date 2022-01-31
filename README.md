# jackdown
Who is mark?

### Wat?

I tried to trudge through the markdown spec and had a heart attack at the complexity.
I don't need a rich featureset, I just want minimal, well defined, syntactical elements with maximum payoff .

### The spec

TODO: I realized it is difficult to write non bold text between star characters, should we allow escape characters, and if so, how?
TODO: Do we care about URLs, images and tables? How will we implement those? Maybe HTML is not the worst here?

#### Tokenization
Given a piece of text we tokenize the following concepts:
```
blank_line(s): (\r | \n | \r\n){2,}
html tag: <.*?>
code: `
italic: _
bold: *
heading: ^#+[ ]
```
anything else is added to a running total "content block".

I am not sure if in the UTF8 2/3/4 byte characters any of these elements may match, so make sure to perform these single-characetr checks per unicode char, not per byte.

#### Parsing
We then have a parsing pass that tries to group matching tokens:

In this example:
```This *word* is bold but this* is wrong.```
We have the following tokens:
```content, bold, content, bold, content, bold, content```
The parser simply finds any content block surrounded by matching code|italic|bold neighbours, and then 'consumes' these neighbours so they can not be picked up more than once.
Reading from left to right this means we get (note we search outwards from content recursively to support `*_content_*` notations, instead of holding on to the boundary tokens as soon as we encounter them):
```content group content bold content```
Then, any token outside of a group gets merged into it's content, any consecutive content gets merged into 1 content. The first step reduced the bold into it's left neighbour:
```content group content content```
The next step reduces the two content blocks into one:
```content group content```
The above step shoiuld include html tags.

A final step is to remove the blank line tokens, because after this any consecutive content and/or group tokens are known unique paragraphs (or headers) so the blank lines are no longer necessary to imply this separation. 

#### Generation
Then there is the generation step. We simply walk the resulting tokens and output a html document.
- If a `content` group is preceded by a `heading`, the node gets wrapped into &lt;hn&gt; tags where n is the number of #.
- Every other `content` node gets wrapped into &lt;p&gt; tags.
- Every `group` gets wrapped based on the first and last tokens (which are identical).
  - italic becomes &lt;i&gt; In this case the wrapping is recursive, a bold group in an intalic group may exist. 
  - bold becomes &lt;b&gt;  In this case the wrapping is recursive, an italic group in a bold group may exist.
  - code becomes &lt;code&gt;

Write &lt;br/&gt; to insert single line breaks manually.
