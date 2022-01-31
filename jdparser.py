import re

MULTIPLE_NEWLINES = re.compile(r'(\r|\n|\r\n){2,}')
CODE = re.compile(r'`')
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

        # this content token is obunded by 2 identical tokens of a valid id
        a, b = tokens[index - 1][2], tokens[index + 1][2]
        if a == b and a in (2, 3, 4):
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

        if tokens[index][2] in (2, 3, 4, 0, -1):  # TODO: have a nicer way to identify code/italic/bold/content
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

    # ditch new line tokens
    tokens = [token for token in tokens if token[2] != 1]

    return tokens


def generateGroupHtml(groupedTokens):
    assert len(groupedTokens) == 3, 'Groups must always have length 3: open tag, content, close tag'
    assert groupedTokens[0][2] == groupedTokens[2][2], 'Groups must start and end with the same boundary token type'
    assert groupedTokens[0][2] in (2, 3, 4), 'Groups must be bounded by code, italic or bold and nothing else'
    # TODO: Code inside italic or bold tags makes no sense and we should assert against it
    tag = {2: 'code', 3: 'i', 4: 'b'}[groupedTokens[0][2]]
    if isinstance(groupedTokens[1][0], tuple):
        html = generateGroupHtml(groupedTokens[1])
    else:
        assert groupedTokens[1][2] == -1, 'We can only have groups or plain text at the center of groups'
        html = text[groupedTokens[1][0]:groupedTokens[1][1]]
    return f'<{tag}>{html}</{tag}>'


def generateHtml(text, tokens):
    index = 0
    count = len(tokens)
    code = []
    while index < count:
        token = tokens[index]
        if token[2] == 5:
            if index + 1 == count: break  # don't generate empty heading tag at tail of document and early out
            # heading replaces paragraph
            nextToken = tokens[index + 1]
            bGroup = isinstance(nextToken[0], tuple)
            assert nextToken[2] == -1 or bGroup, 'Expected "content" or "group" token after "header" token.'
            if bGroup:
                html = generateGroupHtml(nextToken)
            else:
                assert nextToken[2] == -1, 'parser output invalid token %s' % token
                html = text[nextToken[0]:nextToken[1]]
            tag = f'h{(token.count("#") + 1)}'
            code.append(f'<{tag}>{html}</{tag}>')
            index += 1
        else:
            if isinstance(token[0], tuple):
                html = generateGroupHtml(token)
            else:
                assert token[2] == -1, 'parser output invalid token %s' % token
                html = text[token[0]:token[1]]
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
# text = '# hello\n\n*_test_*\n\nHello this <br/> is a * star\n\n# '
# print(generateHtml(text, parse(tokenize(text))))
