DOTS = $(wildcard *.dot)
SVGS = $(DOTS:%.dot=%.svg)
PNGS = $(DOTS:%.dot=%.png)

all: $(SVGS) $(PNGS) reference.pdf

%.svg: %.dot
	dot -Tsvg -o$@ $<

%.png: %.dot
	dot -Tpng -o$@ $<

%.pdf: %.md
	awk '/^# Services/,/EOF/ {print}' $< \
	  | pandoc -V 'title:Float Reference' --from=gfm --output=$@ --toc
