"""Editorial media for the three draft story pages; content remains static/crawlable."""
from html import escape as H


def evidence_gallery(item):
    """Keep product promotional art distinct from frames of the prepared reel."""
    gallery = item.get('evidenceGallery')
    if not gallery:
        return ''
    cards = []
    for image in gallery['items']:
        cards.append(f'''<figure><a href="{H(image['image'], quote=True)}" aria-label="View full-size image: {H(image['title'], quote=True)}"><img class="evidence-image" src="{H(image['image'], quote=True)}" alt="{H(image['alt'], quote=True)}" width="{image['width']}" height="{image['height']}" loading="lazy" decoding="async"></a><figcaption><strong>{H(image['title'])}</strong>{H(image['caption'])}</figcaption></figure>''')
    return f'''<section id="visual-example" class="evidence-gallery {H(gallery['layout'], quote=True)}"><p class="eyebrow">{H(gallery['label'])}</p><h2>{H(gallery['heading'])}</h2><p>{H(gallery['description'])}</p><div class="evidence-grid">{''.join(cards)}</div><p class="evidence-source"><a href="{H(gallery['sourceUrl'], quote=True)}">{H(gallery['sourceLabel'])}</a> · Select an image to see it full size.</p></section>'''


def cover(item):
    v = item.get('visual')
    if not v:
        return ''
    return f'''<figure class="story-cover"><img src="{H(v['image'])}" alt="{H(v['alt'],quote=True)}" width="1536" height="1024" fetchpriority="high" decoding="async"><span class="cover-label">THE HOOPCUT PLAYBOOK</span><figcaption>{H(v['caption'])}</figcaption></figure>'''


def video_block(item, mode='wide'):
    v = item.get('visual', {}).get('video')
    if not v:
        return ''
    video = f'''<video controls playsinline muted preload="none" poster="{H(v['poster'])}" width="960" height="480" aria-label="{H(v['title'],quote=True)}"><source src="{H(v['src'])}" type="video/mp4"></video>'''
    if mode == 'social':
        caption = item['captionGroups'][0]['captions'][0]
        return f'''<section class="caption-inspiration" id="caption-inspiration"><div class="social-example"><div class="social-example-header"><img src="/assets/blog/brand-icon.png" width="28" height="28" alt=""><span>Hoopcut <small>CLIP + CAPTION EXAMPLE</small></span><b aria-hidden="true">•••</b></div>{video}<div class="social-example-caption"><p>{H(caption)}</p><button type="button" data-copy-caption="{H(caption,quote=True)}" aria-label="Copy featured caption">Copy this caption ↗</button></div></div><div class="pairing-copy"><p class="eyebrow">GIVE THE MOMENT A LINE</p><h2>The clip tells the story.<br>The caption adds you.</h2><p>Watch this prepared game clip, then pick a line that fits the moment. Keep it short, credit the setup, and make the detail your own.</p><a href="#captions-1">Find your caption <span aria-hidden="true">↓</span></a><p class="media-disclosure">{H(v['caption'])}</p></div></section>'''
    return f'''<figure class="story-video" id="story-video"><div class="story-video-heading"><span class="eyebrow">{H(v['eyebrow'])}</span><h3>{H(v['title'])}</h3></div>{video}<figcaption>{H(v['caption'])} <a href="/demo/auto-clipping">Explore the interactive clipping demo →</a></figcaption></figure>'''


def overview(item):
    v=item.get('visual')
    if not v:return ''
    if item.get('captionGroups'):
        return '<div class="story-facts"><span><strong>60</strong> caption ideas</span><span><strong>06</strong> moods to browse</span><span><strong>01</strong> click to copy</span></div>'+video_block(item,'social')
    tiles=v.get('tiles',[])
    return '<section class="story-overview" aria-label="At a glance"><p class="eyebrow">'+H(v['overviewTitle'])+'</p><div class="story-overview-grid">'+''.join('<div><span>'+str(i).zfill(2)+'</span><h3>'+H(title)+'</h3><p>'+H(text)+'</p></div>' for i,(title,text) in enumerate(tiles,1))+'</div></section>'


def caption_groups(item):
    groups=item.get('captionGroups',[])
    notes=['For one play, one photo, or a quick update.','Keep the joke on your side of the court.','Give the quiet work its moment.','Celebrate what the whole group earned.','A few words for the longer process.','For the people behind the jersey.']
    markup=[]
    for i,g in enumerate(groups,1):
        cards=''.join('<li><span class="caption-number" aria-hidden="true">'+str((i-1)*10+j).zfill(2)+'</span><p>'+H(text)+'</p><button type="button" data-copy-caption="'+H(text,quote=True)+'" aria-label="Copy caption: '+H(text,quote=True)+'">Copy <span aria-hidden="true">↗</span></button></li>' for j,text in enumerate(g['captions'],1))
        markup.append('<section class="caption-group" id="captions-'+str(i)+'"><header class="caption-group-heading"><span aria-hidden="true">'+str(i).zfill(2)+'</span><div><h2>'+H(g['heading'])+'</h2><p>'+H(notes[i-1])+'</p></div><small>10 IDEAS</small></header><ul class="caption-list">'+cards+'</ul><a class="back-to-categories" href="#caption-categories">Back to categories ↑</a></section>')
    return ''.join(markup)
