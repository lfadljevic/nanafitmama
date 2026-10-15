# nanafitmama
Nana fit mama website (GitHub Pages + Jekyll).

## Writing blog posts with the CMS (Pages CMS)
Posts are written at https://app.pagescms.org. The writing screen has fields for title, date,
cover photo, category, text and an **Objavljeno** (published) switch. Saving creates the post file
in `_posts/` and uploads the photo to `images/blog/`; the site updates a minute or two later.
The screen is configured in `.pages.yml`.

- **Unpublish instead of delete:** switch **Objavljeno** off. The post disappears from the site but stays in the CMS.
  Deleting and renaming are switched off on purpose (renaming would change the post's web address).
- **Categories** are a fixed list in `.pages.yml` (`lifestyle`, `Sport&Zdravlje`, `Nana&Knjiga`).

## Writing a post by hand (without the CMS)
Create a file in `_posts/` named `YYYY-MM-DD-naslov.md` (the file name becomes the address: `/post/naslov/`):

```
---
title: "Naslov članka"
date: 2026-10-20
image: /images/blog/naziv-slike.jpg
kategorija: lifestyle
published: true
---
Prvi odlomak (prikazuje se i kao uvod na popisu članaka).

Ostatak teksta…
```

- **Photo:** upload it to `images/blog/` and use that path in `image`.
- **Draft / unpublish:** set `published: false`. The post disappears from the site but stays in the repository; set it back to `true` to show it again.
- **Categories** used so far: `lifestyle`, `Sport&Zdravlje`, `Nana&Knjiga`.
- `_posts/2026-10-15-primjer-clanka.md` is an unpublished sample.

## Site address
`_config.yml` has `baseurl: "/nanafitmama"` while the site runs at `lfadljevic.github.io/nanafitmama`.
When moving to a custom domain, set `baseurl: ""` and `url:` to that domain.

## Previewing the site
The pages use Jekyll includes and layouts (files starting with `---` or containing `{% include %}`),
so they only display correctly after Jekyll has built them. Opening the files directly or with a plain
file server shows raw template code. Check changes on the GitHub Pages address, or run Jekyll locally
(`bundle install`, then `bundle exec jekyll serve --unpublished`, then open `http://localhost:4000/nanafitmama/`).

## Migrated posts
The 251 posts from the old Wix blog are in `_posts/` with their original dates, categories and text.
Their photos are in `images/blog/` (`<post>.jpg` = thumbnail on the blog list, `<post>-1.jpg` = photo inside the text).
Migrated posts have `hide_image: true`, so the thumbnail is not repeated at the top of the article (as on the old site).
`migration/old-to-new-urls.csv` lists every old Wix address with its new address (useful for redirects when moving to the own domain).
