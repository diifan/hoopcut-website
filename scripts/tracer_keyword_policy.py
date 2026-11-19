"""Reject explicit non-sports intent before identity matching; no basketball-token gate."""
import re
OFF_TOPIC=re.compile(r'\b(?:actors?|actress(?:es)?|casino\w*|naked|nudity|nudes?|porn\w*|hentai|creampie\w*|deepthroat\w*|onlyfans|anal|blowjob\w*|hookup|sex(?:ual)?|aidra\s+fox)\b|(?:\d[\d.]*\s*)?gpa\b|\bgrade\b|\d\s*(?:lbs?|pounds?|kgs?|kg|cm|inches|feet)\s*(?:to|in)\s*(?:lbs?|pounds?|kgs?|kg|cm|inches|feet)\b',re.I)
def rejection_reason(keyword):
 m=OFF_TOPIC.search(keyword)
 return 'explicit non-sports intent: '+m.group(0) if m else None
STOP={'the','and','school','high','hudl','home','sports','club','highlights','with','junior','senior','boys','girls','team'}
def identity_aligned(keyword,title):
 words=lambda s:set(re.findall(r'[a-z]{2,}',s.casefold()))-STOP
 k=words(keyword);return bool(k) and k<=words(title)
