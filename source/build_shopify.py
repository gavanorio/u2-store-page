#!/usr/bin/env python3
"""Convert store/index.html (the U-2 product page prototype) into a Shopify theme section.
Output: shopify-u2/sections/u2-spyplane.liquid, templates/product.u2-spyplane.json, files/ (pictures), and a local test page."""
import re, os, shutil, json

SRC = '/home/claude/store'
OUT = '/home/claude/shopify-u2'
TEST = '/home/claude/shopifytest'
src = open(SRC + '/index.html', encoding='utf-8').read()

# ---------- split ----------
css = src[src.index('<style>') + 7: src.index('</style>')]
body = src[src.index('</style>') + 8: src.index('<script>')]
js = src[src.index('<script>') + 8: src.rindex('</script>')]

# ---------- CSS: every rule gets the .u2p prefix so that the page and the theme do not change each other ----------
css = re.sub(r'/\*.*?\*/', '', css, flags=re.S)

def split_blocks(text):
    """yield (prelude, block_text or None) for each top-level statement"""
    i, n = 0, len(text)
    while i < n:
        j = i
        while j < n and text[j] not in '{;':
            j += 1
        if j >= n:
            break
        if text[j] == ';':
            i = j + 1
            continue
        depth, k = 1, j + 1
        while k < n and depth:
            if text[k] == '{': depth += 1
            elif text[k] == '}': depth -= 1
            k += 1
        yield text[i:j].strip(), text[j + 1:k - 1]
        i = k

def prefix_sel(sel):
    out = []
    for s in sel.split(','):
        s = s.strip()
        if not s: continue
        if s in (':root', 'body'): out.append('.u2p')
        elif s == 'html': continue
        elif s == 'main': out.append('.u2p .u2main')
        elif s == '*': out.append('.u2p'); out.append('.u2p *'); out.append('.u2p *::before'); out.append('.u2p *::after')
        else: out.append('.u2p ' + s)
    return ', '.join(out)

def scope(text):
    res = []
    for pre, blk in split_blocks(text):
        if pre.startswith('@keyframes'):
            res.append(pre.replace('@keyframes ', '@keyframes u2p-') + ' {' + blk + '}')
        elif pre.startswith('@'):
            res.append(pre + ' {\n' + scope(blk) + '\n}')
        else:
            sel = prefix_sel(pre)
            if sel: res.append(sel + ' {' + blk + '}')
    return '\n'.join(res)

css = scope(css)
for name in ('rise', 'track', 'bit', 'flick', 'pop'):
    css = re.sub(r'(animation(?:-name)?:\s*)' + name + r'\b', r'\1u2p-' + name, css)
assert 'u2p-rise' in css
css = css.replace('* { box-sizing: border-box; }', '*{box-sizing:border-box}')
css += '''
.u2p { display: block; position: relative; margin: 0; overflow-x: clip; text-align: left; }
.u2p .buy-x { width: 100%; text-align: left; color: inherit; font: inherit; cursor: pointer; }
.u2p .buy-x[aria-pressed="true"] { border-color: var(--mfd); background: rgba(67, 211, 111, .1); }
.u2p .btn[aria-busy="true"] { opacity: .7; pointer-events: none; }
'''

# ---------- body ----------
a = body.index('<header class="bar"'); b = body.index('</header>') + 9
body = body[:a] + '<div id="bar" hidden><b id="altPill"></b></div>' + body[b:]
a = body.index('<footer>'); b = body.index('</footer>') + 9
body = body[:a] + body[b:]
body = body.replace('<main>', '<div class="u2main">').replace('</main>', '</div>')
body = body.replace('img/liv/', '@@BASE@@liv_').replace('img/', '@@BASE@@')
assert body.count('<b>USD $36.99</b><s>$39.99</s><em class="pct">-8%</em>') == 2
body = body.replace('<b>USD $36.99</b><s>$39.99</s><em class="pct">-8%</em>', '<b>@@PRICE@@</b>@@CMP@@')
body = body.replace('Release offer USD $36.99', 'Release offer @@PRICE@@')
T = '<small>Add it for USD $9.99 more when you buy the U-2.</small></div><em class="pct">-44%</em>'
assert body.count(T) == 1
body = body.replace(T, '<small>@@TONTEXT@@</small></div>@@TONBADGE@@')
assert 'USD $44.98 for the two sceneries.' in body
body = body.replace('USD $44.98 for the two sceneries.', '@@BEALEPRICE@@ for the two sceneries.')
T = 'Necessary for the 7 missions. USD $9.99 with the U-2.</small></div><em class="pct">-38%</em>'
assert T in body
body = body.replace(T, 'Necessary for the 7 missions. @@HUBPRICE@@.</small></div>@@HUBBADGE@@')
assert body.count('<small>Add it for USD $9.99 more') == 0
H = 'Add Mission Hub to the cart · USD $9.99 with the U-2 <em class="pct">-38%</em>'
assert H in body
body = body.replace(H, 'Add Mission Hub to the cart · @@HUBPRICE@@@@HUBBADGE@@')
body = re.sub(r'id="mhubAdd" data-code="" data-off=""', 'id="mhubAdd" data-code="@@HUBCODE@@" data-off="@@HUBOFF@@"', body)
assert '@@HUBCODE@@' in body

# ---------- script ----------
js = js.replace("'img/liv/", "IMG + 'liv_").replace("'img/", "IMG + '")
assert js.count('IMG + ') == 5
js = js.replace("  const $ = (s) => document.querySelector(s);", "  const $ = (s) => document.querySelector(s);\n  const IMG = @@IMGJS@@, CART = @@CARTJS@@;", 1)
old = "  addCart.addEventListener('click', (e) => { if (addCart.getAttribute('aria-disabled') === 'true') e.preventDefault(); });"
assert old in js
js = js.replace(old, r'''  /* ---------- store cart: add with the Shopify cart function, then open the cart of the theme ---------- */
  async function addToCart(ids, btn, code) {
    const old = btn.innerHTML;
    btn.setAttribute('aria-busy', 'true');
    try {
      if (code) await fetch(CART.root + 'discount/' + encodeURIComponent(code), { credentials: 'same-origin' });
      const r = await fetch(CART.root + 'cart/add.js', { method: 'POST', credentials: 'same-origin', headers: { 'Content-Type': 'application/json', Accept: 'application/json' }, body: JSON.stringify({ items: ids.map((id) => ({ id: id, quantity: 1 })) }) });
      if (!r.ok) throw new Error('cart');
      document.documentElement.dispatchEvent(new CustomEvent('cart:refresh', { bubbles: true }));
      const drawer = document.querySelector('cart-drawer') || document.getElementById('cart-drawer');
      if (drawer && typeof drawer.show === 'function') {
        setTimeout(() => drawer.show(), 400);
        btn.textContent = 'Added to the cart'; setTimeout(() => { btn.innerHTML = old; }, 2600);
      } else { location.href = CART.root + 'cart'; }
    } catch (err) {
      btn.textContent = 'Could not add. Try again.'; setTimeout(() => { btn.innerHTML = old; }, 2600);
    } finally { btn.removeAttribute('aria-busy'); }
  }
  const addRows = Array.from(document.querySelectorAll('.buy-x[data-add]'));
  const idsOf = (b) => ((CART.add || {})[b.dataset.add] || []).filter(Boolean);
  if (CART.u2) addRows.forEach((b) => { if (!idsOf(b).length) b.disabled = true; });
  addCart.addEventListener('click', (e) => {
    if (addCart.getAttribute('aria-disabled') === 'true') { e.preventDefault(); return; }
    if (!CART.u2) return;                      // no store data: the link opens the product page
    e.preventDefault();
    const ids = [CART.u2];
    addRows.forEach((b) => { if (b.getAttribute('aria-pressed') === 'true') idsOf(b).forEach((id) => ids.push(id)); });
    addToCart(ids, addCart);
  });''')
js = js.replace("heroT.textContent = 'Out now · USD $36.99';", "heroT.textContent = 'Out now · ' + CART.price;")
assert "CART.price" in js
# Mission Hub button
a = js.index("  /* ---------- Mission Hub button"); b = js.index("  /* ---------- annunciator lamps")
js = js[:a] + r'''  /* ---------- Mission Hub button: the discount code and its text come from the section settings ---------- */
  (() => {
    const a = $('#mhubAdd'); if (!a) return;
    const code = a.dataset.code, off = a.dataset.off;
    if (code) {
      a.href = 'https://www.miltechsimulations.com/discount/' + encodeURIComponent(code) + '?redirect=' + encodeURIComponent('/cart/add?id=51574093578543&quantity=1');
      a.innerHTML = '<span aria-hidden="true">+</span> Add Mission Hub to the cart' + (off ? ' · ' + off : ' at a discount');
    }
    if (CART.hub) a.addEventListener('click', (e) => { e.preventDefault(); addToCart([CART.hub], a, code); });
  })();

''' + js[b:]

FONT = '<link rel="preconnect" href="https://fonts.googleapis.com">\n<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>\n<link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Jost:ital,wght@0,300;0,400;0,500;0,600;0,700;0,800;1,400&display=swap">\n'
page = FONT + '<style>\n' + css + '\n</style>\n<div class="u2p">\n' + body.strip() + '\n</div>\n<script>' + js + '</script>\n'

def render(p, m):
    for k, v in m.items(): p = p.replace(k, v)
    assert '@@' not in p, re.findall(r'@@\w+@@', p)[:5]
    return p

LIQ_HEAD = '''{%- comment -%} U-2 Spyplane product page. Made from the prototype with build_shopify.py. Pictures are in Content > Files, names start with "u2s_". {%- endcomment -%}
{%- liquid
  assign u2probe = 'u2s_c_9.webp'
  assign u2base = u2probe | file_url | split: 'c_9.webp' | first
  assign u2var = product.selected_or_first_available_variant
  assign u2ton = section.settings.tonopah.selected_or_first_available_variant.id
  assign u2hub = section.settings.hub.selected_or_first_available_variant.id
  assign u2ba = section.settings.beale_a.selected_or_first_available_variant.id
  assign u2bb = section.settings.beale_b.selected_or_first_available_variant.id
  assign u2bsum = section.settings.beale_a.price | plus: section.settings.beale_b.price
-%}
'''
SCHEMA = '''
{% schema %}
{
  "name": "U-2 Spyplane page",
  "tag": "section",
  "settings": [
    { "type": "product", "id": "tonopah", "label": "Tonopah product (the add-on in the buy box)" },
    { "type": "text", "id": "tonopah_text", "label": "Tonopah offer text", "default": "Add it for USD $9.99 more when you buy the U-2." },
    { "type": "text", "id": "tonopah_badge", "label": "Tonopah red bubble", "default": "-44%" },
    { "type": "product", "id": "beale_a", "label": "Beale product 1 (Modern Day)" },
    { "type": "product", "id": "beale_b", "label": "Beale product 2 (Retro 1980s)" },
    { "type": "product", "id": "hub", "label": "Mission Hub product" },
    { "type": "text", "id": "hub_badge", "label": "Mission Hub red bubble", "default": "-38%" },
    { "type": "text", "id": "hub_code", "label": "Mission Hub discount code", "info": "Leave empty if you use an automatic discount or no discount." },
    { "type": "text", "id": "hub_off", "label": "Mission Hub price text on the button", "info": "Example: USD $9.99 with the U-2. Leave empty to show the product price." }
  ],
  "presets": [{ "name": "U-2 Spyplane page" }]
}
{% endschema %}
'''
liquid = LIQ_HEAD + render(page, {
    '@@BASE@@': '{{ u2base }}',
    '@@PRICE@@': '{{ product.price | money }}',
    '@@CMP@@': '{% if product.compare_at_price > product.price %}{% assign u2off = product.compare_at_price | minus: product.price | times: 100.0 | divided_by: product.compare_at_price | round %}<s>{{ product.compare_at_price | money }}</s><em class="pct">-{{ u2off }}%</em>{% endif %}',
    '@@TONBADGE@@': '{% if section.settings.tonopah_badge != blank %}<em class="pct">{{ section.settings.tonopah_badge | escape }}</em>{% endif %}',
    '@@HUBBADGE@@': '{% if section.settings.hub_badge != blank %} <em class="pct">{{ section.settings.hub_badge | escape }}</em>{% endif %}',
    '@@PURL@@': '{{ product.url }}',
    '@@TONTEXT@@': '{{ section.settings.tonopah_text | escape }}',
    '@@BEALEPRICE@@': '{% if u2bsum > 0 %}{{ u2bsum | money }}{% else %}USD $44.98{% endif %}',
    '@@HUBPRICE@@': '{% if section.settings.hub_off != blank %}{{ section.settings.hub_off | escape }}{% elsif section.settings.hub != blank %}{{ section.settings.hub.price | money }}{% else %}USD $15.99{% endif %}',
    '@@HUBCODE@@': '{{ section.settings.hub_code | escape }}',
    '@@HUBOFF@@': '{{ section.settings.hub_off | escape }}',
    '@@IMGJS@@': '{{ u2base | json }}',
    '@@CARTJS@@': '{ root: {{ routes.root_url | json }}, u2: {{ u2var.id | default: "null" }}, ton: {{ u2ton | default: "null" }}, hub: {{ u2hub | default: "null" }}, add: { ton: [{{ u2ton | default: "null" }}], beale: [{{ u2ba | default: "null" }}, {{ u2bb | default: "null" }}], hub: [{{ u2hub | default: "null" }}] }, price: {{ product.price | money | strip_html | json }} }',
}) + SCHEMA
assert liquid.count('{%') == liquid.count('%}')

shutil.rmtree(OUT, ignore_errors=True)
for d in ('sections', 'templates', 'files'): os.makedirs(f'{OUT}/{d}')
open(f'{OUT}/sections/u2-spyplane.liquid', 'w', encoding='utf-8').write(liquid)
json.dump({'sections': {'main': {'type': 'u2-spyplane', 'settings': {
    'tonopah': 'kbab-beale-air-force-base-retro-1980s-for-msfs2024-copy', 'hub': 'miltech-mission-hub', 'beale_a': 'blackbird-simulations-kbab-beale-air-force-base', 'beale_b': 'blackbird-simulations-kbab-beale-air-force-base-retro-1960s-for-msfs2024', 'hub_code': '', 'hub_off': 'USD $9.99 with the U-2', 'tonopah_badge': '-44%', 'hub_badge': '-38%', 'tonopah_text': 'Add it for USD $9.99 more when you buy the U-2.'}}}, 'order': ['main']},
    open(f'{OUT}/templates/product.u2-spyplane.json', 'w'), indent=2)

# pictures: only the files that the page uses, with flat names
used = set(re.findall(r'@@BASE@@([A-Za-z0-9_.\-]+\.(?:webp|png|jpg))', body))
names = []
for root, _, fs in os.walk(SRC + '/img'):
    for f in fs:
        rel = os.path.relpath(os.path.join(root, f), SRC + '/img').replace(os.sep, '/')
        flat = rel.replace('liv/', 'liv_')
        dyn = flat.startswith(('c_', 'shot_', 'liv_', 'scr_', 'x_sc', 'artw_'))
        if flat in used or dyn:
            shutil.copy(os.path.join(root, f), f'{OUT}/files/u2s_{flat}'); names.append(flat)
missing = [u for u in used if u not in names]
print('liquid KB', len(liquid.encode()) // 1024, 'pictures', len(names), 'missing', missing)

# local test page (no Liquid): the same markup with fixed values
shutil.rmtree(TEST, ignore_errors=True); os.makedirs(TEST + '/img')
for f in os.listdir(f'{OUT}/files'): shutil.copy(f'{OUT}/files/{f}', f'{TEST}/img/{f}')
test = render(page, {'@@BASE@@': 'img/u2s_', '@@PRICE@@': '$36.99', '@@CMP@@': '<s>$39.99</s><em class="pct">-8%</em>', '@@TONBADGE@@': '<em class="pct">-44%</em>', '@@HUBBADGE@@': ' <em class="pct">-38%</em>', '@@PURL@@': '#', '@@BEALEPRICE@@': 'USD $44.98', '@@TONTEXT@@': 'Add it for USD $9.99 more when you buy the U-2.', '@@HUBPRICE@@': 'USD $15.99', '@@HUBCODE@@': '', '@@HUBOFF@@': '',
                     '@@IMGJS@@': '"img/u2s_"', '@@CARTJS@@': '{ root: "/", u2: null, ton: null, hub: null, add: {}, price: "$36.99" }'})
theme = '<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><style>body{margin:0;font-family:Georgia,serif;color:#900} h2{font-size:80px;color:green} p{margin:2em} .btn{background:pink!important} button{border:4px solid red}</style></head><body><header style="position:sticky;top:0;z-index:50;height:64px;background:#fff;border-bottom:1px solid #ccc">THEME HEADER</header><main>'
open(TEST + '/index.html', 'w', encoding='utf-8').write(theme + test + '</main><footer style="padding:40px">THEME FOOTER</footer></body></html>')
