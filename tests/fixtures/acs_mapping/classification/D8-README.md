The three `.gz` originals listed in `d8-originals.provenance.json` are lossless,
complete public files captured for the owner-approved Stage 8 D8 assertion rule.
Each record binds the compressed and decompressed SHA-256, original byte size and
the public acquisition citation. Compression uses gzip mtime 0. Tests decompress
these tracked files into isolated temporary paths and never read production data.
The other supporting full originals (Census 2018, PUMS 2018 and the current paired
XLS) are already tracked here and pinned in `provenance.json`.
