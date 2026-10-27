"""Original SVG layouts; no external images, scripts, fonts or customer likenesses."""
from html import escape as H

INK='#242d26'
PAPER='#f1eddf'
ACCENT='#ad4726'
CREAM='#f7f2e4'
DARK='#141a17'
DISPLAY='Impact, Arial Black, Arial, sans-serif'

def text(x,y,value,size=28,fill=INK,extra=''):
    return f'<text x="{x}" y="{y}" fill="{fill}" font-size="{size}" {extra}>{H(str(value))}</text>'

def shell(w,h,title,body):
    return f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" viewBox="0 0 {w} {h}" role="img" aria-label="{H(title,quote=True)}"><title>{H(title)}</title><rect width="{w}" height="{h}" fill="{PAPER}"/><g font-family="Arial, Helvetica, sans-serif">{body}</g></svg>'

def field(n,x,y,value,size=36,maxwidth=950,fill=INK):
    # Constrain the authored example too, before the browser editor fits actual glyphs.
    estimate=sum(.28 if c.isspace() else .62 for c in str(value))*size
    limit=f' textLength="{maxwidth}" lengthAdjust="spacingAndGlyphs"' if estimate>maxwidth else ''
    return text(x,y,value,size,fill,f'id="slot-{n}" data-max="{maxwidth}" data-base-size="{size}"'+limit)

def display_field(n,x,y,value,size,maxwidth,fill=CREAM,italic=False):
    return field(n,x,y,value,size,maxwidth,fill).replace('data-max=',f'font-family="{DISPLAY}" font-weight="900"'+(' font-style="italic"' if italic else '')+' data-max=')

def court_detail(x,y,width,height,color=CREAM):
    return f'<g fill="none" stroke="{color}" stroke-width="2" opacity="0.18"><rect x="{x}" y="{y}" width="{width}" height="{height}"/><path d="M {x+width/2} {y} V {y+height}"/><circle cx="{x+width/2}" cy="{y+height/2}" r="{height*.22}"/><path d="M {x} {y+height*.27} H {x+width*.17} V {y+height*.73} H {x} M {x+width} {y+height*.27} H {x+width*.83} V {y+height*.73} H {x+width}"/></g>'

def ball(x,y,r=80):
    return f'<g fill="none" stroke="{ACCENT}" stroke-width="3" data-accent="stroke"><circle cx="{x}" cy="{y}" r="{r}"/><path d="M {x-r} {y} H {x+r} M {x} {y-r} V {y+r} M {x-r*.72} {y-r*.7} Q {x+r*.5} {y} {x-r*.72} {y+r*.7} M {x+r*.72} {y-r*.7} Q {x-r*.5} {y} {x+r*.72} {y+r*.7}"/></g>'

def graphic(r):
    v=[x[1] for x in r['fields']]; layout=r['layout']
    if layout=='cover':
        b=f'<rect width="1080" height="1920" fill="{DARK}"/>'
        b+=text(65,100,'BASKETBALL / SELECTED MOMENTS',22,CREAM,'letter-spacing="2"')
        b+=f'<path d="M 65 142 H 1015" stroke="{CREAM}" opacity="0.3"/>'
        b+=field(2,65,215,v[2],26,940,CREAM).replace('data-max=', 'letter-spacing="2" data-max=')
        b+=display_field(3,55,460,v[3],172,955,CREAM,True)
        b+=f'<path d="M 0 590 L 1080 510 V 1400 L 0 1480 Z" fill="{ACCENT}" data-accent="fill"/>'
        b+='<defs><clipPath id="cover-action-panel"><path d="M 0 590 L 1080 510 V 1400 L 0 1480 Z"/></clipPath></defs>'
        b+='<g clip-path="url(#cover-action-panel)">'+court_detail(-220,675,1500,580)+'</g>'
        b+=display_field(1,70,1300,v[1],760,930,CREAM,True)
        b+=text(990,1370,'IN THE MOMENT',21,CREAM,'text-anchor="end" letter-spacing="3"')
        b+=display_field(0,65,1655,v[0],112,950)
        b+=f'<path d="M 65 1740 H 1015" stroke="{CREAM}" opacity="0.3"/>'
        b+=field(4,65,1820,v[4],30,950,CREAM)
        return shell(1080,1920,r['title'],b)
    if layout=='poster':
        # A display poster rather than a framed worksheet: strong type, a full-bleed
        # team-color panel and clear identity. All five original fields remain editable.
        cream='#f7f2e4'
        b='<rect width="1200" height="1500" fill="#141a17"/>'
        b+='<defs><pattern id="poster-grain" width="8" height="8" patternUnits="userSpaceOnUse"><circle cx="2" cy="2" r="0.7" fill="#fff" opacity="0.08"/></pattern><clipPath id="poster-panel"><rect x="60" y="590" width="1080" height="550"/></clipPath></defs>'
        b+=f'<path d="M 60 153 H 1140" stroke="{cream}" opacity="0.3"/>'
        b+=f'<circle cx="74" cy="104" r="10" fill="{ACCENT}" data-accent="fill"/>'
        b+=text(103,113,'BASKETBALL / SENIOR TRIBUTE',23,cream,'letter-spacing="2"')
        b+=field(3,1140,113,v[3],25,510,cream).replace('data-max="510"','text-anchor="end" data-max="510"')
        b+=text(55,350,'SENIOR',250,cream,'font-family="Impact, Arial Black, Arial, sans-serif" font-weight="900" font-style="italic" textLength="1065" lengthAdjust="spacingAndGlyphs"')
        b+=text(55,551,'NIGHT',250,'none',f'font-family="Impact, Arial Black, Arial, sans-serif" font-weight="900" font-style="italic" stroke="{cream}" stroke-width="2" textLength="1065" lengthAdjust="spacingAndGlyphs"')
        b+=f'<rect x="60" y="590" width="1080" height="550" fill="{ACCENT}" data-accent="fill"/>'
        b+='<g clip-path="url(#poster-panel)" fill="none" stroke="#f7f2e4" stroke-width="2" opacity="0.23"><circle cx="990" cy="890" r="350"/><ellipse cx="990" cy="890" rx="150" ry="350"/><path d="M 640 890 H 1340 M 990 540 V 1240"/></g>'
        b+=field(1,92,1090,v[1],570,900,cream).replace('data-max="900"','font-family="Impact, Arial Black, Arial, sans-serif" font-weight="900" font-style="italic" letter-spacing="-12" data-max="900"')
        b+=text(1103,1095,'THE NEXT CHAPTER',20,cream,'text-anchor="end" letter-spacing="2" transform="rotate(-90 1103 1095)"')
        b+=field(0,62,1270,v[0],103,1070,cream).replace('data-max="1070"','font-family="Impact, Arial Black, Arial, sans-serif" font-weight="900" data-max="1070"')
        b+=field(2,67,1330,v[2],27,1060,cream).replace('data-max="1060"','letter-spacing="2.5" data-max="1060"')
        b+=f'<path d="M 65 1373 H 1135" stroke="{cream}" opacity="0.3"/>'
        b+=field(4,67,1430,v[4],29,1040,cream)
        b+='<rect width="1200" height="1500" fill="url(#poster-grain)" pointer-events="none"/>'
        return shell(1200,1500,r['title'],b)
    if layout=='recruiting':
        b=f'<rect width="1200" height="675" fill="{DARK}"/><rect width="330" height="675" fill="{ACCENT}" data-accent="fill"/>'
        b+='<defs><clipPath id="profile-number-panel"><rect width="330" height="675"/></clipPath></defs>'
        b+='<g clip-path="url(#profile-number-panel)">'+court_detail(-140,170,650,390)+'</g>'
        b+=text(40,70,'BASKETBALL',20,CREAM,'letter-spacing="3"')
        b+=display_field(1,25,430,'#'+v[1],145,280,CREAM,True)
        b+=text(40,615,'PLAYER / PROFILE',18,CREAM,'letter-spacing="2"')
        b+=text(390,100,'THE PLAYER BEHIND THE PLAY',18,CREAM,'letter-spacing="2"')
        b+=display_field(0,385,280,v[0],105,745)
        b+=field(2,390,355,v[2],32,740,CREAM)
        b+=f'<path d="M 390 405 H 1135" stroke="{CREAM}" opacity="0.3"/>'
        b+=field(3,390,485,v[3],31,740,CREAM)
        b+=text(390,565,'CONTACT',15,CREAM,'letter-spacing="2"')
        b+=field(4,390,615,v[4],27,740,CREAM)
        return shell(1200,675,r['title'],b)
    if layout=='table-card':
        b=f'<rect x="900" width="300" height="600" fill="{DARK}"/><rect x="65" y="65" width="325" height="60" fill="{ACCENT}" data-accent="fill"/>'
        b+=text(85,105,'SENIOR NIGHT',23,CREAM,'letter-spacing="3"')
        b+=field(3,65,220,v[3],28,760)
        b+=display_field(0,60,390,v[0],98,770,INK)
        b+=field(2,65,475,v[2],26,770).replace('data-max=', 'letter-spacing="1.8" data-max=')
        b+=text(940,105,'THE SENIOR',19,CREAM,'letter-spacing="2"')
        b+=display_field(1,923,385,'#'+v[1],130,245,CREAM,True)
        b+=f'<path d="M 940 505 H 1150" stroke="{CREAM}" opacity="0.4"/>'
        b+=text(940,555,'ONE OF OUR OWN.',15,CREAM,'letter-spacing="1"')
        b+=f'<rect y="630" width="1200" height="170" fill="{ACCENT}" data-accent="fill"/>'
        b+=field(4,65,730,v[4],34,1070,CREAM)
        b+=f'<path d="M 65 550 H 830" stroke="{INK}" opacity="0.3"/>'
        return shell(1200,800,r['title'],b)
    if layout=='memory':
        b=f'<rect width="1000" height="28" fill="{ACCENT}" data-accent="fill"/>'
        b+=text(65,110,'SENIOR NIGHT / A NOTE FOR YOU',20,INK,'letter-spacing="2"')
        b+=text(60,260,'A MOMENT',120,INK,f'font-family="{DISPLAY}" font-weight="900"')
        b+=text(60,380,'TO KEEP.',120,'none',f'font-family="{DISPLAY}" font-weight="900" stroke="{ACCENT}" stroke-width="2" data-accent="stroke"')
        b+=display_field(0,65,490,v[0],58,690,INK)
        b+=display_field(1,800,490,'#'+v[1],58,135,ACCENT).replace('data-max=', 'data-accent="fill" data-max=')
        b+=field(2,65,540,v[2],22,860)
        b+=f'<path d="M 65 590 H 935" stroke="{ACCENT}" stroke-width="3" data-accent="stroke"/>'
        b+=field(3,65,675,v[3],30,865)
        b+=''.join(f'<path d="M 65 {y} H 935" stroke="#9da696" stroke-width="1.4"/>' for y in [785,900,1015,1130])
        b+=field(4,65,1240,v[4],27,865)
        b+='<path d="M 195 1245 H 935" stroke="#9da696"/>'
        b+=text(65,1345,'ONE TEAM. MANY MEMORIES.',19,INK,'letter-spacing="3"')
        return shell(1000,1400,r['title'],b)
    b=f'<rect width="24" height="800" fill="{ACCENT}" data-accent="fill"/>'
    b+=text(85,100,'BASKETBALL / TEAM RECOGNITION',20,INK,'letter-spacing="2.3"')
    b+=f'<path d="M 85 140 H 1115" stroke="{ACCENT}" stroke-width="2" data-accent="stroke"/>'
    b+=display_field(1,80,265,v[1],56,1030,INK)
    b+=text(85,330,'PRESENTED TO',17,INK,'letter-spacing="3"')
    b+=display_field(0,80,450,v[0],110,1030,INK)
    b+=f'<rect x="85" y="485" width="145" height="7" fill="{ACCENT}" data-accent="fill"/>'
    b+=field(3,85,565,v[3],30,1030)
    b+=f'<path d="M 85 630 H 1115" stroke="{INK}" opacity="0.25"/>'
    b+=field(2,85,690,v[2],26,1030)+field(4,85,745,v[4],23,1030)
    return shell(1200,800,r['title'],b)

def sheet_image(r):
    cols=r['columns']; rows=r['rows']; count=min(4,len(cols)); widths=1100/count
    b=text(70,85,'HOOPCUT / EDITABLE WORKSHEET',17,ACCENT)+text(70,165,r['short'],48)
    b+=text(70,215,'Fictional examples — replace before use',20)
    b+='<rect x="50" y="265" width="1100" height="65" fill="#d8dfce"/>'
    for i,c in enumerate(cols[:count]): b+=text(65+i*widths,305,c[:23],20)
    for j,row in enumerate(rows[:4]):
        y=360+j*80
        b+=f'<path d="M 50 {y+45} H 1150" stroke="#b7bfaf"/>'
        for i,v in enumerate(row[:count]): b+=text(65+i*widths,y+12,str(v)[:24],17)
    b+=text(70,750,'EDIT THE FIELDS  /  DOWNLOAD CSV  /  PRINT',18,ACCENT)
    return shell(1200,800,r['title'],b)

def guide_image(a,index):
    b=text(65,80,'THE HOOPCUT PLAYBOOK / ORIGINAL PLANNING DIAGRAM',16,ACCENT)
    if index in [0,1]:
        b+=text(65,150,'Game coverage' if index==0 else 'One drill. One repeatable frame.',43)
        b+='<g stroke="#506248" stroke-width="3" fill="none"><rect x="180" y="245" width="840" height="410"/><path d="M 600 245 V 655"/><circle cx="600" cy="450" r="70"/><rect x="180" y="355" width="150" height="190"/><rect x="870" y="355" width="150" height="190"/><circle cx="225" cy="450" r="20"/><circle cx="975" cy="450" r="20"/></g>'
        if index==0:
            b+='<path d="M 600 710 L 200 280 L 1000 280 Z" fill="#ad47261a" stroke="#ad4726" stroke-dasharray="10 8"/>'
            b+=text(70,220,'FIXED WIDE: test both ends',22)+text(70,700,'Operated view: follow the possession smoothly',20)
            b+='<rect x="560" y="680" width="80" height="38" rx="6" fill="#ad4726"/>'
        else:
            b+='<path d="M 650 695 L 810 335 L 1020 535 Z" fill="#ad47261a" stroke="#ad4726" stroke-dasharray="10 8"/><circle cx="850" cy="470" r="18" fill="#ad4726"/>'
            b+=text(70,220,'Keep start, release and finish visible',22)+text(70,710,'Phone outside the run and rebound paths',20)
    elif index==2:
        b+=text(65,160,'Three poster directions',48)
        for i,label in enumerate(['PORTRAIT','NUMBER','MEMORY']):
            x=65+i*365;b+=f'<rect x="{x}" y="235" width="335" height="415" fill="none" stroke="#7f8d75"/>'
            b+=text(x+22,285,label,20,ACCENT)
            if i==0:b+=f'<rect x="{x+22}" y="315" width="290" height="215" fill="#d8dfce"/>'+text(x+55,435,'PHOTO PLACEHOLDER',18)
            if i==1:b+=text(x+50,515,'12',165)
            if i==2:b+=text(x+22,390,'One team.',30)+text(x+22,440,'Many memories.',30)
            b+=text(x+22,605,'PLAYER NAME',24)
    elif index==3:
        b+=text(65,160,'A gift plan the team can finish',48)
        for i,(title,note) in enumerate([('MEMORY','Collect a specific message'),('KEEPSAKE','Proof details before ordering'),('VIDEO','Choose approved real clips')]):
            y=235+i*130;b+=text(70,y+35,str(i+1).zfill(2),42,ACCENT)+text(170,y+22,title,28)+text(170,y+63,note,25)
        b+=text(65,730,'Use real quotes. Sample budget amounts are fictional.',21)
    else:
        b+=text(65,160,'A clear path through the memories',44)
        for i,(title,note) in enumerate([('RECOGNIZE','Name / number / class'),('REMEMBER','Photo / keepsake / story'),('PARTICIPATE','Card / pen / collection')]):
            x=65+i*365;b+=f'<rect x="{x}" y="255" width="335" height="315" rx="8" fill="#d8dfce"/>'+text(x+20,315,str(i+1).zfill(2),32,ACCENT)+text(x+20,400,title,26)+text(x+20,460,note,18)
        b+='<path d="M 70 660 H 1120" stroke="#ad4726" stroke-width="4"/>'+text(65,720,'Keep the visitor route clear. Adapt to the real venue.',23)
    return shell(1200,800,a['title'],b)
