# nanafitmama
Nana fit mama website (GitHub Pages + Jekyll).

## Writing a blog post
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
