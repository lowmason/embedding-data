'''Decode OSHA ITA CSV lines that mix UTF-8 and Windows-1252 bytes.

Most non-ASCII text in the ITA files is Windows-1252, a few rows are UTF-8, and one line
can hold both. Each line is decoded as UTF-8, and only the bytes UTF-8 rejects are decoded
as Windows-1252; its five undefined bytes still raise.
'''

import codecs

def cp1252_fallback(error: UnicodeDecodeError) -> tuple[str, int]:
    '''Decode only the bytes UTF-8 rejected as Windows-1252; its five undefined bytes raise.'''
    return error.object[error.start:error.end].decode('cp1252'), error.end


codecs.register_error('osha-cp1252-fallback', cp1252_fallback)


def decode_line(raw: bytes) -> str:
    '''Decode one raw CSV line that may mix UTF-8 and Windows-1252 bytes.'''
    return raw.decode('utf-8', errors='osha-cp1252-fallback')
