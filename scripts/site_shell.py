"""The public website's frame: header, banner, tab bar placement, footer and theme.

build_site.py puts the dashboard page (template/page.html) inside this frame. The banner is written
from the data at build time, so it always shows the latest release.
"""
import html
import math

FONTS = ('<link rel="preconnect" href="https://fonts.googleapis.com">'
         '<link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>'
         '<link href="https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600&'
         'family=Source+Serif+4:opsz,wght@8..60,400;8..60,600&display=swap" rel="stylesheet">')

FAVICON = ("data:image/svg+xml,"
           "%3Csvg xmlns='http://www.w3.org/2000/svg' viewBox='0 0 32 32'%3E"
           "%3Crect width='32' height='32' rx='7' fill='%2312284A'/%3E"
           "%3Crect x='6' y='19' width='4' height='7' rx='1' fill='%239CC3FF'/%3E"
           "%3Crect x='12' y='14' width='4' height='12' rx='1' fill='%239CC3FF'/%3E"
           "%3Crect x='18' y='10' width='4' height='16' rx='1' fill='%23FFFFFF'/%3E"
           "%3Crect x='24' y='6' width='4' height='20' rx='1' fill='%23FF8A7A'/%3E%3C/svg%3E")

LOGO = ('<svg class="logo" viewBox="0 0 32 32" aria-hidden="true"><rect width="32" height="32" rx="7" fill="#1C3A66"/>'
        '<rect x="6" y="19" width="4" height="7" rx="1" fill="#9CC3FF"/><rect x="12" y="14" width="4" height="12" rx="1" fill="#9CC3FF"/>'
        '<rect x="18" y="10" width="4" height="16" rx="1" fill="#FFFFFF"/><rect x="24" y="6" width="4" height="20" rx="1" fill="#FF8A7A"/></svg>')

# Theme tokens the dashboard page reads (light, then dark)
LIGHT = ("--color-fg:#172033;--color-fg-muted:#566176;--color-bg:#F4F6F9;--color-panel:#FFFFFF;--color-border-line:#E1E6EE;"
         "--color-ok:#25734A;--color-warn:#9A6400;--color-bad:#B42D24;--cds-chart-status-critical:#D0453A;--cds-chart-muted:#B8C0CC;"
         "--cds-chart-grid:#EDF0F4;--cds-chart-axis:#C5CDD8;--cds-chart-reference:#566176;--cds-surface-popover:#FFFFFF;"
         "--cds-border:#D9DFE8;--cds-shadow-popover:0 4px 16px rgba(18,40,74,.14);--cds-text-secondary:#566176;"
         "--navy:#12284A;--navy-2:#1C3A66;--on-navy:#FFFFFF;--on-navy-muted:#B7C4D8;")
DARK = ("--color-fg:#E6EBF2;--color-fg-muted:#9AA7BA;--color-bg:#0C1525;--color-panel:#131F33;--color-border-line:#24324A;"
        "--color-ok:#6CC08B;--color-warn:#E0A84A;--color-bad:#F28B80;--cds-chart-status-critical:#E25F53;--cds-chart-muted:#56637A;"
        "--cds-chart-grid:#1D2A40;--cds-chart-axis:#34445E;--cds-chart-reference:#9AA7BA;--cds-surface-popover:#1A2840;"
        "--cds-border:#2C3B55;--cds-shadow-popover:0 4px 16px rgba(0,0,0,.5);--cds-text-secondary:#9AA7BA;"
        "--navy:#16305A;--navy-2:#2F6FB3;--on-navy:#FFFFFF;--on-navy-muted:#B4C3DA;")
def theme_css():
    """Light by default, dark when the device prefers it, and either one when the visitor chooses it."""
    return (f":root{{{LIGHT}{SIZES}color-scheme:light}}"
            f"@media (prefers-color-scheme: dark){{:root:not([data-theme=light]){{{DARK}color-scheme:dark}}}}"
            f":root[data-theme=dark]{{{DARK}color-scheme:dark}}")


# runs before the page draws, so a saved choice never flashes the wrong theme
THEME_HEAD = ("<script>try{var t=localStorage.getItem('theme');if(t==='light'||t==='dark')"
              "document.documentElement.setAttribute('data-theme',t)}catch(e){}</script>")

SIZES = ("--cds-radius:10px;--cds-pad-xs:4px;--cds-pad-sm:8px;--cds-pad-md:12px;--cds-pad-lg:20px;--cds-gap-xs:4px;--cds-gap-sm:8px;"
         "--cds-gap-md:16px;--cds-gap-lg:24px;--cds-gap-xl:32px;--cds-font-size-caption:12.5px;--cds-font-size-body:15px;"
         "--cds-font-size-heading:19px;--cds-font-size-title:30px;--cds-font-weight-medium:600;"
         "--font-anthropic-sans:'IBM Plex Sans',system-ui,-apple-system,'Segoe UI',sans-serif;"
         "--font-anthropic-serif:'Source Serif 4',Georgia,serif;--cds-dur-slow:.3s;--cds-ease-out:cubic-bezier(.2,.8,.2,1);")

CSS = """
html,body{margin:0;background:var(--color-bg);color:var(--color-fg);font-family:var(--font-anthropic-sans);-webkit-font-smoothing:antialiased}
.wrap{max-width:1160px;margin:0 auto;padding:0 20px}
a{color:inherit}
/* header + banner */
.masthead{background:var(--navy);color:var(--on-navy)}
.topbar{display:flex;align-items:center;justify-content:space-between;gap:16px;padding:16px 0}
.brand{display:flex;align-items:center;gap:10px;text-decoration:none;font-weight:600;font-size:17px;letter-spacing:.005em}
.brand .logo{width:30px;height:30px}
.toplinks{display:flex;gap:20px;font-size:14px}
.top-right{display:flex;align-items:center;gap:10px}
.country{display:flex;padding:3px;border-radius:999px;background:rgba(255,255,255,.1)}
.country a{padding:6px 14px;border-radius:999px;font-size:14px;font-weight:500;color:var(--on-navy-muted);text-decoration:none;white-space:nowrap}
.country a:hover{color:#FFFFFF}
.country a[aria-current=page]{background:#FFFFFF;color:#12284A}
.theme-btn{display:inline-flex;align-items:center;justify-content:center;width:36px;height:36px;border-radius:50%;border:1px solid rgba(255,255,255,.25);
  background:transparent;color:#FFFFFF;cursor:pointer;padding:0}
.theme-btn:hover{background:rgba(255,255,255,.12)}
.theme-btn svg{width:18px;height:18px}
.theme-btn .moon{display:none}
:root[data-theme=dark] .theme-btn .sun{display:none}:root[data-theme=dark] .theme-btn .moon{display:block}
@media (prefers-color-scheme: dark){:root:not([data-theme=light]) .theme-btn .sun{display:none}:root:not([data-theme=light]) .theme-btn .moon{display:block}}
.period{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--color-fg-muted)}
.period[hidden]{display:none}
.standalone .tab-lede{margin:2px 0 0;font-size:15px;color:var(--color-fg-muted);text-align:center}
.toplinks a{color:var(--on-navy-muted);text-decoration:none}
.toplinks a:hover,.toplinks a:focus-visible{color:var(--on-navy);text-decoration:underline;text-underline-offset:3px}
.banner{text-align:center;padding:40px 0 48px}
.banner .kicker{text-wrap:balance;margin:0 0 14px;color:var(--on-navy-muted);font-size:14px}
.banner h1{text-wrap:balance;font-family:var(--font-anthropic-serif);font-weight:600;font-size:clamp(30px,5vw,50px);line-height:1.1;margin:0 auto;max-width:18ch;letter-spacing:-.01em}
.banner .lede{text-wrap:balance;margin:18px auto 0;max-width:60ch;font-size:17px;line-height:1.55;color:#DCE4F0}
/* the target ruler */
.ruler{max-width:720px;margin:44px auto 0;padding:0 10px}
.ruler-track{position:relative;height:10px;border-radius:5px;background:rgba(255,255,255,.14)}
.ruler-ok{position:absolute;top:0;bottom:0;left:0;border-radius:5px 0 0 5px;background:rgba(156,195,255,.35)}
.ruler-target{position:absolute;top:-16px;bottom:-16px;width:0;border-left:2px dashed #FFFFFF}
.ruler-target span{position:absolute;bottom:100%;left:0;transform:translateX(-50%);margin-bottom:6px;white-space:nowrap;font-size:13px;color:#FFFFFF;font-weight:500}
.ruler-mark{position:absolute;top:50%;width:18px;height:18px;margin:-9px 0 0 -9px;border-radius:50%;border:3px solid var(--navy)}
.ruler-mark.head{background:#FF8A7A}
.ruler-mark.core{background:#9CC3FF}
.ruler-mark span{position:absolute;left:50%;transform:translateX(-50%);white-space:nowrap;font-size:13px;line-height:1.25;text-align:center}
.ruler-mark span b{display:block;font-family:var(--font-anthropic-serif);font-size:22px;font-weight:600;color:#FFFFFF}
.ruler-mark.below span{top:26px}
.ruler-mark.above span{bottom:26px}
.ruler-mark span em{font-style:normal;color:var(--on-navy-muted)}
.ruler-scale{position:relative;height:18px;margin-top:64px;font-size:12px;color:var(--on-navy-muted)}
.ruler-scale span{position:absolute;transform:translateX(-50%)}
/* tab bar */
.tabs-row{position:sticky;top:0;z-index:30;display:flex;align-items:center;justify-content:center;gap:16px;flex-wrap:wrap;
  margin:0 -20px;padding:12px 20px;background:color-mix(in srgb,var(--color-bg) 92%,transparent);backdrop-filter:blur(8px);
  border-bottom:1px solid var(--color-border-line)}
.standalone .cp-tabs{border:0;gap:6px;justify-content:center;flex-wrap:wrap;overflow:visible}
.standalone .cp-tabs button{border:1px solid var(--color-border-line);border-radius:999px;margin:0;padding:8px 18px;font-size:15px;font-weight:500;
  color:var(--color-fg);background:var(--color-panel)}
.standalone .cp-tabs button:hover{border-color:var(--navy-2)}
.standalone .cp-tabs button[aria-selected=true]{background:var(--navy-2);border-color:var(--navy-2);color:#FFFFFF}
.standalone #viewseg{border-radius:999px}
.standalone #viewseg button{padding:7px 14px;font-size:13px}
/* page */
.standalone #dash-root{padding-top:0;padding-bottom:48px}
.standalone .cp{gap:24px}
.standalone .cp-head{display:none}
.standalone .cp-panel{gap:20px;padding-top:4px}
.standalone .cp-card{border-radius:12px;padding:24px}
.standalone .cp h2{font-family:var(--font-anthropic-serif);font-weight:600;font-size:22px;letter-spacing:-.005em;margin-bottom:6px}
.standalone .cp h3{font-size:15px}
.standalone .cp-note{font-size:13.5px;line-height:1.5;max-width:90ch}
.standalone .cp-takeaways{border-left:4px solid var(--navy-2)}
.standalone .cp-takeaways ul{font-size:16px}
.standalone .cp-kpis{grid-template-columns:repeat(auto-fit,minmax(min(100%,300px),1fr))}
@media (min-width:960px){.standalone .cp-kpis{grid-template-columns:repeat(3,1fr)}}
.standalone .cp-kpi .lbl{font-size:13px;font-weight:500}
.standalone .cp-kpi .big{font-size:34px}
.standalone .cp-prose{max-width:none}
.standalone .cp-prose > *{max-width:78ch}
.standalone .cp-prose h2{max-width:none}
/* release dates under the ruler */
.banner .release{margin:30px 0 0;display:flex;justify-content:center;gap:24px;flex-wrap:wrap;font-size:13.5px;color:var(--on-navy-muted)}
/* time-frame chooser */
.viewbar{display:flex;align-items:center;justify-content:center;gap:16px 20px;flex-wrap:wrap;margin:20px 0 4px}
.viewbar[hidden]{display:none}
.vb-q{margin:0;font-size:15px;font-weight:600;color:var(--color-fg)}
.vb-opts{display:flex;gap:10px;flex-wrap:wrap;justify-content:center}
.vb-opts button{font:inherit;display:flex;flex-direction:column;align-items:flex-start;gap:2px;text-align:left;min-width:250px;cursor:pointer;
  padding:12px 16px 12px 42px;position:relative;border-radius:12px;border:1.5px solid var(--color-border-line);background:var(--color-panel);color:var(--color-fg)}
.vb-opts button::before{content:"";position:absolute;left:15px;top:16px;width:14px;height:14px;border-radius:50%;border:2px solid var(--cds-chart-axis);box-sizing:border-box}
.vb-opts button:hover{border-color:var(--navy-2)}
.vb-opts button[aria-pressed=true]{border-color:var(--navy-2);box-shadow:0 0 0 1px var(--navy-2) inset;background:color-mix(in srgb,var(--navy-2) 7%,var(--color-panel))}
.vb-opts button[aria-pressed=true]::before{border:4.5px solid var(--navy-2)}
.vb-t{font-weight:600;font-size:15px}
.vb-d{font-size:13px;color:var(--color-fg-muted)}
.mini-view{display:flex;align-items:center;gap:8px;font-size:13px;color:var(--color-fg-muted)}
.standalone #viewseg button[aria-pressed=true]{background:var(--navy-2);color:#FFFFFF}
/* number cards */
.standalone .cp-kpi{display:flex;flex-direction:column;gap:6px}
.standalone .cp-kpi .big{margin:2px 0 0}
.kpi-gap{font-size:13px;font-weight:500}
.kpi-gap > span{display:inline-block;padding:3px 10px;border-radius:999px;background:color-mix(in srgb,var(--cds-chart-muted) 22%,transparent)}
.kpi-gap > span.up{background:color-mix(in srgb,var(--color-bad) 11%,transparent);color:var(--color-bad)}
.kpi-gap > span.down{background:color-mix(in srgb,#2F6FB3 13%,transparent);color:#2F6FB3}
.kpi-gap-note{color:var(--color-fg-muted);font-weight:400}
.standalone .cp-kpi .sub{font-size:13px}
/* takeaways */
.standalone .tk-title{font-size:20px;margin:0 0 10px}
/* tables */
.standalone .cp table{font-size:13.5px}
.standalone .cp th{font-weight:600;color:var(--color-fg-muted);border-bottom:1.5px solid var(--color-border-line)}
.standalone .cp tbody tr:hover td{background:color-mix(in srgb,var(--navy-2) 5%,transparent)}
.standalone .cp td{padding:7px 10px}
/* skip link */
.skip{position:absolute;left:-999px;top:8px;background:#FFFFFF;color:#12284A;padding:8px 12px;border-radius:6px;z-index:100}
.skip:focus{left:8px}
/* footer */
.sitefoot{background:var(--navy);color:var(--on-navy-muted);font-size:14px;line-height:1.6}
.sitefoot .cols{display:grid;grid-template-columns:repeat(auto-fit,minmax(min(100%,240px),1fr));gap:28px;padding:36px 0 20px}
.sitefoot h4{margin:0 0 8px;color:#FFFFFF;font-size:15px;font-weight:600}
.sitefoot p{margin:0}
.sitefoot a{color:#DCE4F0}
.sitefoot .legal{border-top:1px solid rgba(255,255,255,.12);padding:16px 0 28px;font-size:13px}
@media (max-width:640px){.toplinks{display:none}.vb-opts button{min-width:0;width:100%}.vb-opts{width:100%}.country a{padding:6px 11px;font-size:13px}.banner .release{gap:4px 16px;flex-direction:column;align-items:center}.banner{padding:28px 0 36px}.banner .lede{font-size:16px}
  .tabs-row{gap:10px;position:static}.brand span{display:none}.standalone .cp-tabs button{padding:7px 13px;font-size:14px}.ruler-mark span b{font-size:18px}}
:focus-visible{outline:2px solid #6FA2E8;outline-offset:2px}
"""

# moves the tab bar and the measure switch into one sticky row, and the takeaways into the Overview tab
AFTER = """<script>
(function(){
  var tabs=document.getElementById('tabs'),seg=document.getElementById('viewseg'),take=document.getElementById('takeaways'),ov=document.getElementById('overview');
  var NO_PERIOD=['momentum','compare','method'];
  if(tabs&&seg){
    var row=document.createElement('div');row.className='tabs-row';tabs.parentNode.insertBefore(row,tabs);row.appendChild(tabs);
    var box=document.createElement('div');box.className='period';box.id='period';
    var lab=document.createElement('span');lab.id='period-label';lab.textContent='Change over';
    box.appendChild(lab);box.appendChild(seg);row.appendChild(box);
    seg.setAttribute('aria-labelledby','period-label');
    seg.querySelectorAll('button').forEach(function(b){
      b.textContent=b.dataset.view==='yoy'?'12 months':'1 month';
      b.title=b.dataset.view==='yoy'?(seg.dataset.yoyTitle||''):(seg.dataset.momTitle||'');
    });
  }
  if(take&&ov){var lede=ov.querySelector('.tab-lede');ov.insertBefore(take,lede?lede.nextSibling:ov.firstChild);}
  dash.onData(function(){
    var p=dash.params(),tab=p.tab||'overview';
    var pr=document.getElementById('period');if(pr)pr.style.visibility=NO_PERIOD.indexOf(tab)>-1?'hidden':'visible';
    document.querySelectorAll('.cp-kpi .gapnum').forEach(function(s){
      var txt=s.textContent.trim(),v=parseFloat(txt.replace('\u2212','-'));
      if(isNaN(v))return;
      if(v>0&&txt.charAt(0)!=='+')s.textContent='+'+txt;
      s.parentNode.classList.toggle('up',v>0);s.parentNode.classList.toggle('down',v<=0);
    });
  });
  var TABS=['overview','drivers','components','momentum','regions','compare','method'];
  var go=function(){var t=location.hash.slice(1);if(TABS.indexOf(t)>-1){dash.setParams({tab:t});}};
  window.addEventListener('hashchange',go);
  document.querySelectorAll('a[data-tab-link]').forEach(function(a){a.addEventListener('click',function(){setTimeout(function(){var r=document.querySelector('.tabs-row');if(r)r.scrollIntoView({block:'start'});},0);});});
  // switching country keeps the open tab
  document.querySelectorAll('.country a').forEach(function(a){a.addEventListener('click',function(){var t=(dash.params().tab)||'';if(t&&t!=='overview')a.href=a.getAttribute('href').split('#')[0]+'#'+t;});});
})();
</script>"""

# theme toggle, also used on the privacy page
THEME_JS = """<script>
(function(){
  var b=document.querySelector('.theme-btn');if(!b)return;
  var cur=function(){var t=document.documentElement.getAttribute('data-theme');if(t)return t;return window.matchMedia&&matchMedia('(prefers-color-scheme: dark)').matches?'dark':'light';};
  var label=function(){var d=cur()==='dark';b.setAttribute('aria-label',d?'Switch to light theme':'Switch to dark theme');b.title=d?'Light theme':'Dark theme';};
  label();
  b.addEventListener('click',function(){var n=cur()==='dark'?'light':'dark';document.documentElement.setAttribute('data-theme',n);try{localStorage.setItem('theme',n)}catch(e){}label();
    if(window.dash&&dash.setParams)dash.setParams({});});
})();
</script>"""

THEME_BTN = ('<button type="button" class="theme-btn" aria-label="Switch theme">'
             '<svg class="sun" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" aria-hidden="true"><circle cx="12" cy="12" r="4.5"/>'
             '<path d="M12 2v2.5M12 19.5V22M2 12h2.5M19.5 12H22M4.9 4.9l1.8 1.8M17.3 17.3l1.8 1.8M4.9 19.1l1.8-1.8M17.3 6.7l1.8-1.8"/></svg>'
             '<svg class="moon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">'
             '<path d="M20.5 14.5A8.5 8.5 0 0 1 9.5 3.5a8.5 8.5 0 1 0 11 11z"/></svg></button>')


def _num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def _date(iso):
    import datetime
    try:
        d = datetime.date.fromisoformat(iso)
    except (TypeError, ValueError):
        return None
    return f"{d.strftime('%B')} {d.day}, {d.year}"


def banner(data, release=None, country=None):
    country = country or {}
    comps = {r["item"]: r for r in data["components"]}
    head = _num(comps["All items"]["yoy"])
    core = _num(comps["All items less food and energy"]["yoy"])
    latest = max(r["date"] for r in data["fred"] if r["headline"])
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    month_name = f"{months[int(latest[5:7]) - 1]} {latest[:4]}"
    parents = [r for r in data["effects"] if r["view"] == "yoy" and r["level"] == "parent"]
    top = max(parents, key=lambda r: float(r["contrib"]))

    release = release or {}
    rel_bits = []
    if release.get("month") == latest[:7] and _date(release.get("released")):
        rel_bits.append(f"Released {_date(release['released'])}")
    if release.get("month") == latest[:7] and _date(release.get("next_release")):
        rel_bits.append(f"Next release {_date(release['next_release'])}")
    release_line = ('<p class="release">' + "<span></span>".join(f"<span>{b}</span>" for b in rel_bits) + "</p>") if rel_bits else ""
    verb = "rose" if head >= 0 else "fell"
    gap = head - 2
    goal = country.get("goal", "the Federal Reserve's 2% goal")
    gap_txt = (f"{abs(gap):.1f} points {'above' if gap > 0 else 'below'} {goal}" if abs(gap) >= 0.05 else f"right at {goal}")
    lede = (f"That's {gap_txt}. Core inflation, which leaves out food and energy, was {core:.1f}%. "
            + country.get("lede_extra", "")
            + f"{top['item']} added the most: {float(top['contrib']):.2f} of the {head:.1f} points.")

    lo = min(0, math.floor(min(head, core)))
    hi = max(6, math.ceil(max(head, core) + 1))
    pos = lambda v: (v - lo) / (hi - lo) * 100
    # labels: headline below, core below unless the two sit close together
    core_side = "above" if abs(head - core) < 1.0 else "below"
    ticks = "".join(f'<span style="left:{pos(t):.2f}%">{t}%</span>' for t in range(lo, hi + 1))
    ruler = f"""<div class="ruler" role="img" aria-label="Headline CPI {head:.1f}% and core CPI {core:.1f}% on a scale from {lo}% to {hi}%, with the 2% target marked">
  <div class="ruler-track">
    <div class="ruler-ok" style="width:{pos(2):.2f}%"></div>
    <div class="ruler-target" style="left:{pos(2):.2f}%"><span>2% target</span></div>
    <div class="ruler-mark core {core_side}" style="left:{pos(core):.2f}%"><span><b>{core:.1f}%</b><em>Core</em></span></div>
    <div class="ruler-mark head below" style="left:{pos(head):.2f}%"><span><b>{head:.1f}%</b><em>All items</em></span></div>
  </div>
  <div class="ruler-scale" aria-hidden="true">{ticks}</div>
</div>"""
    return f"""<section class="banner" aria-labelledby="headline">
    <p class="kicker">Consumer Price Index, 12 months to {month_name}</p>
    <h1 id="headline">{country.get("people", "US")} prices {verb} {abs(head):.1f}% over the past year</h1>
    <p class="lede">{html.escape(lede)}</p>
    {ruler}
    {release_line}
  </section>""", month_name


def viewbar(data):
    latest = max(r["date"] for r in data["fred"] if r["headline"])
    months = ["January", "February", "March", "April", "May", "June", "July", "August", "September", "October", "November", "December"]
    y, m = int(latest[:4]), int(latest[5:7])
    prev_m = months[m - 2] if m > 1 else "December"
    yoy_d = f"{months[m - 1]} {y} compared with {months[m - 1]} {y - 1}"
    mom_d = f"{months[m - 1]} compared with {prev_m}, seasonally adjusted"
    return f"""<div class="viewbar" id="viewbar" role="group" aria-labelledby="vb-q">
  <p class="vb-q" id="vb-q">Compare prices over</p>
  <div class="vb-opts">
    <button type="button" data-view="yoy" aria-pressed="true"><span class="vb-t">The past 12 months</span><span class="vb-d">{yoy_d}</span></button>
    <button type="button" data-view="mom" aria-pressed="false"><span class="vb-t">The latest month</span><span class="vb-d">{mom_d}</span></button>
  </div>
</div>"""


def header(cfg, banner_html, country_code="us"):
    name = html.escape(cfg["site_name"])
    cur = lambda c: ' aria-current="page"' if c == country_code else ""
    return f"""<header class="masthead">
  <div class="wrap">
    <nav class="topbar" aria-label="Site">
      <a class="brand" href="/">{LOGO}<span>{name}</span></a>
      <div class="top-right">
        <nav class="country" aria-label="Country"><a href="/"{cur("us")}>United States</a><a href="/canada/"{cur("ca")}>Canada</a></nav>
        {THEME_BTN}
      </div>
    </nav>
    {banner_html}
  </div>
</header>"""


def footer(cfg, month_name, base="", country=None):
    name = html.escape(cfg["site_name"])
    country = country or {}
    sources = country.get("sources_html", '<a href="https://www.bls.gov/cpi/">U.S. Bureau of Labor Statistics</a>, CPI news release tables<br><a href="https://fred.stlouisfed.org/">FRED</a>, Federal Reserve Bank of St. Louis')
    legal = country.get("legal", "Independent analysis, not an official BLS or Federal Reserve product, and not financial advice. BLS data are public domain; FRED data courtesy of the Federal Reserve Bank of St. Louis.")
    about = country.get("about", "What's driving US inflation, component by component.")
    return f"""<footer class="sitefoot">
  <div class="wrap">
    <div class="cols">
      <div><h4>{name}</h4><p>{about} Updated automatically after each monthly CPI release. Latest data: {month_name}.</p></div>
      <div><h4>Sources</h4><p>{sources}</p></div>
      <div><h4>About the numbers</h4><p>How each figure is calculated is explained in the <a href="{base}#method" data-tab-link>Methodology</a> tab, where you can also download the data.</p></div>
    </div>
    <p class="legal">{legal} <a href="/privacy">Privacy policy</a></p>
  </div>
</footer>"""
