# Malfoid shorts by @KarlaBoban97, in story order

This is an unofficial reading list of **[Karla (@KarlaBoban97)](https://x.com/KarlaBoban97)**'s Malfoid short stories,
arranged by **in-universe chronology** rather than posting date. Every short appears as an official X embed
(`blockquote.twitter-tweet` + `platform.twitter.com/widgets.js`), so views, likes and reposts all go to her original posts.

Live site: https://rguillimanxiii.github.io/Karla-Malfoid-reader/

## Files

* `shorts.json`: the source of truth.
  * `author`: handle and numeric X id (`2009643135618756609`)
  * `arcs[]`: the story sections, in order (`prologue`, `term`, `poland`, `together`, `summer`, `war`). A temporary `new` arc is shown last if needed.
  * `shorts[]`: **in story order**. Each has `arc`, `post_ids` (more than one if it's a thread), `date`, `title`, `summary`, `text` (shown as a fallback inside the blockquote) and optionally `needs_review`.
  * `excluded` / `skipped`: her posts that were deliberately left out (fandom commentary, quote posts, author notes, replies), so updates don't suggest them again.
  * `newest_post_id`: the newest of her posts seen so far. Use it as `since_id`.
* `index.html` is **generated**, so don't edit it. It's one static page with the CSS inlined and a small ES5 script.
  Embeds activate lazily, a few screens ahead, and the post text sits inside each blockquote as a fallback, so the page also works when
  `widgets.js` is blocked, for example in some in-app browsers.
* `assets/style.css` gets inlined into `index.html` at build time.
* `scripts/update.py` ingests new posts, edits the order and rebuilds the page (`--help`).

## Updating (every 3 days)

1. Fetch her posts newer than `newest_post_id` with the X API v2 (the X MCP `search_posts_all`, saving with write_to_file):
   `query="from:KarlaBoban97 -is:retweet"`, `since_id=<newest_post_id>`, `max_results=25`,
   `post.fields=created_at,author_id,conversation_id,referenced_tweets,note_tweet,attachments`,
   `expansions=attachments.media_keys`. Follow `next_token` until it runs out. Keep each raw response file.
2. `python3 scripts/update.py resp1.txt [resp2.txt ...] --updated YYYY-MM-DD`
   * A new original post that mentions Malfoid and has an image goes into the `new` arc with `needs_review: true`.
     Everything else goes into `skipped`, with the reason printed.
   * It's safe to re-run, because known ids are skipped.
3. Put each new short in its place in the story, read the text and decide where it falls in the timeline:
   * `python3 scripts/update.py --move <ID> --after <PREV_ID> [--arc summer]` (or `--after START --arc <arc>`)
   * `python3 scripts/update.py --set <ID> --title "…" --summary "…" --reviewed`
   * A thread continuation: `--attach <ID> --to <FIRST_POST_ID>`. A wrongly added post: `--exclude <ID>`.
     A skipped post that's really a short: `--include <ID> --after <PREV_ID> --title … --summary …`.
4. `git add -A && git commit -m "Update shorts" && git push`. GitHub Pages serves `main` (root) and usually goes live within a minute.

Takedown: if the author wants this changed or removed, contact [@RGuillimanXIII](https://x.com/RGuillimanXIII).
