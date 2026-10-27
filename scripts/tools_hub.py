"""Public Tools directory and homepage entry. Existing tool URLs stay stable."""
import json
import re
from html import escape as H
from pathlib import Path
from batch_one_content import RESOURCES

ROOT=Path(__file__).resolve().parents[1]
BASE='https://hoopcut.ai'
GROUPS=[('design-print','Design & print','Player graphics, covers and keepsakes you can personalize.'),('highlight-planning','Plan your highlights','Go from source timestamps to a clear sequence of plays.'),('social-content','Social & team content','Give each clip a fitting caption and a place in the week.'),('team-events','Team events','Coordinate senior night, media day and team recognition.')]

def group(r):
    if r['kind']=='graphic':return 'design-print'
    if r['category']=='Editing':return 'highlight-planning'
    if r['category']=='Social planning':return 'social-content'
    return 'team-events'

def tool_card(r):
    action='Customize design' if r['kind']=='graphic' else 'Calculate budget' if r['kind']=='budget' else 'Edit worksheet'
    formats='SVG · PNG · Print' if r['kind']=='graphic' else 'CSV · Print'
    return f'''<article class="tool-card" data-tool data-group="{group(r)}"><a class="tool-card-image" href="/templates/{r['slug']}" aria-label="Open {H(r['short'],quote=True)}"><img src="/assets/resources/{r['slug']}.jpg" alt="{H(r['short'],quote=True)} example" loading="lazy" decoding="async" width="1200" height="800"></a><div class="tool-card-copy"><p class="eyebrow">{H(r['category'])}</p><h3><a href="/templates/{r['slug']}">{H(r['short'])}</a></h3><p>{H(r['description'])}</p><div class="tool-card-bottom"><span>{formats}</span><a href="/templates/{r['slug']}">{action} <span aria-hidden="true">↗</span></a></div></div></article>'''

def build_tools():
    from build_blog import head,navigation,footer
    url=BASE+'/tools';title='Free Basketball Tools, Templates & Planners | Hoopcut'
    description='Free basketball tools for player posters, reel covers, clip logs, captions and team events. Personalize a design, edit a worksheet, then download or print.'
    graph=[{'@type':'CollectionPage','@id':url+'#page','url':url,'name':title,'description':description,'inLanguage':'en','mainEntity':{'@id':url+'#list'}},{'@type':'ItemList','@id':url+'#list','numberOfItems':len(RESOURCES),'itemListElement':[{'@type':'ListItem','position':i,'name':r['title'],'url':BASE+'/templates/'+r['slug']} for i,r in enumerate(RESOURCES,1)]},{'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Tools','item':url}]}]
    hero='''<section class="tools-hero"><div class="tools-hero-copy"><p class="eyebrow">FREE BASKETBALL TOOLS</p><h1>Your game.<br><span>Your toolkit.</span></h1><p class="lede">Make a player graphic. Plan a better reel. Get the team together. Useful little tools for the things around the game.</p><div class="tools-hero-actions"><a class="tools-primary" href="#tool-library">Find your next tool <span aria-hidden="true">↓</span></a><a href="/demo/auto-clipping">Explore auto clipping ↗</a></div><p class="tools-facts"><span>15 free tools</span><span>No sign-in</span><span>Download & keep</span></p></div><div class="tools-hero-art" aria-label="Examples of editable basketball designs"><img class="hero-design hero-cover" src="/assets/resources/basketball-reel-cover-preview.jpg" width="1080" height="1920" alt="Editable game-night reel cover with example jersey number 12" decoding="async"><img class="hero-design hero-poster" src="/assets/resources/basketball-senior-night-poster-preview.jpg" width="1200" height="1500" alt="Senior Night poster with fictional player details" fetchpriority="high" decoding="async"><div class="hero-art-note"><span>MAKE IT PERSONAL</span><strong>Your name. Your number. Your colors.</strong></div></div></section>'''
    controls='''<section id="tool-library" class="tools-library" aria-labelledby="library-title"><div class="tools-library-heading"><div><p class="eyebrow">PICK A TASK. GET STARTED.</p><h2 id="library-title">A little help for your next play.</h2></div><div id="tool-search-controls" hidden><label for="tool-search">Find a tool</label><div class="tool-search-box"><input type="search" id="tool-search" placeholder="Try poster, clip log, media day…" autocomplete="off"><button type="button" id="clear-search">Clear</button></div></div></div><nav class="tools-filters" aria-label="Tool categories"><a href="#tool-library" data-filter="all" aria-current="true">All tools <span>15</span></a>'''+''.join(f'<a href="#{key}" data-filter="{key}">{H(label)} <span>{sum(group(r)==key for r in RESOURCES)}</span></a>' for key,label,_ in GROUPS)+'''</nav><p id="tool-count" class="tool-count" role="status" aria-live="polite">15 tools to make your own.</p>'''
    sections=''.join(f'<section class="tools-group" id="{key}" data-tool-group="{key}" aria-labelledby="{key}-title"><header><h2 id="{key}-title">{H(label)}</h2><p>{H(note)}</p></header><div class="tools-grid">'+''.join(tool_card(r) for r in RESOURCES if group(r)==key)+'</div></section>' for key,label,note in GROUPS)
    tail='''<div id="no-tools" class="no-tools" hidden><h2>No matching tools yet.</h2><p>Try a shorter phrase, choose All tools, or clear your search.</p></div></section><section class="tools-workflow"><div><p class="eyebrow">FROM THE PLAN TO THE PLAY</p><h2>A tool for the plan.<br>Hoopcut for the footage.</h2><p>Use these browser tools to organize the project or create a graphic. For basketball video, explore Hoopcut’s auto clipping and Shot Tracer demos.</p><a class="tools-primary" href="/demo/auto-clipping">Try the clipping demo ↗</a><a class="tools-secondary" href="/demo/shot-tracer">See Shot Tracer ↗</a></div><div class="tools-guide-links"><h3>Need a starting point?</h3><a href="/blog/how-to-make-a-basketball-highlight-video">How to make a basketball highlight video ↗</a><a href="/blog/basketball-senior-night-ideas">Plan basketball senior night ↗</a><a href="/blog/basketball-media-day-ideas">Prepare a basketball media day ↗</a><a href="/blog">Browse the Blog ↗</a></div></section><section class="tools-faq"><p class="eyebrow">GOOD TO KNOW</p><h2>Before you make it yours.</h2><details><summary>Are the tools free to use?</summary><p>Yes. You can use these browser tools and download their files without signing in. The Hoopcut iPhone app is a separate product.</p></details><details><summary>What can I download?</summary><p>The six design templates export SVG and PNG images. The nine planning tools offer CSV files and a print view. Each tool also includes an original example you can start from.</p></details><details><summary>Will the tool save my changes?</summary><p>Your edits stay in the current page. Download a copy before refreshing or leaving. These tools do not upload your entries or publish to a social account.</p></details><details><summary>Do I need the app to use a template?</summary><p>No. The templates work in your browser. Hoopcut’s auto clipping and Shot Tracer focus on the basketball footage you want to turn into highlights.</p></details></section>'''
    page=head(title,description,url,graph,'/assets/resources/basketball-reel-cover.jpg','Basketball reel cover template example')
    page=page.replace('</head>','<link rel="stylesheet" href="/assets/tools/tools.css"><script src="/assets/tools/tools.js" defer></script></head>')
    page=page.replace('<body>','<body class="tools-directory">')+navigation('tools')+'<main id="main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><span aria-current="page">Tools</span></nav>'+hero+controls+sections+tail+'</main>'+footer()+'</body></html>'
    (ROOT/'tools.html').write_text(page)

def home_tools_section():
    picks=[('basketball-reel-cover','A cover that feels like you.','Personalize the title, name and jersey number.','Make a reel cover'),('basketball-clip-log','Find that play again.','Keep source files and timestamps together for the next edit.','Open the clip log'),('basketball-senior-gift-budget','Make the team plan add up.','Work out quantities, costs and extras before ordering.','Plan the gift budget')]
    return '<!-- TOOLS HOME START --><section id="tools" class="extra-section home-tools" aria-labelledby="home-tools-title"><div class="home-tools-heading"><div><div class="section-kicker">MORE FOR THE GAME</div><h2 id="home-tools-title">Little tools.<br>Made for basketball.</h2><p>Design a player graphic, organize your next reel or get the team event ready. Free tools you can use right in your browser.</p></div><a class="home-tools-all" href="/tools">Explore all 15 tools ↗</a></div><div class="home-tools-grid">'+''.join(f'<a href="/templates/{s}" class="home-tool-card"><img src="/assets/resources/{s}.jpg" alt="{H(action,quote=True)} example" loading="lazy" decoding="async" width="1200" height="800"><div><h3>{H(title)}</h3><p>{H(note)}</p><span>{H(action)} ↗</span></div></a>' for s,title,note,action in picks)+'</div></section><!-- TOOLS HOME END -->'

def integrate_site():
    # Keep existing public template URLs; change the directory and visible navigation.
    files=[ROOT/'index.html',ROOT/'terms.html',ROOT/'privacy.html',*ROOT.glob('blog/*.html'),*ROOT.glob('templates/*.html'),*ROOT.glob('demo/*.html')]
    for f in files:
        source=f.read_text().replace('/blog#templates','/tools').replace('>Resources<','>Tools<')
        nav=re.search(r'<nav[^>]*aria-label="Main navigation"[^>]*>.*?</nav>',source,re.S)
        if nav and 'href="/tools"' not in nav[0]:
            source=source.replace(nav[0],nav[0].replace('<a href="/blog">Blog</a>','<a href="/tools">Tools</a><a href="/blog">Blog</a>',1),1)
        nav=re.search(r'<nav[^>]*aria-label="Main navigation"[^>]*>.*?</nav>',source,re.S)
        if nav:
            source=source.replace(nav[0],re.sub(r'<a\b[^>]*href="/(?:terms|privacy)"[^>]*>.*?</a>','',nav[0]),1)
        if f.parent==ROOT:
            footer=re.search(r'<footer\b.*?</footer>',source,re.S)
            if footer and 'class="footer-links"' not in footer[0]:
                links='<nav class="footer-links" aria-label="Footer navigation"><a href="/tools">Tools</a><a href="/blog">Blog</a><a href="/terms">Terms</a><a href="/privacy">Privacy</a></nav>'
                source=source.replace(footer[0],footer[0].replace('<div class="footer-contact">',links+'<div class="footer-contact">'),1)
            if 'href="/assets/footer.css"' not in source:
                source=source.replace('</head>','<link rel="stylesheet" href="/assets/footer.css"></head>')
        footer=re.search(r'<footer\b.*?</footer>',source,re.S)
        if footer:
            updated=footer[0]
            for path,label in [('/terms','Terms'),('/privacy','Privacy')]:
                if f'href="{path}"' not in updated:
                    updated=updated.replace('</footer>',f'<a href="{path}">{label}</a></footer>')
            source=source.replace(footer[0],updated,1)
        if f.name=='index.html' and f.parent==ROOT:
            source=re.sub(r'<!-- TOOLS HOME START -->.*?<!-- TOOLS HOME END -->','',source,flags=re.S)
            source=source.replace('<section class="extra-section seo-guides"',home_tools_section()+'<section class="extra-section seo-guides"',1)
            if 'href="/assets/tools/home-tools.css"' not in source:source=source.replace('</head>','<link rel="stylesheet" href="/assets/tools/home-tools.css"></head>')
        f.write_text(source)
