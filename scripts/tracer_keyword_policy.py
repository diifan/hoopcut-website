"""Reject explicit non-sports intent before identity matching; no basketball-token gate."""
import json
import re
from pathlib import Path
UNPUBLISHED=set(json.loads((Path(__file__).resolve().parents[1]/'content/shot-tracer/unpublished-slugs.json').read_text()))
OFF_TOPIC=re.compile(r'\b(?:obits?|obituaries|obituary|apartments?|hotels?|actors?|actress(?:es)?|casino\w*|naked|nudity|nudes?|porn\w*|hentai|creampie\w*|deepthroat\w*|onlyfans|anal|blowjob\w*|hookup|sex(?:ual)?|aidra\s+fox)\b|(?:\d[\d.]*\s*)?gpa\b|\bgrade\b|\d\s*(?:lbs?|pounds?|kgs?|kg|cm|inches|feet)\s*(?:to|in)\s*(?:lbs?|pounds?|kgs?|kg|cm|inches|feet)\b',re.I)
def rejection_reason(keyword):
 if re.sub(r'[^a-z0-9]+','-',keyword.casefold()).strip('-') in UNPUBLISHED:
  return 'withdrawn from publication'
 m=OFF_TOPIC.search(keyword)
 return 'explicit non-sports intent: '+m.group(0) if m else None
STOP={'the','and','school','high','hudl','home','sports','club','highlights','with','junior','senior','boys','girls','team'}
def identity_aligned(keyword,title):
 words=lambda s:set(re.findall(r'[a-z]{2,}',s.casefold()))-STOP
 k=words(keyword);return bool(k) and k<=words(title)
