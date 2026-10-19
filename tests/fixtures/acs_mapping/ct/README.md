These are public Census and CT OPM originals captured for the approved Stage 8 D9
route. `provenance.json` records original URL/time/size/hash, fixture hash, lossless
gzip hash and exact transformation. Tests verify both compressed and fixture bytes
before reading isolated temporary files; production data and ignored diagnostic
folders are never runtime test inputs.

Six files are complete lossless public originals. The TIGER ZIP fixture retains all
seven original member names and complete original DBF, CPG, PRJ and XML members.
Only unused SHP/SHX geometry bodies are truncated to their first 100 original bytes;
the ZIP is regenerated with stored compression. This preserves all 49,926 original
population/code records and the exact 17-field DBF physical schema while avoiding
unused geometry. Its fixture SHA differs explicitly from the production ZIP SHA.
Fixture registry pinning uses the actual fixture hash; production registry pinning
continues to require the complete official archive's approved SHA.

The TIGER gzip stream is byte-split into two files below the repository's 1,000 KiB
added-file limit. Tests authenticate each part and the concatenated gzip stream
before lossless decompression; this changes none of the fixture ZIP/DBF bytes.
