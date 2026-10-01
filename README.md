<div align="center">

# olx

[![License](https://img.shields.io/badge/LICENSE-MIT-5C9E31?style=for-the-badge)](LICENSE)
[![Python](https://img.shields.io/badge/PYTHON-3.11%2B-3776AB?style=for-the-badge&logo=python&logoColor=white)](https://www.python.org)
[![Built by](https://img.shields.io/badge/BUILT%20BY-JGALEA-8A2BE2?style=for-the-badge&logo=github&logoColor=white)](https://github.com/jgalea)

**Search OLX Portugal listings from the terminal.**

</div>

OLX's search pads results with listings that don't match (a search for one brand returns its TVs, its kettles and other brands' bulbs). `olx` keeps only listings whose title has every word you searched for, and adds a radius around any town, price and condition filters, and JSON output.

```
uv tool install git+https://github.com/jgalea/olx-cli

olx search "philips hue"                         # title must contain every word
olx search "hue go" --near Porto --radius 30     # km around a town
olx search hue --condition used --max 50 --sort cheap
olx search "philips hue" --loose                 # keep OLX's fuzzy matches
olx search hue --json
olx show 672509944                               # or a listing URL
```

OLX's public API sits behind CloudFront, which rejects plain HTTP clients, so requests go through curl_cffi with a Chrome TLS fingerprint. OLX also pads searches with unrelated listings (an empty query still returns ~70), which is why matching is on the title by default.

Not affiliated with OLX.
