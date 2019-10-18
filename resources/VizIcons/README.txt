For prepearing images the next commands were used:

$ export name=<filename>
$ convert -resize x64 -gravity center -crop 64x64+0+0 $name.svg -flatten -colors 132 -background transparent $name.ico
$ convert $name.ico -transparent white $name.ico

If there are issues with setting white to transparency (not pure white is present), then use
$ convert -resize x64 -gravity center -crop 64x64+0+0 $name.svg -flatten -colors 256 -background transparent $name.ico
$ convert $name.ico -fuzz 1% -transparent white $name.ico

.png files were created by exporting .svg to .png using Inkscape.

