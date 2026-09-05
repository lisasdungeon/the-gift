# Bibles

140 Bible translations as plain JSON, one file per translation, sourced from the
[scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) project
(a compiled, public-domain/open-license dataset built primarily from CrossWire SWORD
Project texts). The original repo also ships this same data as CSV/SQL/SQLite/Parquet/
YAML/XML — only the JSON copy was pulled here to keep the footprint reasonable; if you
want another format, re-run the same clone against `formats/<csv|sql|sqlite|...>`
instead of `formats/json`.

`UPSTREAM_README.md` and `docs/README.md` are the original project's own docs, kept for
attribution and deeper detail on how the data was built.

## Format

Each file is `formats/json/<CODE>.json`:

```json
{
  "translation": "KJV: King James Version (1769) with Strongs Numbers and Morphology and CatchWords",
  "books": [
    {
      "name": "Genesis",
      "chapters": [
        { "chapter": 1, "verses": [ { "verse": 1, "text": "In the beginning God created the heaven and the earth." } ] }
      ]
    }
  ]
}
```

66 books, in order, for every translation (a handful of files add deuterocanonical books
or are NT/OT-only where that's what historically exists for that text — check the
`translation` field's own description).

## Notable translations included

- **English, classic**: KJV (KJVA, KJVPCE, RWebster, RNKJV, AKJV, UKJV, MKJV — KJV
  family variants), ASV, YLT (Young's Literal), Darby, Webster, Tyndale (1526), Wycliffe
  (1382), Geneva1599, DRC (Douay-Rheims, Catholic), BBE (Bible in Basic English), Weymouth-
  adjacent LITV, Rotherham, Noyes, Anderson, Twenty (Twentieth Century NT), Haweis
- **English, modern/open**: WEB family (NHEB, NHEBJE, NHEBME), LEB (Lexham), BSB (Berean
  Standard Bible), OEB (Open English Bible)
- **Original languages**: WLC (Hebrew Masoretic Text), TR + Byz + StatResGNT (Greek NT
  text-types), MapM, Peshitta (Aramaic)
- **Latin**: Vulgate + VulgClementine/Conte/Hetzenauer/Sistine variants
- **Jewish**: JPS 1917
- **Major world languages**: French (9 variants incl. Crampon, Darby/JND, Synodale,
  Geneve1669), German (9 variants incl. Luther-lineage BoLut, Elberfelder, Schlachter),
  Spanish (4 variants incl. Reina-Valera), Portuguese (3), Dutch (3), Russian (2),
  Chinese (Union + Union-traditional + Standard), Japanese (3), Korean (2), Swedish (3),
  Finnish (3), Polish (2), Czech (2), Slovenian (4), Serbian (2), Vietnamese, Thai,
  Norwegian (3), Danish, Hungarian, Croatian, Ukrainian, Greek (modern), Albanian,
  Armenian, Esperanto, and more
- **Smaller/heritage languages**: Manx Gaelic, Cherokee (Che1860), Burmese, Haitian
  Creole, Tagalog, Cebuano, Maori, Estonian, Latvian, Malagasy, Tok Pisin, and others

Full list: `ls formats/json/`.

## License

Public domain / freely redistributable — same license terms as the upstream
[scrollmapper/bible_databases](https://github.com/scrollmapper/bible_databases) repo
(see `LICENSE`). That project only includes texts it can distribute this way; if a
translation you want isn't here (e.g. modern copyrighted translations like NIV/ESV/NASB),
it's because those aren't open-license and can't legally be redistributed this way.

## Want more?

The upstream repo has more (other formats, and it periodically adds translations). The
[BibleNLP/ebible](https://github.com/BibleNLP/ebible) corpus is a much larger companion
project (~1,000+ public-domain/permissively-licensed translations, mostly non-English
and minority languages) if you want serious breadth beyond what's curated here.
