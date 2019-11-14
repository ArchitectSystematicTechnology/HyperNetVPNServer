DOTS = $(wildcard *.dot)
SVGS = $(DOTS:%.dot=%.svg)
PNGS = $(DOTS:%.dot=%.png)

all: $(SVGS) $(PNGS)

%.svg: %.dot
	dot -Tsvg -o$@ $<

%.png: %.dot
	dot -Tpng -o$@ $<

