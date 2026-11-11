#!/usr/bin/env python3
"""Build two useful court tools into the actual public site and sitemap."""
import hashlib
import json
import re
import subprocess
from html import escape as H
from pathlib import Path
from xml.etree import ElementTree as ET

ROOT = Path(__file__).resolve().parents[1]
BASE = 'https://hoopcut.ai'
DATE = '2026-11-11'
NBA = 'https://official.nba.com/rule-no-1-court-dimensions-equipment/'
FIBA = 'https://www.venueguide.fiba.basketball/vanue-design'
FIBA_RULES = 'https://assets.fiba.basketball/image/upload/documents-corporate-fiba-official-rules-2024-v10a.pdf'
PAGES = [
    dict(mode='diagram',slug='basketball-court-diagram',name='Basketball court diagram',
         title='Basketball Court Diagram: Free Interactive Tool | Hoopcut',
         description='Create a basketball court diagram with NBA or FIBA layouts. Place players, draw movement arrows, mark a camera position, then download SVG or PNG for free.',
         intro='Map your next run. Place the players, draw the movement and find a spot for your camera. A free basketball court diagram you can make your own.',
         guide=[
             ('Build a basketball court diagram that works for your plan', 'Choose the NBA or FIBA reference layout, then switch between a full court and half court. The diagram changes the playing-area proportions, lane and three-point markings with the selected court. Feet and metres change the dimension labels; they do not move your markers. The drawing simplifies minor markings and is intended for planning, not venue construction.'),
             ('Place the players, ball and movement', 'Choose Player and tap the court to add a numbered marker. Drag a player to adjust the position. Choose Arrow, then tap its start and end to show a cut or pass. A ball marker can identify who starts with possession. Use Eraser to remove a marker, or Undo to reverse the last edit. Half-court view keeps markers on the other half of the full-court plan, so you can return to the full view later.'),
             ('Include the person behind the camera', 'Add a camera marker to discuss where the recording might come from. Treat this as a placement note, not a simulated camera view: the tool does not calculate lens coverage, obstructions or a safe filming area. Check the actual venue, keep equipment outside active play and preserve a view of both the shooter and basket. Our basketball filming guide explains what to check before recording.'),
             ('Take the plan to practice', 'Give your plan a short title, then export a PNG for a group chat or an SVG for further editing. The print view removes page navigation and keeps the drawing. Your current draft is saved in this browser when local storage is available. It does not sync between devices; downloaded files are the copy you can keep or share. You can also open the blank reference SVG without running JavaScript.')],
         faq=[('Is the basketball court diagram free?', 'Yes. Place markers, change layouts and download your diagram without an account or the Hoopcut app.'),('Can I print a blank basketball court?', 'Yes. Clear the markers, choose half court or full court, then use Print or download SVG. There is also a blank reference download below the editor.'),('Which court measurements are included?', 'The NBA reference uses a 94 by 50 foot playing area. The FIBA reference uses a 28 by 15 metre playing area. Their three-point lines and lanes differ. This is a simplified reference diagram; consult the linked governing-body rules for a complete specification.'),('Does the camera marker show what my phone will record?', 'No. It is a note about a proposed filming position. It does not model camera angle, lens, lighting or venue access.'),('Will my diagram survive a refresh?', 'The current draft saves on this device when browser storage is available. Clearing browser data or using a different browser can remove it. Download SVG or PNG to keep a separate copy.')],
         links=[('Record a basketball shooting session','/tools/basketball-shot-chart'),('Choose a basketball filming position','/blog/how-to-film-basketball-games'),('Plan the clips from your recording','/templates/basketball-clip-log')]),
    dict(mode='shots',slug='basketball-shot-chart',name='Basketball shot chart',
         title='Basketball Shot Chart & Shooting Tracker — Free | Hoopcut',
         description='Track basketball shots on a free interactive shot chart. Log makes and misses, see field-goal and zone percentages, save locally, and export PNG or CSV.',
         intro='Every shot tells you something. Tap the court to log makes and misses, find your spots and keep a record of the work. Your basketball shot chart starts here.',
         guide=[
             ('Make a basketball shot chart from your own attempts', 'Choose the court reference before starting. Select Made or Missed, then tap the spot where the shot was taken. A filled circle records a make; a cross records a miss. Keep tapping for attempts with the same result, or change the result button when needed. For keyboard entry, open Add by position or focus the court and use arrow keys, followed by Enter.'),
             ('Read field-goal percentage in context', 'Field-goal percentage is made shots divided by recorded attempts, multiplied by 100. For example, 6 makes from 10 attempts is 60%. The tool also separates two-point and three-point attempts and groups locations into six broad areas. Those groups are planning categories, not official league tracking zones. A chart containing only selected highlights cannot describe the accuracy of a full game or practice.'),
             ('Correct the chart before comparing sessions', 'Drag an entry to correct its position, change its result in the recent-shot log or remove an accidental tap. Undo restores the last edit. The two-point or three-point estimate uses the selected reference court and the point you enter; a tap on the line is treated as two points. These are manual locations, not calibrated measurements from a camera. Changing court references scales existing points and recalculates their classification.'),
             ('Keep a shooting record you can use again', 'Export CSV for the complete attempt log, including result, court reference, zone and coordinates in metres. Download PNG for a visual practice recap, or SVG to keep an editable graphic. Only the most recent 12 entries appear in the on-page log, while statistics and exports include every recorded attempt, up to 500 per session. Your current session saves in this browser when storage is available.'),
             ('Connect practice notes with your basketball footage', 'If you film practice, use a separate clip log to record where the selected attempts appear in the source video. This browser tool does not detect shots, create clips or add a trajectory. Hoopcut on iPhone provides basketball auto clipping and Shot Tracer. Keep every attempt in your shooting record even when your highlight reel contains only the plays you choose to share.')],
         faq=[('How is shooting percentage calculated?', 'Field-goal percentage equals makes divided by attempts times 100. With no attempts, the chart shows a dash. Two-point, three-point and zone results use their own attempt counts.'),('Does the shot chart automatically analyse video?', 'No. You enter makes, misses and positions manually. This free browser tool is separate from Hoopcut’s iPhone auto clipping and Shot Tracer features.'),('Are the demo shots real player results?', 'No. The optional demo session is fictional. Demo entries are labelled in the page and exports. Clear them before recording your own shooting session.'),('Are my shots uploaded?', 'The tool saves the current draft in your browser and creates downloads on your device. There is no account or cloud shot database. The title and individual shot coordinates are not included in tool-usage analytics events.'),('Can I correct or undo an attempt?', 'Yes. Drag a shot marker to move it, toggle Made or Missed in the recent-shot log, remove an entry or use Undo. CSV includes all attempts, including entries older than the recent on-page log.'),('Can I use it on my phone?', 'Yes. Tap the court after choosing Made or Missed. The chart and controls adapt to a small screen. Avoid confusing an estimated tap location with a measured shooting distance.')],
         links=[('Plan a basketball court and filming setup','/tools/basketball-court-diagram'),('Keep source-video timestamps in a clip log','/templates/basketball-clip-log'),('Record basketball practice alone','/blog/record-basketball-practice-alone'),('See the basketball Shot Tracer demo','/demo/shot-tracer')])
]


def svg_reference(mode):
    code="import {courtSVG} from './assets/court/geometry.js'; const s=JSON.parse(process.argv[1]); const r=courtSVG(s,{exporting:true}); console.log(JSON.stringify(r));"
    state=dict(standard='nba',view='half' if mode=='shots' else 'full',units='ft',theme='wood',dimensions=mode!='shots',items=[])
    result=subprocess.run(['node','--input-type=module','-e',code,json.dumps(state)],cwd=ROOT,text=True,capture_output=True,check=True)
    return json.loads(result.stdout)


def shared_controls(shots):
    return '''<div class="control-block"><p class="control-title">Court setup</p><label class="field" for="court-standard">Reference layout<select id="court-standard"><option value="nba">NBA · 94 × 50 ft</option><option value="fiba">FIBA · 28 × 15 m</option></select></label>'''+('' if shots else '''<div class="segmented" aria-label="Court view"><button type="button" data-view="full" aria-pressed="true">Full court</button><button type="button" data-view="half" aria-pressed="false">Half court</button></div>''')+'''<label class="field session-title-field" for="session-title">'''+('Session name' if shots else 'Plan name')+'''<input id="session-title" type="text" value="'''+('My shooting session' if shots else 'Evening run')+'''" maxlength="60" autocomplete="off"></label></div>'''


def workspace(page,reference):
    shots=page['mode']=='shots'
    symbols=[('player','①','Player'),('ball','◉','Ball'),('camera','▣','Camera'),('arrow','↗','Arrow'),('erase','⌫','Eraser')]
    markers='<div class="control-block"><p class="control-title">Make your play</p><div class="marker-tools">'+''.join('<button type="button" data-mode="'+key+'" aria-pressed="'+str(i==0).lower()+'"><span class="tool-icon" aria-hidden="true">'+icon+'</span>'+label+'</button>' for i,(key,icon,label) in enumerate(symbols))+'</div><p class="control-note">Tap to add. Drag to move.<br>For an arrow, tap a start and an end.</p></div>'
    display='''<div class="control-block display-settings"><p class="control-title">Display</p><label class="field" for="court-units">Dimensions in<select id="court-units"><option value="ft">Feet</option><option value="m">Metres</option></select></label><label class="check-label"><input type="checkbox" id="show-dimensions"'''+('' if shots else ' checked')+'''>Show dimensions</label><div class="segmented" aria-label="Court color"><button type="button" data-theme="wood" aria-pressed="true">Wood</button><button type="button" data-theme="ink" aria-pressed="false">Forest</button></div></div>'''
    stats='''<div class="shot-stats"><div class="fg-stat"><strong id="shot-fg">—</strong><span>FIELD-GOAL<br>PERCENTAGE</span></div><div class="metric"><strong id="shot-made">0</strong><span>SHOTS MADE</span></div><div class="metric"><strong id="shot-attempts">0</strong><span>ATTEMPTS</span></div></div><div class="split-stats"><div><span>2-POINT</span><b id="shot-two">0/0</b></div><div><span>3-POINT</span><b id="shot-three">0/0</b></div></div><div><p class="control-title">Around the court</p><div class="zones" id="shot-zones"></div></div>'''
    keyboard='''<details class="keyboard-entry"><summary>Add a shot by position</summary><div class="keyboard-fields"><label class="field" for="shot-position">Approximate spot<select id="shot-position"><option value="rim">At the rim</option><option value="paint">Paint</option><option value="midrange">Mid-range</option><option value="left">Left three</option><option value="top">Above-break three</option><option value="right">Right three</option></select></label><button type="button" id="add-position-shot">Add selected result</button></div></details>'''
    settings=('<details class="shot-settings"><summary>Court & session settings</summary>'+shared_controls(shots)+display+'</details>'+keyboard) if shots else shared_controls(shots)+markers+display
    controls='<aside class="studio-controls" aria-label="'+('Shooting statistics and setup' if shots else 'Court diagram controls')+'">'+(stats if shots else '')+settings+'</aside>'
    result_buttons='''<div class="shot-result" aria-label="Shot result"><button type="button" class="result-made" data-result="made" aria-pressed="true"><span class="result-symbol" aria-hidden="true">●</span>Made</button><button type="button" class="result-missed" data-result="missed" aria-pressed="false"><span class="result-symbol" aria-hidden="true">×</span>Missed</button></div>'''
    exports='<button type="button" id="export-svg">SVG ↓</button><button type="button" id="export-png" class="primary">Download PNG ↓</button>'+('<button type="button" id="export-csv">CSV ↓</button>' if shots else '')+'<button type="button" id="print-court">Print</button>'
    svg='<svg id="court-svg" class="court-svg" xmlns="http://www.w3.org/2000/svg" viewBox="'+reference['viewBox']+'" role="group" aria-label="Interactive basketball court. Use arrow keys to position, Enter to add, Delete to remove a selected entry." tabindex="0">'+reference['content']+'</svg>'
    foot='Choose Made or Missed, then tap a shot location. Your positions are manual estimates.' if shots else 'Start with a player. Add a ball, a camera and the movement between them.'
    canvas='<div class="court-workspace"><div class="canvas-toolbar">'+(result_buttons if shots else '<p class="plan-title">'+('<span id="drawing-title">Evening run</span>'))+('' if shots else '<span id="session-badge">Example plan</span></p>')+('<span class="shot-label" id="session-badge">Your session</span><span id="drawing-title" hidden>My shooting session</span>' if shots else '')+'<div class="canvas-buttons"><button type="button" id="undo-court" disabled>↶ Undo</button><button type="button" id="clear-court"'+(' disabled' if shots else '')+'>Clear</button></div></div><div id="court-frame" class="court-frame '+('half' if shots else 'full')+'">'+svg+'</div><div class="canvas-foot"><p>'+foot+'</p><span class="court-shortcut"><kbd>↑↓←→</kbd> move · <kbd>Enter</kbd> place</span></div><div class="session-tools"><button type="button" id="sample-court">'+('Try demo shots' if shots else 'Load example plan')+'</button></div></div>'
    widget='<section id="workspace" class="studio'+(' shooting' if shots else '')+'" aria-label="'+H(page['name'])+' editor"><h2 class="print-heading" id="print-heading">'+H(page['name'])+'</h2><header class="studio-top"><div class="studio-name"><span class="studio-dot" aria-hidden="true"></span><span id="court-reference">NBA / '+('HALF COURT' if shots else 'FULL COURT')+'</span><span id="local-save" class="local-save">Works on your device</span></div><div class="export-actions">'+exports+'</div></header><div class="studio-body">'+controls+canvas+'</div><div id="studio-status" class="studio-status" role="status" aria-live="polite">'+('Choose Made or Missed, then tap where the shot was taken.' if shots else 'Choose a marker, then tap the court.')+'</div><p class="print-heading print-summary" id="print-summary"></p></section>'
    log='''<section class="shot-log" aria-labelledby="shot-log-title"><header><h2 id="shot-log-title">The shot log.</h2><span class="shot-label" id="log-count">0 shots</span></header><p id="shot-empty" class="log-empty">A clean slate. Record your first attempt on the court above, or try the clearly labelled demo session.</p><div class="log-scroll"><table id="shot-log-table" hidden><thead><tr><th scope="col">Shot</th><th scope="col">Result</th><th scope="col">Type</th><th scope="col">Area</th><th scope="col">Edit</th></tr></thead><tbody id="shot-table-body"></tbody></table></div><p class="control-note">Latest 12 attempts shown. All attempts are included in your totals and CSV. A circle means made; a cross means missed.</p></section>''' if shots else ''
    fallback='<div class="studio-bottom"><span>Free to use · No sign-in · Your current draft stays in this browser.</span><a href="/assets/court/'+page['slug']+'-blank.svg" download>Download a blank '+('half-court shot chart' if shots else 'court diagram')+' ↗</a></div><noscript><p>The editor needs JavaScript. You can still read the guide and download the blank reference SVG above.</p></noscript>'
    dialog='<dialog id="clear-dialog"><h2>Clear this '+('shooting session' if shots else 'court plan')+'?</h2><p>Your current entries will be removed from this draft. Download a copy first if you want to keep them. You can also undo the clear.</p><div class="dialog-actions"><form method="dialog"><button>Keep editing</button></form><button type="button" id="confirm-clear" class="primary">Clear '+('session' if shots else 'plan')+'</button></div></dialog>'
    return widget+fallback+log+dialog


def build():
    from build_blog import head,navigation,footer
    (ROOT/'tools').mkdir(exist_ok=True);assets=ROOT/'assets/court';assets.mkdir(exist_ok=True)
    subprocess.run(['node',str(ROOT/'scripts/build_court_media.cjs')],check=True)
    store=json.loads((ROOT/'content/site-config.json').read_text())['app']['appStoreUrl']
    settings=json.loads((ROOT/'content/site-config.json').read_text())['analytics']
    script=ROOT/'assets/court/studio.js';style=ROOT/'assets/court/studio.css'
    # Keep module imports relative to the same directory; a content hash busts
    # the entry cache while assets/court retains the host's normal revalidation.
    digest=hashlib.sha256(script.read_bytes()+(assets/'geometry.js').read_bytes()).hexdigest()[:12]
    css_hash=hashlib.sha256(style.read_bytes()).hexdigest()[:12]
    for page in PAGES:
        slug=page['slug'];url=BASE+'/tools/'+slug;reference=svg_reference(page['mode'])
        blank='<svg xmlns="http://www.w3.org/2000/svg" viewBox="'+reference['viewBox']+'" role="img" aria-label="Blank NBA '+H(page['name'])+'">'+reference['content']+'</svg>'
        (assets/(slug+'-blank.svg')).write_text(blank)
        graph=[{'@type':'WebPage','@id':url+'#page','url':url,'name':page['title'],'description':page['description'],'inLanguage':'en','dateModified':DATE,'mainEntity':{'@id':url+'#tool'}},
               {'@type':'WebApplication','@id':url+'#tool','url':url,'name':page['name'],'description':page['description'],'applicationCategory':'SportsApplication','operatingSystem':'Any modern browser','browserRequirements':'JavaScript enabled for the editor','isAccessibleForFree':True,'offers':{'@type':'Offer','price':'0','priceCurrency':'USD'},'author':{'@type':'Organization','name':'Hoopcut','url':BASE+'/'}},
               {'@type':'BreadcrumbList','itemListElement':[{'@type':'ListItem','position':1,'name':'Home','item':BASE+'/'},{'@type':'ListItem','position':2,'name':'Tools','item':BASE+'/tools'},{'@type':'ListItem','position':3,'name':page['name'],'item':url}]}]
        hero='<header class="studio-hero"><div><p class="eyebrow">THE HOOPCUT TOOLKIT / '+('017 — SHOOT & REVIEW' if page['mode']=='shots' else '016 — PLAN YOUR PLAY')+'</p><h1>'+H(page['name'])+'.</h1><p class="lede">'+H(page['intro'])+'</p></div><nav class="studio-tabs" aria-label="Court tools">'+''.join('<a href="/tools/'+p['slug']+'"'+(' aria-current="page"' if p==page else '')+'>'+('Court diagram' if p['mode']=='diagram' else 'Shot chart')+' <span aria-hidden="true">↗</span></a>' for p in PAGES)+'</nav></header>'
        guide=''.join('<section id="guide-'+str(i)+'"><h2>'+H(title)+'</h2><p>'+H(text)+'</p></section>' for i,(title,text) in enumerate(page['guide'],1))
        dimensions='''<section id="court-dimensions"><h2>NBA and FIBA court references.</h2><table class="dimensions-table"><caption>Playing-area dimensions, not total venue footprint</caption><thead><tr><th scope="col">Reference</th><th scope="col">Full court</th><th scope="col">Three-point arc</th></tr></thead><tbody><tr><th scope="row">NBA</th><td>94 × 50 ft</td><td>23 ft 9 in; 22 ft at corners</td></tr><tr><th scope="row">FIBA</th><td>28 × 15 m</td><td>6.75 m arc</td></tr></tbody></table><p>The selected reference changes the drawing. Diagram line thickness and minor markings are simplified. See the governing-body sources for exact measurement conventions.</p></section>'''
        questions='<section class="studio-faq" id="questions"><h2>A few things to know.</h2>'+''.join('<details><summary>'+H(q)+'</summary><p>'+H(a)+'</p></details>' for q,a in page['faq'])+'</section>'
        aside='<aside><div class="next-step"><p class="eyebrow">FROM THE PLAN TO THE PLAY</p><h2>You bring the game.<br>Keep the moments.</h2><p>Record your basketball footage, then use Hoopcut on iPhone for auto clipping and Shot Tracer. These free browser tools are your planning companions.</p><a href="'+H(store,quote=True)+'" data-app-access="app-store" data-cta="court-tool">Get Hoopcut for iPhone ↗</a></div><nav class="related-tools" aria-label="Related basketball tools and guides">'+''.join('<a href="'+u+'">'+H(t)+' ↗</a>' for t,u in page['links'])+'</nav><section class="source-note" id="sources"><p>REFERENCE NOTES / CHECKED NOV 11, 2026</p><p>Reference geometry: <a href="'+NBA+'">NBA official court rules</a>, <a href="'+FIBA+'">FIBA venue guide</a> and <a href="'+FIBA_RULES+'">FIBA court markings</a>. Original planning graphics by Hoopcut; not a certified court specification.</p></section></aside>'
        markup=head(page['title'],page['description'],url,graph,'/assets/court/'+slug+'-social.png',page['name']+' tool on a basketball court')
        markup=markup.replace('</head>','<link rel="stylesheet" href="/assets/court/studio.css?v='+css_hash+'"><script id="site-settings" type="application/json">'+json.dumps({'analytics':settings})+'</script><script src="/assets/site-events.js" defer></script><script type="module" src="/assets/court/studio.js?v='+digest+'"></script></head>').replace('<body>','<body class="court-page">')
        markup+=navigation('tools')+'<main id="main"><nav class="breadcrumbs" aria-label="Breadcrumb"><a href="/">Home</a><span aria-hidden="true">/</span><a href="/tools">Tools</a><span aria-hidden="true">/</span><span aria-current="page">'+H(page['name'])+'</span></nav>'+hero+workspace(page,reference)+'<div class="studio-reading"><article>'+guide+dimensions+questions+'<p class="studio-byline">Original tool and guide by Hoopcut · Updated <time datetime="'+DATE+'">November 11, 2026</time></p></article>'+aside+'</div></main>'+footer()+'<script id="court-tool-data" type="application/json">'+json.dumps({'mode':page['mode'],'slug':slug})+'</script></body></html>'
        (ROOT/'tools'/(slug+'.html')).write_text(markup)
    integrate_entries()
    tree=ET.parse(ROOT/'sitemap.xml');root=tree.getroot();ns='{http://www.sitemaps.org/schemas/sitemap/0.9}'
    for path in ['/tools/'+p['slug'] for p in PAGES]+['/','/tools']:
        url=BASE+path;node=next((n for n in root if n.findtext(ns+'loc')==url),None)
        if node is None:node=ET.SubElement(root,ns+'url');ET.SubElement(node,ns+'loc').text=url
        modified=node.find(ns+'lastmod')
        if modified is None:modified=ET.SubElement(node,ns+'lastmod')
        modified.text=max(modified.text or '',DATE)
    ET.register_namespace('',ns[1:-1]);tree.write(ROOT/'sitemap.xml',encoding='utf-8',xml_declaration=True)
    print('Built court diagram + shot chart; integrated Tools, homepage, sitemap. No publishing.')


def integrate_entries():
    cards=''.join('<article class="tool-card" data-tool data-group="court-practice"><a class="tool-card-image" href="/tools/'+p['slug']+'"><img src="/assets/court/'+p['slug']+'-social.png" width="1200" height="630" alt="'+H(p['name'],quote=True)+' interactive tool" loading="lazy" decoding="async"></a><div class="tool-card-copy"><p class="eyebrow">COURT & PRACTICE</p><h3><a href="/tools/'+p['slug']+'">'+H(p['name'])+'</a></h3><p>'+H(p['description'])+'</p><div class="tool-card-bottom"><span>'+('PNG · CSV · SVG' if p['mode']=='shots' else 'PNG · SVG · Print')+'</span><a href="/tools/'+p['slug']+'">Open tool ↗</a></div></div></article>' for p in PAGES)
    section='<!-- COURT TOOLS START --><section class="tools-group" id="court-practice" data-tool-group="court-practice" aria-labelledby="court-practice-title"><header><h2 id="court-practice-title">On the court.</h2><p>Draw the plan. Record the practice. Keep your next run in view.</p></header><div class="tools-grid">'+cards+'</div></section><!-- COURT TOOLS END -->'
    f=ROOT/'tools.html';source=f.read_text();source=re.sub(r'<!-- COURT TOOLS START -->.*?<!-- COURT TOOLS END -->','',source,flags=re.S)
    anchor='<section class="tools-group" id="design-print"';assert anchor in source
    source=source.replace(anchor,section+anchor,1)
    source=source.replace('15 free tools','17 free tools').replace('15 tools to make your own.','17 tools to make your own.').replace('All tools <span>15</span>','All tools <span>17</span>')
    source=source.replace('The six design templates export SVG and PNG images. The nine planning tools offer CSV files and a print view. Each tool also includes an original example you can start from.','Court diagrams export SVG and PNG; shot charts also export a CSV attempt log. The six design templates export SVG and PNG, and the nine planning worksheets offer CSV and print views.')
    source=source.replace('Your edits stay in the current page. Download a copy before refreshing or leaving. These tools do not upload your entries or publish to a social account.','The court diagram and shot chart save the current draft on this device when browser storage is available. Other templates keep edits in the current page. Download a copy to keep your work. These tools do not publish to a social account.')
    source=source.replace('Free basketball tools for player posters, reel covers, clip logs, captions and team events. Personalize a design, edit a worksheet, then download or print.','Free basketball court diagrams, shot charts, player posters, reel covers and clip logs. Plan a play, track your shots, personalize a design, then download.')
    source=re.sub(r'<a href="#court-practice" data-filter="court-practice">.*?</a>','',source)
    source=source.replace('<a href="#design-print" data-filter="design-print">','<a href="#court-practice" data-filter="court-practice">Court & practice <span>2</span></a><a href="#design-print" data-filter="design-print">',1)
    def itemlist(match):
        data=json.loads(match[1])
        for node in data.get('@graph',[]):
            if node.get('@type')=='ItemList':
                entries=node['itemListElement'];entries=[e for e in entries if e.get('url') not in {BASE+'/tools/'+p['slug'] for p in PAGES}]
                entries=[{'@type':'ListItem','name':p['name'],'url':BASE+'/tools/'+p['slug']} for p in PAGES]+entries
                for i,e in enumerate(entries,1):e['position']=i
                node['itemListElement']=entries;node['numberOfItems']=len(entries)
        return '<script type="application/ld+json">'+json.dumps(data,ensure_ascii=False).replace('</','<\\/')+'</script>'
    source=re.sub(r'<script type="application/ld\+json">(.*?)</script>',itemlist,source,flags=re.S);f.write_text(source)
    # Add a narrow homepage entry while preserving the owner's original reviews.
    f=ROOT/'index.html';source=f.read_text();source=re.sub(r'<!-- COURT HOME START -->.*?<!-- COURT HOME END -->','',source,flags=re.S)
    entry='<!-- COURT HOME START --><div style="display:flex;flex-wrap:wrap;gap:12px;margin:24px 0"><a href="/tools/basketball-court-diagram" style="font-size:14px;color:#e6b58f">Draw a basketball court plan ↗</a><a href="/tools/basketball-shot-chart" style="font-size:14px;color:#e6b58f">Track your basketball shots ↗</a></div><!-- COURT HOME END -->'
    anchor='<div class="home-tools-grid">';assert anchor in source
    source=source.replace(anchor,entry+anchor,1).replace('Explore all 15 tools','Explore all 17 tools');f.write_text(source)


if __name__=='__main__':build()
