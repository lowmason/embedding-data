Complete public national geography originals support the v2 raw-to-bundle fixture
chain. `provenance.json` retains each original citation, byte size/SHA, compressed
size/SHA and layout observations. Gzip uses mtime 0 and decompresses byte-for-byte.
The already tracked genuine nationwide Geocorr intersection fixture is reused from
the geography folder. No production-tree or ignored diagnostic-folder read occurs
in tests. Upstream geographic builders run unchanged against these originals;
fixture people remain synthetic.
