#!/bin/bash


COOKIES="$HOME/.limited/cookies.txt"
OUTFILE="$HOME/data/flickr/api/$(date +%s)_api.html"
URL="https://www.flickr.com/services/apps/72157632479752633/key"

wget -nv --progress=dot --load-cookies $COOKIES -O $OUTFILE  $URL