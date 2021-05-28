class HeaderException(Exception):
    pass


class UnknownVersionException(Exception):
    pass


class ContentIsNotLoaded(Exception):
    pass


class NotEnoughChunkContent(Exception):
    pass


class ContentNotEmpty(Exception):
    pass


class ParserException(Exception):
    pass


class UnknownChunkType(Exception):
    pass