"""Add the homepage's permanent entry into the basketball video workflows."""
import re
from pathlib import Path


START = '<!-- TRACER HOME START -->'
END = '<!-- TRACER HOME END -->'
STYLESHEET = '<link id="tracer-home-entry-styles" rel="stylesheet" href="/assets/tracer-home-entry.css">'
NAV_LINK = '<a class="nav-link" data-tracer-workflows-link href="/shot-tracer/scenarios">Workflows</a>'
SECTION = '''<!-- TRACER HOME START -->
<section class="extra-section tracer-home-entry" id="basketball-workflows" aria-labelledby="tracer-home-title">
  <div class="tracer-home-heading">
    <div>
      <p class="tracer-home-kicker">BASKETBALL VIDEO WORKFLOWS</p>
      <h2 id="tracer-home-title">Start with your next shot.</h2>
      <p class="tracer-home-intro">From a practice rep to a pickup highlight, find a clear way to prepare your footage and add a shot tracer.</p>
    </div>
    <a class="tracer-home-browse" href="/shot-tracer/scenarios">Browse all workflows <span aria-hidden="true">↗</span></a>
  </div>
  <div class="tracer-home-grid">
    <a class="tracer-home-card" href="/shot-tracer/basketball-training-app">
      <span class="tracer-home-category">01 / PRACTICE</span>
      <h3>Give your practice a finish.</h3>
      <p>Choose a complete shooting rep and turn it into a short clip with a visible ball trail.</p>
      <span class="tracer-home-action">Explore practice videos <span aria-hidden="true">→</span></span>
    </a>
    <a class="tracer-home-card" href="/shot-tracer/pickup-basketball-app">
      <span class="tracer-home-category">02 / PICKUP</span>
      <h3>Keep the play. Share the shot.</h3>
      <p>Keep the setup, release and finish together when you edit a moment from your pickup game.</p>
      <span class="tracer-home-action">Make a pickup highlight <span aria-hidden="true">→</span></span>
    </a>
    <a class="tracer-home-card" href="/shot-tracer/basketball-scouting">
      <span class="tracer-home-category">03 / SCOUTING FOOTAGE</span>
      <h3>One original. A separate edit.</h3>
      <p>Preserve clean footage for evaluation and make a separate shot tracer version for sharing.</p>
      <span class="tracer-home-action">Organize your basketball footage <span aria-hidden="true">→</span></span>
    </a>
  </div>
</section>
<!-- TRACER HOME END -->'''


def apply_home_entry(root):
    """Update index.html only; return whether its bytes changed.

    Small build/test fixtures without a homepage need no entry. Existing reviews,
    tools, metadata, media and scripts are preserved outside the owned markup.
    """
    file = Path(root) / 'index.html'
    if not file.is_file():
        return False
    original = file.read_text()
    source = original

    if source.count(START) != source.count(END) or source.count(START) > 1:
        raise ValueError('Unexpected tracer homepage markers')
    if START in source:
        source = re.sub(re.escape(START) + r'.*?' + re.escape(END), lambda _: SECTION, source, count=1, flags=re.S)
    else:
        anchor = re.search(r'<section\b[^>]*\bclass="[^"]*\breviews\b[^"]*"[^>]*>', source)
        if not anchor:
            raise ValueError('Homepage reviews boundary missing; refusing to guess insertion point')
        source = source[:anchor.start()] + SECTION + source[anchor.start():]

    nav = re.search(r'<nav\b(?=[^>]*\bid="site-navigation")[^>]*>.*?</nav>', source, re.S)
    if not nav:
        raise ValueError('Homepage primary navigation missing')
    navigation = re.sub(r'<a\b[^>]*\bdata-tracer-workflows-link\b[^>]*>.*?</a>', '', nav[0], flags=re.S)
    tool_link = re.search(r'<a\b[^>]*\bhref="/shot-tracer"[^>]*>.*?</a>', navigation, re.S)
    if not tool_link:
        raise ValueError('Homepage Shot Tracer navigation link missing')
    navigation = navigation[:tool_link.end()] + NAV_LINK + navigation[tool_link.end():]
    source = source[:nav.start()] + navigation + source[nav.end():]

    header = re.search(r'<header\b[^>]*\bclass="[^"]*\bsite-header\b[^"]*"[^>]*>', source)
    if not header:
        raise ValueError('Homepage header missing')
    if 'data-tracer-home-entry' not in header[0]:
        source = source[:header.start()] + header[0][:-1] + ' data-tracer-home-entry="true">' + source[header.end():]

    source = re.sub(r'<link\b[^>]*\bid="tracer-home-entry-styles"[^>]*>', '', source)
    if source.count('</head>') != 1:
        raise ValueError('Homepage requires one head')
    source = source.replace('</head>', STYLESHEET + '</head>', 1)
    if source != original:
        file.write_text(source)
        return True
    return False


if __name__ == '__main__':
    apply_home_entry(Path(__file__).resolve().parents[1])
