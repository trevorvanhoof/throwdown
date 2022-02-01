"""
This is an example implementation that I apply to my personal use cases and I hope that that provides enough coverage.
"""

"""
In lieu of this, I have added the pygments syntax highlighter to expand upon the definition of code (`-bounded) segments,
the first line of such a segment may be a language name (and will be discarded if valid) resulting in syntax highlighted
HTML being written instead of a <code> block opposing the official spec.
"""
USE_PYGMENTS = True

if USE_PYGMENTS:
    from pygments import highlight
    from pygments.lexers import *
    from pygments.lexers import LEXERS
    from pygments.formatters import HtmlFormatter

import re

MULTIPLE_NEWLINES = re.compile(r'(\r|\n|\r\n){2,}')
CODE = re.compile(r'`[^`]*`')
ITALIC = re.compile(r'_')
BOLD = re.compile(r'\*')
HEADING = re.compile(r'^#+ ', re.MULTILINE)
TAG = re.compile(r'<.*?>', re.DOTALL)
ORDERED_TOKENS = [
    TAG,  # HTML tags have priorities so we don't accidentally parse stuff inside the tag attributes
    MULTIPLE_NEWLINES,
    CODE,
    ITALIC,
    BOLD,
    HEADING,
]


def nxt(itr):
    for e in itr: return e
    return None


def tokenize(text):
    cursor = 0

    # this is a list of tuples: token start, token end, token ID (index in ORDERED_TOKENS or -1 if inbetween valid tokens)
    tokens = []

    while True:
        # find best token after the cursor
        bestMatch = None
        bestMatchId = -1
        for index, token in enumerate(ORDERED_TOKENS):
            match = nxt(token.finditer(text, cursor))
            if not match:
                continue
            if bestMatch is None:
                bestMatch = match
                bestMatchId = index
            elif match.start() < bestMatch.start():
                bestMatch = match
                bestMatchId = index
        if not bestMatch:  # done, append unknown token for tail if there is data left
            if cursor != len(text):
                tokens.append((cursor, len(text), -1))
            break
        if cursor != bestMatch.start():
            tokens.append((cursor, bestMatch.start(), -1))
        tokens.append((bestMatch.start(), bestMatch.end(), bestMatchId))
        cursor = bestMatch.end()

    return tokens


def parse(tokens):
    # group bounded tokens
    index = 1
    while index < len(tokens) - 1:  # we only care about bounded content tokens, so we can ignore the first and last tokens
        token = tokens[index]

        # only consider content tokens
        bContent = isinstance(token[0], tuple) or token[2] == -1
        if not bContent:
            index += 1
            continue

        # this content token is bounded by 2 identical tokens of a valid id
        a, b = tokens[index - 1][2], tokens[index + 1][2]
        if a == b and a in (3, 4):
            # group
            tokens[index - 1] = tuple(tokens[index - 1:index + 2])
            tokens.pop(index)
            tokens.pop(index)
            # focus back on this content to allow recursion
            index -= 1
        else:
            # only advance if we didn't group
            index += 1

    # consolidate floating tokens
    index = 0
    count = len(tokens)
    while index < count:
        token = tokens[index]

        if tokens[index][2] in (3, 4, 0, -1):  # TODO: have a nicer way to identify code/italic/bold/content
            # merge left if possible (there is a content element on the left)
            if index:
                if tokens[index - 1][2] == -1:
                    tokens[index - 1] = tokens[index - 1][0], tokens[index][1], -1
                    tokens.pop(index)
                    count -= 1
                    continue
            # if we could not merge, convert to content otherwise so the next element can merge left into this
            tokens[index] = tokens[index][0], tokens[index][1], -1

        index += 1

    # join adjacent groups and content into a new type of group; since we used tuples before we just use lists now
    index = 0
    count = len(tokens)

    start = None
    while index < count:
        token = tokens[index]

        bGroup = isinstance(token[0], tuple)
        bContent = token[2] in (-1, 4)
        if start is None:
            if bGroup or bContent:
                start = index
        else:
            if not (bGroup or bContent):
                # end of run, combine
                if index - start > 1:
                    tokens[start] = list(tokens[start:index])
                    index -= 1
                    while index > start:
                        tokens.pop(index)
                        index -= 1
                        count -= 1
                start = None

        index += 1

    # ditch new line tokens
    tokens2 = []
    for token in tokens:
        if isinstance(token, tuple) and token[2] == 1:
            continue
        tokens2.append(token)
    return tokens2


def generateGroupHtml(text, groupedTokens):
    assert len(groupedTokens) == 3, 'Groups must always have length 3: open tag, content, close tag'
    assert groupedTokens[0][2] == groupedTokens[2][2], 'Groups must start and end with the same boundary token type'
    assert groupedTokens[0][2] in (2, 3, 4), 'Groups must be bounded by code, italic or bold and nothing else'
    # TODO: Code inside italic or bold tags makes no sense and we should assert against it
    tag = {3: 'i', 4: 'b'}[groupedTokens[0][2]]
    if isinstance(groupedTokens[1][0], tuple):
        html = generateGroupHtml(text, groupedTokens[1])
    else:
        assert groupedTokens[1][2] == -1, 'We can only have groups or plain text at the center of groups'
        html = text[groupedTokens[1][0]:groupedTokens[1][1]]
    return f'<{tag}>{html}</{tag}>'


def generateContentHtml(text, token):
    if isinstance(token, list):
        return ''.join(generateContentHtml(text, subToken) for subToken in token)

    if isinstance(token[0], tuple):
        return generateGroupHtml(text, token)

    assert token[2] == -1, 'parser output invalid token ' + str(token)
    return text[token[0]:token[1]]


def generateHtml(text, tokens):
    index = 0
    count = len(tokens)
    code = []

    while index < count:
        token = tokens[index]
        if isinstance(token, list):
            html = generateContentHtml(text, token)
            tag = 'p'
            code.append(f'<{tag}>{html}</{tag}>')
        elif token[2] == 5:
            if index + 1 == count: break  # don't generate empty heading tag at tail of document and early out
            # heading replaces paragraph
            nextToken = tokens[index + 1]
            bGroup = isinstance(nextToken[0], tuple)
            assert nextToken[2] == -1 or bGroup, 'Expected "content" or "group" token after "header" token.'
            if bGroup:
                html = generateContentHtml(text, nextToken)
            else:
                assert nextToken[2] == -1, 'parser output invalid token %s' % token
                html = text[nextToken[0]:nextToken[1]]
            tag = f'h{(token.count("#") + 1)}'
            code.append(f'<{tag}>{html}</{tag}>')
            index += 1
        elif token[2] == 2:
            # + 1 & -1 are to strip the ` tokens
            html = text[token[0] + 1:token[1] - 1]
            if USE_PYGMENTS:
                # inject syntax highlighting
                firstLine = html.split('\n', 1)[0].split('\r', 1)[0]
                if firstLine + 'Lexer' in LEXERS:
                    lexer = find_lexer_class(firstLine)()
                    html = highlight(html[len(firstLine):], lexer, HtmlFormatter())
                else:
                    html = f'<code>{html}</code>'
            else:
                html = f'<code>{html}</code>'
            code.append(html)
        else:
            html = generateContentHtml(text, token)
            tag = 'p'
            code.append(f'<{tag}>{html}</{tag}>')
        index += 1
    return code


def convert(inPath, outPath):
    with open(inPath, 'r') as fh:
        text = fh.read()
    with open(outPath, 'w') as fh:
        for ln in generateHtml(text, parse(tokenize(text))):
            fh.write(ln)

# Demo:
# text = '# hello\n\n`*_test_*`\n\nHello *_this_* <br/> is a * star\n\n# '
# print(generateHtml(text, parse(tokenize(text))))
