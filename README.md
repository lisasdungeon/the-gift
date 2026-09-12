# The Gift

A personal library of free, public-domain / openly-licensed Bible translations and study
resources, pulled together from established open-data projects rather than built from
scratch. Nothing here is paywalled, DRM'd, or account-gated.

## Structure

```
Bibles/                                  140 Bible translations, three formats under Bibles/formats/
Study Guides/
  Commentaries and Reference/            20 classic commentaries & reference works (SWORD format)
```

## Bibles/

140 translations across ~50 languages, compiled by the [scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases)
project from public-domain and freely-licensed source texts (mostly digitized via the
CrossWire SWORD Project). Three formats ship under `Bibles/formats/`: plain text
(one UTF-8 `.txt` per translation — the readable copy), per-book and per-language
python files for scripting, and cross-reference correlate data.

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

## Serving it

`server.py` (Python 3 stdlib only) serves the whole library with a landing
page and browsable listings:

```bash
python3 server.py          # 0.0.0.0:8770 — LAN-visible
```

Never exposes `.git`, the private `model/` folder, or dotfiles. For hosting
on the RNK box (192.168.1.202) see [deploy/HOSTING.md](deploy/HOSTING.md).
Bulk/programmatic access should use git or rsync, not HTTP.

## Licensing

Everything here is free to use, but "free" isn't monolithic:
- The large majority of texts are genuinely **public domain**.
- A couple of items (flagged explicitly in `Study Guides/README.md`) are copyrighted but
  distributed with the rights-holder's permission for free non-commercial use — not
  public domain, still free to read, not necessarily free to relicense or resell.
- Always check the specific file/module's license note before redistributing.
