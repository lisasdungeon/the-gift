# The Gift

A personal library of free, public-domain / openly-licensed Bible translations and study
resources, pulled together from established open-data projects rather than built from
scratch. Nothing here is paywalled, DRM'd, or account-gated.

## Structure

```
Bibles/                                  140 Bible translations, plain JSON, one file each
Study Guides/
  Commentaries and Reference/            20 classic commentaries & reference works (SWORD format)
```

## Bibles/

140 translations across ~50 languages, compiled by the [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
project from public-domain and freely-licensed source texts (mostly digitized via the
CrossWire SWORD Project). Each translation is a single `.json` file with a simple
`translation → books → chapters → verses` structure. See [Bibles/README.md](Bibles/README.md)
for the format and a list of notable translations.

## Study Guides/Commentaries and Reference/

20 classic, public-domain Bible commentaries, topical references, and dictionaries
(Matthew Henry, Jamieson-Fausset-Brown, Barnes' Notes, Adam Clarke, Calvin, Strong's
Greek/Hebrew Dictionaries, Nave's Topical Bible, and more), in the standard **SWORD
module format** used by CrossWire and its downstream apps. See
[Study Guides/README.md](Study%20Guides/README.md) for what's included, licensing per
module, and how to actually read them (they're not plain text — see below).

## A note on "solid, not 1:1"

This is a curated slice of much larger open datasets, not an exhaustive mirror. If you
want more (more languages, more commentaries, Hebrew/Greek interlinear/tagged texts,
etc.), the source projects have a lot more available — see the per-folder READMEs for
where to go back and pull additional material.

## Licensing

Everything here is free to use, but "free" isn't monolithic:
- The large majority of texts are genuinely **public domain**.
- A couple of items (flagged explicitly in `Study Guides/README.md`) are copyrighted but
  distributed with the rights-holder's permission for free non-commercial use — not
  public domain, still free to read, not necessarily free to relicense or resell.
- Always check the specific file/module's license note before redistributing.
