#!/usr/bin/env python3
"""Malfoid reader: maintain shorts.json and regenerate index.html.

Usage:
  python3 scripts/update.py --build
      Regenerate index.html from shorts.json (no network).
  python3 scripts/update.py RESP.json [RESP2.json ...]
      Ingest raw X API v2 responses (user timeline or search results; the MCP
      wrapper text around the JSON is fine). New @KarlaBoban97 posts that look
      like Malfoid shorts are added to the "new" arc with needs_review=true.
      Everything else that is new is listed in "skipped" so it won't be shown again.
  python3 scripts/update.py --move ID --after OTHER_ID [--arc ARC]
      Put short ID right after OTHER_ID (use --after START to put it first in ARC).
  python3 scripts/update.py --set ID [--title T] [--summary S] [--arc ARC] [--reviewed]
  python3 scripts/update.py --attach ID --to SHORT_ID
      Add a thread continuation post to an existing short.
  python3 scripts/update.py --exclude ID       Remove a short and add it to excluded.
  python3 scripts/update.py --include ID --after OTHER_ID [--arc ARC] --title T --summary S
      Add a post (e.g. one in excluded/skipped) as a short; text is taken from posts_cache.
Every mutating command also rebuilds index.html.
"""
import argparse, hashlib, html, json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DATA = os.path.join(ROOT, 'shorts.json')
INDEX = os.path.join(ROOT, 'index.html')


def load():
    with open(DATA, encoding='utf-8') as f:
        return json.load(f)


def save(d):
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=1)
        f.write('\n')


def parse_resp(path):
    s = open(path, encoding='utf-8').read()
    i = s.find('{')
    dec = json.JSONDecoder()
    out = []
    while i != -1 and i < len(s):
        try:
            obj, end = dec.raw_decode(s[i:])
        except ValueError:
            i = s.find('{', i + 1)
            continue
        if isinstance(obj, dict):
            out.append(obj)
        i = s.find('{', i + end)
    return out


def full_text(p):
    return (p.get('note_tweet') or {}).get('text') or p.get('text', '')


def clean(t):
    t = re.sub(r'\s*https://t\.co/\w+\s*$', '', t.strip())
    t = re.sub(r'\s*https://t\.co/\w+\s*$', '', t)
    return t.strip()


def looks_like_short(p, author_id, known_ids):
    """Heuristic: a Malfoid short is an original post (not a reply to others,
    not a quote) by the author with a photo that mentions Malfoid."""
    if p.get('author_id') and p['author_id'] != author_id:
        return False, 'other author'
    refs = {r['type']: r['id'] for r in p.get('referenced_tweets', [])}
    if 'retweeted' in refs:
        return False, 'repost'
    if 'quoted' in refs:
        return False, 'quote post (commentary on someone else\'s work)'
    if 'replied_to' in refs:
        if refs['replied_to'] in known_ids and len(clean(full_text(p))) > 200:
            return True, 'possible thread continuation of %s (consider --attach)' % refs['replied_to']
        return False, 'reply'
    t = full_text(p)
    if 'malfoid' not in t.lower():
        return False, 'no Malfoid mention'
    if not (p.get('attachments') or {}).get('media_keys'):
        return False, 'no image'
    return True, ''


def ingest(d, files):
    author_id = d['author']['id']
    known = {pid for s in d['shorts'] for pid in s['post_ids']}
    seen = known | set(d.get('excluded', {})) | set(d.get('skipped', {}))
    added, skipped = [], []
    newest = int(d.get('newest_post_id') or 0)
    for f in files:
        for obj in parse_resp(f):
            for p in obj.get('data', []) if isinstance(obj.get('data'), list) else []:
                pid = p['id']
                if p.get('author_id') and p['author_id'] != author_id:
                    continue
                newest = max(newest, int(pid))
                if pid in seen:
                    continue
                seen.add(pid)
                d.setdefault('posts_cache', {})[pid] = {
                    'created_at': p.get('created_at'), 'text': clean(full_text(p))}
                ok, why = looks_like_short(p, author_id, known)
                if ok:
                    t = clean(full_text(p))
                    d['shorts'].append({
                        'arc': 'new', 'post_ids': [pid], 'date': (p.get('created_at') or '')[:10],
                        'title': t.split('\n')[0][:60], 'summary': t.replace('\n', ' ')[:140],
                        'text': t, 'needs_review': True})
                    added.append((pid, why, t[:90].replace('\n', ' ')))
                else:
                    d.setdefault('skipped', {})[pid] = why
                    skipped.append((pid, why, clean(full_text(p))[:90].replace('\n', ' ')))
    d['newest_post_id'] = str(newest)
    print('Added %d new short(s) to arc "new" (needs_review):' % len(added))
    for a in added:
        print('  + %s %s | %s' % a)
    print('Skipped %d post(s):' % len(skipped))
    for s in skipped:
        print('  - %s [%s] | %s' % s)
    print('newest_post_id =', d['newest_post_id'])


def find(d, pid):
    for i, s in enumerate(d['shorts']):
        if pid in s['post_ids']:
            return i
    sys.exit('post %s is not on the site' % pid)


def move(d, pid, after, arc=None):
    s = d['shorts'].pop(find(d, pid))
    if arc:
        s['arc'] = arc
    if after == 'START':
        arc = arc or s['arc']
        idx = next((i for i, x in enumerate(d['shorts']) if x['arc'] == arc), len(d['shorts']))
    else:
        idx = find(d, after) + 1
        if not arc:
            s['arc'] = d['shorts'][idx - 1]['arc']
    d['shorts'].insert(idx, s)


def esc(t):
    return html.escape(t, quote=True)


def build(d):
    arcs = [a for a in d['arcs']]
    arc_ids = [a['id'] for a in arcs]
    if any(s['arc'] == 'new' for s in d['shorts']) and 'new' not in arc_ids:
        arcs.append({'id': 'new', 'title': 'Newest (not yet placed)',
                     'blurb': 'Recently posted shorts that haven\'t been placed in the timeline yet.'})
    handle = d['author']['username']
    prof = 'https://x.com/' + handle
    n = 0
    body = []
    toc = []
    for a in arcs:
        items = [s for s in d['shorts'] if s['arc'] == a['id']]
        if not items:
            continue
        first = n + 1
        sec = ['<section class="arc" id="%s">' % esc(a['id']),
               '<h2>%s</h2>' % esc(a['title']), '<p class="sub">%s</p>' % esc(a.get('blurb', ''))]
        for s in items:
            n += 1
            sec.append('<article class="short" id="s%d">' % n)
            sec.append('<h3><span class="n">%d</span> %s</h3>' % (n, esc(s['title'])))
            sec.append('<p class="sum">%s</p>' % esc(s['summary']))
            for pid in s['post_ids']:
                url = 'https://twitter.com/%s/status/%s' % (handle, pid)
                txt = s['text'] if pid == s['post_ids'][0] else d.get('posts_cache', {}).get(pid, {}).get('text', '')
                paras = '<br>'.join(esc(x) for x in txt.split('\n'))
                sec.append('<div class="embed"><blockquote class="tw-pending" data-theme="dark" data-dnt="true" data-conversation="none">'
                           '<p lang="en" dir="ltr">%s</p>&mdash; Karla (@%s) <a href="%s">%s</a></blockquote></div>'
                           % (paras, esc(handle), url, esc(s.get('date', ''))))
            sec.append('<p class="orig"><a href="https://x.com/%s/status/%s" target="_blank" rel="noopener">Open on X</a> · '
                       '<a href="#s%d">#%d</a> · <a href="#top">top</a></p>' % (esc(handle), s['post_ids'][0], n, n))
            sec.append('</article>')
        sec.append('</section>')
        body.append('\n'.join(sec))
        toc.append('<a class="btn" href="#%s">%s <span class="c">%d–%d</span></a>' % (esc(a['id']), esc(a['title']), first, n))
    version = hashlib.sha1(json.dumps(d, sort_keys=True).encode()).hexdigest()[:10]
    css = open(os.path.join(ROOT, 'assets', 'style.css'), encoding='utf-8').read()
    out = TEMPLATE.format(
        handle=esc(handle), prof=prof, count=n, toc='\n  '.join(toc), body='\n'.join(body),
        updated=esc(d.get('updated', '')), v=version, css=css)
    with open(INDEX, 'w', encoding='utf-8') as f:
        f.write(out)
    print('Built index.html: %d shorts, v=%s' % (n, version))


TEMPLATE = u'''<!doctype html>
<html lang="en">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<title>Malfoid shorts by @{handle}, in story order</title>
<meta name="description" content="An unofficial reading list of @{handle}'s Malfoid short stories on X, in in-universe chronological order, shown as the original X posts.">
<meta property="og:title" content="Malfoid shorts by @{handle}, in story order">
<meta property="og:description" content="{count} Malfoid shorts by @{handle}, in in-universe order, shown as the original X posts.">
<meta name="twitter:widgets:theme" content="dark">
<style>
{css}
</style>
</head>
<body id="top">
<header class="hero">
  <p class="kicker">Stories by <a href="{prof}" target="_blank" rel="noopener">@{handle}</a> on X</p>
  <h1>Malfoid shorts, in story order</h1>
  <p class="credit">All {count} shorts were written and posted by <a href="{prof}" target="_blank" rel="noopener"><b>Karla (@{handle})</b></a>. Each one below is her original X post, embedded, so views, likes and reposts go to her. <a href="{prof}" target="_blank" rel="noopener">Follow her on X</a>.</p>
  <nav class="jump">
  {toc}
  </nav>
  <p class="meta">Arranged by in-universe chronology, not by posting date. Last checked {updated}.</p>
</header>
<main>
{body}
</main>
<footer class="foot">
  This is an unofficial fan reading list. Every story and image belongs to <a href="{prof}" target="_blank" rel="noopener">@{handle}</a>. Nothing is copied here except a text fallback. The posts are embedded straight from X, so please like and repost them there.
  If you're the author and want this page changed or taken down, ask <a href="https://x.com/RGuillimanXIII" target="_blank" rel="noopener">@RGuillimanXIII</a> and it will be done.
</footer>
<script>
/* ES5 only (X in-app browser safe). Embeds are activated lazily, a few screens ahead. */
(function () {{
  var pending = [];
  var started = false;
  function all() {{ return document.querySelectorAll('blockquote.tw-pending'); }}
  function activate(bq) {{
    if (bq.className.indexOf('tw-pending') === -1) return;
    bq.className = 'twitter-tweet';
    if (window.twttr && window.twttr.widgets && window.twttr.widgets.load) {{
      window.twttr.widgets.load(bq.parentNode);
    }} else {{
      pending.push(bq);
    }}
  }}
  function flush() {{
    if (!(window.twttr && window.twttr.widgets && window.twttr.widgets.load)) return;
    for (var i = 0; i < pending.length; i++) window.twttr.widgets.load(pending[i].parentNode);
    pending = [];
  }}
  window.twttr = (function (d, s, id) {{
    var js, fjs = d.getElementsByTagName(s)[0], t = window.twttr || {{}};
    if (d.getElementById(id)) return t;
    js = d.createElement(s); js.id = id; js.async = true; js.charset = 'utf-8';
    js.src = 'https://platform.twitter.com/widgets.js';
    fjs.parentNode.insertBefore(js, fjs);
    t._e = []; t.ready = function (f) {{ t._e.push(f); }};
    return t;
  }}(document, 'script', 'twitter-wjs'));
  window.twttr.ready(function () {{ flush(); }});
  var list = all();
  if ('IntersectionObserver' in window) {{
    var io = new IntersectionObserver(function (entries) {{
      for (var i = 0; i < entries.length; i++) {{
        if (entries[i].isIntersecting) {{ io.unobserve(entries[i].target); activate(entries[i].target); }}
      }}
    }}, {{ rootMargin: '2500px 0px' }});
    for (var i = 0; i < list.length; i++) io.observe(list[i]);
  }} else {{
    for (var j = 0; j < list.length; j++) activate(list[j]);
  }}
}}());
</script>
</body>
</html>
'''


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('files', nargs='*')
    ap.add_argument('--build', action='store_true')
    ap.add_argument('--move'); ap.add_argument('--after'); ap.add_argument('--arc')
    ap.add_argument('--set'); ap.add_argument('--title'); ap.add_argument('--summary')
    ap.add_argument('--reviewed', action='store_true')
    ap.add_argument('--attach'); ap.add_argument('--to')
    ap.add_argument('--exclude'); ap.add_argument('--include')
    ap.add_argument('--updated')
    a = ap.parse_args()
    d = load()
    if a.files:
        ingest(d, a.files)
    if a.move:
        move(d, a.move, a.after or 'START', a.arc)
    if a.set:
        s = d['shorts'][find(d, a.set)]
        if a.title: s['title'] = a.title
        if a.summary: s['summary'] = a.summary
        if a.arc: s['arc'] = a.arc
        if a.reviewed: s.pop('needs_review', None)
    if a.attach:
        s = d['shorts'][find(d, a.to)]
        if a.attach not in s['post_ids']:
            s['post_ids'].append(a.attach)
        d.get('skipped', {}).pop(a.attach, None)
        for i, x in enumerate(list(d['shorts'])):
            if x['post_ids'] == [a.attach] and x is not s:
                d['shorts'].remove(x)
    if a.exclude:
        s = d['shorts'].pop(find(d, a.exclude))
        d.setdefault('excluded', {})[a.exclude] = 'removed by hand: ' + s['title']
    if a.include:
        c = d.get('posts_cache', {}).get(a.include)
        if not c:
            sys.exit('no cached text for %s; ingest a response containing it first' % a.include)
        d.get('excluded', {}).pop(a.include, None); d.get('skipped', {}).pop(a.include, None)
        d['shorts'].append({'arc': a.arc or 'new', 'post_ids': [a.include], 'date': (c.get('created_at') or '')[:10],
                            'title': a.title or c['text'][:60], 'summary': a.summary or c['text'][:140], 'text': c['text']})
        if a.after:
            move(d, a.include, a.after, a.arc)
    if a.updated:
        d['updated'] = a.updated
    save(d)
    build(d)


if __name__ == '__main__':
    main()
