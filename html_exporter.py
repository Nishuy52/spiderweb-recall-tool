import json
from models import Person

PLATOON_PALETTE = [
    "#4E79A7","#F28E2B","#E15759","#76B7B2","#59A14F",
    "#EDC948","#B07AA1","#FF9DA7","#9C755F","#BAB0AC"
]

def export_html(people: list[Person], output_path: str):
    available = [p for p in people if p.available]
    platoons  = sorted(set(p.platoon for p in available))
    platoon_color = {plt: PLATOON_PALETTE[i % len(PLATOON_PALETTE)] for i, plt in enumerate(platoons)}

    nodes = []
    for p in available:
        nodes.append({
            "id":        p.name,
            "label":     f"{p.rank}\n{p.name}",
            "rank":      p.rank,
            "platoon":   p.platoon,
            "appt":      p.appt,
            "initiator": p.is_initiator,
            "color":     "#FFD700" if p.is_initiator else platoon_color.get(p.platoon, "#aaa"),
            "calls":     len(p.calls),
            "calledBy":  len(p.called_by),
        })

    links = []
    seen = set()
    for p in available:
        for c in p.calls:
            key = (p.name, c.name)
            if key not in seen:
                seen.add(key)
                links.append({"source": p.name, "target": c.name})

    nodes_json = json.dumps(nodes)
    links_json = json.dumps(links)
    platoon_legend = json.dumps([{"platoon": plt, "color": platoon_color[plt]} for plt in platoons])

    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<title>Spiderweb Recall Chart</title>
<style>
  * {{ box-sizing: border-box; margin: 0; padding: 0; }}
  body {{ font-family: Arial, sans-serif; background: #0d1117; color: #e6edf3; height: 100vh; display: flex; flex-direction: column; }}
  header {{ background: #161b22; padding: 14px 24px; border-bottom: 1px solid #30363d; display: flex; align-items: center; gap: 16px; flex-wrap: wrap; }}
  header h1 {{ font-size: 18px; font-weight: 700; color: #FFD700; letter-spacing: 1px; }}
  header .subtitle {{ font-size: 12px; color: #8b949e; }}
  .controls {{ display: flex; gap: 10px; align-items: center; margin-left: auto; flex-wrap: wrap; }}
  .controls label {{ font-size: 12px; color: #8b949e; }}
  .controls input[type=range] {{ width: 100px; accent-color: #FFD700; }}
  .btn {{ background: #21262d; border: 1px solid #30363d; color: #e6edf3; padding: 5px 12px; border-radius: 6px; cursor: pointer; font-size: 12px; }}
  .btn:hover {{ background: #30363d; }}
  .main {{ display: flex; flex: 1; overflow: hidden; }}
  #graph {{ flex: 1; }}
  #sidebar {{ width: 260px; background: #161b22; border-left: 1px solid #30363d; padding: 16px; overflow-y: auto; font-size: 13px; }}
  #sidebar h2 {{ font-size: 14px; font-weight: 600; margin-bottom: 12px; color: #FFD700; }}
  .legend-item {{ display: flex; align-items: center; gap: 8px; margin-bottom: 7px; font-size: 12px; }}
  .legend-dot {{ width: 14px; height: 14px; border-radius: 50%; flex-shrink: 0; }}
  .info-box {{ background: #0d1117; border: 1px solid #30363d; border-radius: 8px; padding: 12px; margin-top: 12px; line-height: 1.7; }}
  .info-box .name {{ font-weight: 700; font-size: 14px; color: #FFD700; margin-bottom: 4px; }}
  .info-box .tag {{ display: inline-block; background: #21262d; border-radius: 4px; padding: 1px 6px; font-size: 11px; margin: 1px; cursor: default; border-bottom: 1px dotted #8b949e; }}
  .info-box .tag[title]:hover::after {{ content: attr(title); position: absolute; background: #30363d; color: #e6edf3; border: 1px solid #58a6ff; border-radius: 4px; padding: 3px 8px; font-size: 11px; white-space: nowrap; z-index: 10; margin-top: 18px; margin-left: -40px; pointer-events: none; }}
  .info-box .tag {{ position: relative; }}
  .stat-grid {{ display: grid; grid-template-columns: 1fr 1fr; gap: 6px; margin-top: 12px; }}
  .stat-box {{ background: #0d1117; border: 1px solid #30363d; border-radius: 6px; padding: 8px; text-align: center; }}
  .stat-box .val {{ font-size: 20px; font-weight: 700; color: #FFD700; }}
  .stat-box .lbl {{ font-size: 10px; color: #8b949e; margin-top: 2px; }}
  .node-label {{ font-size: 9px; fill: #e6edf3; pointer-events: none; text-anchor: middle; }}
  .search-box {{ width: 100%; background: #0d1117; border: 1px solid #30363d; color: #e6edf3; border-radius: 6px; padding: 6px 10px; font-size: 12px; margin-bottom: 10px; }}
  .search-box:focus {{ outline: none; border-color: #FFD700; }}
  hr {{ border: none; border-top: 1px solid #30363d; margin: 12px 0; }}
</style>
</head>
<body>
<header>
  <div>
    <h1>⚡ Spiderweb Recall Chart</h1>
    <div class="subtitle">Call chain visualisation — hover nodes to inspect</div>
  </div>
  <div class="controls">
    <label>Link strength <input type="range" id="strengthSlider" min="0" max="100" value="40"></label>
    <label>Charge <input type="range" id="chargeSlider" min="10" max="300" value="120"></label>
    <button class="btn" onclick="resetZoom()">Reset View</button>
  </div>
</header>
<div class="main">
  <svg id="graph"></svg>
  <div id="sidebar">
    <h2>Legend</h2>
    <div class="legend-item"><div class="legend-dot" style="background:#FFD700;border:2px solid #fff;"></div><span>Initiator (OC/CSM/2IC)</span></div>
    <div class="legend-item"><div style="width:32px;height:3px;background:#56d364;border-radius:2px;flex-shrink:0;position:relative;"><span style="position:absolute;right:-4px;top:-4px;font-size:9px;color:#56d364">▶</span></div><span>Outbound call</span></div>
    <div class="legend-item"><div style="width:32px;height:3px;background:#ffa198;border-radius:2px;flex-shrink:0;position:relative;"><span style="position:absolute;right:-4px;top:-4px;font-size:9px;color:#ffa198">▶</span></div><span>Inbound call</span></div>
    <div id="platoon-legend"></div>
    <hr>
    <input class="search-box" id="searchBox" type="text" placeholder="Search name...">
    <div id="node-info"><span style="color:#8b949e;font-size:12px;">Click a node to see details</span></div>
    <hr>
    <h2>Statistics</h2>
    <div class="stat-grid" id="stats"></div>
  </div>
</div>
<script src="https://cdnjs.cloudflare.com/ajax/libs/d3/7.8.5/d3.min.js"></script>
<script>
const nodesData = {nodes_json};
const linksData = {links_json};
const platoonLegend = {platoon_legend};

// Build legend
const legEl = document.getElementById('platoon-legend');
platoonLegend.forEach(p => {{
  legEl.innerHTML += `<div class="legend-item"><div class="legend-dot" style="background:${{p.color}}"></div><span>Platoon ${{p.platoon}}</span></div>`;
}});

// Stats
const avail = nodesData.length;
const reached = nodesData.filter(n => n.calledBy > 0 || n.initiator).length;
document.getElementById('stats').innerHTML = `
  <div class="stat-box"><div class="val">${{avail}}</div><div class="lbl">Available</div></div>
  <div class="stat-box"><div class="val">${{reached}}</div><div class="lbl">Reached</div></div>
  <div class="stat-box"><div class="val">${{nodesData.filter(n=>n.initiator).length}}</div><div class="lbl">Initiators</div></div>
  <div class="stat-box"><div class="val">${{(reached/avail*100).toFixed(0)}}%</div><div class="lbl">Coverage</div></div>
`;

const svg = d3.select('#graph');
const w = () => svg.node().getBoundingClientRect().width;
const h = () => svg.node().getBoundingClientRect().height;

// arrow-out: outbound calls (green)
svg.append('defs').append('marker')
  .attr('id','arrow-out').attr('viewBox','0 -4 10 8').attr('refX',18).attr('refY',0)
  .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
  .append('path').attr('d','M0,-4L10,0L0,4').attr('fill','#3fb950').attr('opacity',0.85);

// arrow-in: inbound calls (orange)
svg.append('defs').append('marker')
  .attr('id','arrow-in').attr('viewBox','0 -4 10 8').attr('refX',18).attr('refY',0)
  .attr('markerWidth',6).attr('markerHeight',6).attr('orient','auto')
  .append('path').attr('d','M0,-4L10,0L0,4').attr('fill','#f78166').attr('opacity',0.85);

// highlighted versions
svg.append('defs').append('marker')
  .attr('id','arrow-out-hl').attr('viewBox','0 -4 10 8').attr('refX',18).attr('refY',0)
  .attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto')
  .append('path').attr('d','M0,-4L10,0L0,4').attr('fill','#56d364');

svg.append('defs').append('marker')
  .attr('id','arrow-in-hl').attr('viewBox','0 -4 10 8').attr('refX',18).attr('refY',0)
  .attr('markerWidth',7).attr('markerHeight',7).attr('orient','auto')
  .append('path').attr('d','M0,-4L10,0L0,4').attr('fill','#ffa198');

const g = svg.append('g');
const zoom = d3.zoom().scaleExtent([0.1,4]).on('zoom', e => g.attr('transform', e.transform));
svg.call(zoom);

const nodes = nodesData.map(d => ({{...d}}));
const links = linksData.map(d => ({{...d}}));

let sim = buildSim(120, 40);

function buildSim(charge, strength) {{
  return d3.forceSimulation(nodes)
    .force('link', d3.forceLink(links).id(d=>d.id).distance(90).strength(strength/100))
    .force('charge', d3.forceManyBody().strength(-charge))
    .force('center', d3.forceCenter(w()/2, h()/2))
    .force('collision', d3.forceCollide(22));
}}

const link = g.append('g').selectAll('line').data(links).join('line')
  .attr('stroke','#3fb950').attr('stroke-width',1.5).attr('opacity',0.4)
  .attr('marker-end','url(#arrow-out)');

const node = g.append('g').selectAll('g').data(nodes).join('g')
  .attr('cursor','pointer')
  .call(d3.drag()
    .on('start', (e,d) => {{ if(!e.active) sim.alphaTarget(0.3).restart(); d.fx=d.x; d.fy=d.y; }})
    .on('drag',  (e,d) => {{ d.fx=e.x; d.fy=e.y; }})
    .on('end',   (e,d) => {{ if(!e.active) sim.alphaTarget(0); d.fx=null; d.fy=null; }}))
  .on('click', showInfo)
  .on('mouseover', highlight)
  .on('mouseout',  unhighlight);

node.append('circle')
  .attr('r', d => d.initiator ? 20 : 14)
  .attr('fill', d => d.color)
  .attr('stroke', d => d.initiator ? '#fff' : '#30363d')
  .attr('stroke-width', d => d.initiator ? 2.5 : 1);

node.append('text').attr('class','node-label').attr('dy','-10px')
  .text(d => {{
    const combined = d.rank + ' ' + d.id;
    return combined.length > 16 ? combined.slice(0,15)+'\u2026' : combined;
  }});

sim.on('tick', () => {{
  link.attr('x1',d=>d.source.x).attr('y1',d=>d.source.y)
      .attr('x2',d=>d.target.x).attr('y2',d=>d.target.y);
  node.attr('transform',d=>`translate(${{d.x}},${{d.y}})`);
}});

function highlight(e, d) {{
  const related = new Set([d.id, ...links.filter(l=>l.source.id===d.id||l.target.id===d.id).flatMap(l=>[l.source.id,l.target.id])]);
  node.attr('opacity', n => related.has(n.id) ? 1 : 0.15);
  link
    .attr('opacity', l => l.source.id===d.id||l.target.id===d.id ? 1 : 0.04)
    .attr('stroke', l => {{
      if (l.source.id===d.id) return '#56d364';  // outbound = bright green
      if (l.target.id===d.id) return '#ffa198';  // inbound  = bright orange
      return '#3fb950';
    }})
    .attr('stroke-width', l => l.source.id===d.id||l.target.id===d.id ? 2.5 : 1.5)
    .attr('marker-end', l => {{
      if (l.source.id===d.id) return 'url(#arrow-out-hl)';
      if (l.target.id===d.id) return 'url(#arrow-in-hl)';
      return 'url(#arrow-out)';
    }});
}}
function unhighlight() {{
  node.attr('opacity',1);
  link.attr('stroke','#3fb950').attr('stroke-width',1.5).attr('opacity',0.4).attr('marker-end','url(#arrow-out)');
}}

function showInfo(e, d) {{
  const nodeMap = Object.fromEntries(nodesData.map(n => [n.id, n]));
  const callsList = links.filter(l=>l.source.id===d.id).map(l=>{{
    const n = nodeMap[l.target.id];
    const appt = n && n.appt ? n.appt : '';
    const title = appt ? ` title="${{appt}}"` : '';
    return `<span class="tag"${{title}}>${{n ? n.rank+' '+n.id : l.target.id}}</span>`;
  }}).join(' ') || '<i style="color:#8b949e">None</i>';
  const calledByList = links.filter(l=>l.target.id===d.id).map(l=>{{
    const n = nodeMap[l.source.id];
    const appt = n && n.appt ? n.appt : '';
    const title = appt ? ` title="${{appt}}"` : '';
    return `<span class="tag"${{title}}>${{n ? n.rank+' '+n.id : l.source.id}}</span>`;
  }}).join(' ') || '<i style="color:#8b949e">None</i>';
  document.getElementById('node-info').innerHTML = `
    <div class="info-box">
      <div class="name">${{d.rank}} ${{d.id}}</div>
      <div>Platoon: <b>${{d.platoon}}</b>${{d.appt ? ' · '+d.appt : ''}}</div>
      ${{d.initiator ? '<div style="color:#FFD700;font-size:11px;margin-top:4px;">★ Initiator</div>' : ''}}
      <hr style="margin:8px 0">
      <div><b>Calls:</b> ${{callsList}}</div>
      <div style="margin-top:6px"><b>Called by:</b> ${{calledByList}}</div>
    </div>`;
}}

document.getElementById('searchBox').addEventListener('input', function() {{
  const q = this.value.toLowerCase();
  if(!q) {{ node.attr('opacity',1); link.attr('opacity',0.5); return; }}
  const match = new Set(nodes.filter(n=>n.id.toLowerCase().includes(q)).map(n=>n.id));
  node.attr('opacity', n => match.has(n.id) ? 1 : 0.15);
  link.attr('opacity', l => match.has(l.source.id)||match.has(l.target.id) ? 0.85 : 0.04)
      .attr('stroke', l => match.has(l.source.id) ? '#56d364' : match.has(l.target.id) ? '#ffa198' : '#3fb950');
}});

document.getElementById('strengthSlider').addEventListener('input', function() {{
  sim.force('link').strength(+this.value/100);
  sim.alpha(0.3).restart();
}});
document.getElementById('chargeSlider').addEventListener('input', function() {{
  sim.force('charge').strength(-this.value);
  sim.alpha(0.3).restart();
}});

function resetZoom() {{
  svg.transition().duration(400).call(zoom.transform, d3.zoomIdentity);
}}

window.addEventListener('resize', () => {{
  sim.force('center', d3.forceCenter(w()/2, h()/2)).alpha(0.1).restart();
}});
</script>
</body>
</html>"""

    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
