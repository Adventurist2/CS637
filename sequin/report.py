"""Portable result files, scientific plots, and an offline sequence viewer."""

import csv
import html
import json
import os
from pathlib import Path

import networkx as nx
import numpy as np


def write_json(path, value):
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(value, indent=2, allow_nan=False), encoding="utf-8")


def write_csv(path, rows):
    if not rows:
        return
    path = Path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    keys = list(dict.fromkeys(key for row in rows for key in row))
    with path.open("w", encoding="utf-8", newline="") as stream:
        writer = csv.DictWriter(stream, fieldnames=keys)
        writer.writeheader()
        for row in rows:
            writer.writerow({k: json.dumps(v) if isinstance(v, (list, dict)) else v for k, v in row.items()})


def comparison_plot(rows, path):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mplconfig"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt

    valid = [r for r in rows if r.get("status") == "ok"]
    if not valid:
        return
    cases = sorted(set(r["case"] for r in valid))
    fig, axes = plt.subplots(len(cases), 2, figsize=(12, 3.5 * len(cases)), squeeze=False)
    for i, case in enumerate(cases):
        subset = [r for r in valid if r["case"] == case]
        ramp_axis = len(set(r["k"] for r in subset)) == 1 and len(set(r["ramp_fraction"] for r in subset)) > 1
        xkey, splitkey = ("ramp_fraction", "k") if ramp_axis else ("k", "ramp_fraction")
        for method in sorted(set(r["method"] for r in subset)):
            for split in sorted(set(r[splitkey] for r in subset)):
                selected = [r for r in subset if r["method"] == method and r[splitkey] == split]
                if not selected:
                    continue
                xs = sorted(set(r[xkey] for r in selected))
                shed = [np.mean([r["shed_fraction"] * 100 for r in selected if r[xkey] == x]) for x in xs]
                std = [np.std([r["shed_fraction"] * 100 for r in selected if r[xkey] == x]) for x in xs]
                runtime = [np.mean([r["seconds"] for r in selected if r[xkey] == x]) for x in xs]
                label = f"{method}, {'k' if ramp_axis else 'ramp'}={split:g}"
                axes[i, 0].errorbar(xs, shed, yerr=std, marker="o", capsize=3, label=label)
                axes[i, 1].plot(xs, runtime, marker="o", label=label)
        for ax in axes[i]:
            ax.set_title(case.replace("pglib_opf_", ""))
            ax.set_xlabel("Generator ramp fraction" if ramp_axis else "Number of failed lines (k)")
            ax.grid(alpha=0.2)
        axes[i, 0].set_ylabel("Final demand shed (%)\nmean ± population SD across seeds")
        axes[i, 1].set_ylabel("Search time (seconds)")
        axes[i, 1].set_yscale("symlog", linthresh=0.1)
    handles, labels = axes[0, 0].get_legend_handles_labels()
    fig.legend(handles, labels, loc="outside lower center", ncol=3, fontsize=8)
    fig.suptitle("Independent SEQUIN implementation: measured benchmark results", fontsize=13)
    fig.tight_layout(rect=(0, 0.09, 1, 0.97))
    fig.savefig(path, dpi=160, bbox_inches="tight")
    plt.close(fig)


def sequence_viewer(path, case, trace, sequence, title="Sequential outage simulation"):
    graph = nx.MultiGraph()
    graph.add_nodes_from(range(case.nbus))
    graph.add_edges_from(zip(case.branch_from.tolist(), case.branch_to.tolist()))
    positions = nx.spring_layout(graph, seed=7, iterations=100)
    nodes = [{"id": int(case.bus_ids[i]), "x": float(positions[i][0]), "y": float(positions[i][1]),
              "demand_mw": float(case.demand[i] * case.base_mva),
              "generator": bool(np.any(case.gen_bus == i))} for i in range(case.nbus)]
    edges = [{"id": i + 1, "from": int(case.branch_from[i]), "to": int(case.branch_to[i]),
              "rating_mw": float(case.rating[i] * case.base_mva) if np.isfinite(case.rating[i]) else None}
             for i in range(case.nbranch)]
    payload = {"nodes": nodes, "edges": edges, "trace": [s.to_dict(case) for s in trace],
               "sequence": list(sequence), "metadata": case.metadata()}
    template = r'''<!doctype html>
<html lang="en"><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<title>SEQUIN sequence viewer</title><style>
body{font-family:system-ui,sans-serif;margin:0;background:#eef2f7;color:#162638}
main{max-width:1150px;margin:auto;padding:25px}h1{font-size:25px;margin:0 0 8px}
.card{background:white;border-radius:12px;padding:20px;margin-top:18px;box-shadow:0 3px 12px #15243610}
.stats{display:flex;gap:25px;flex-wrap:wrap}.stats strong{font-size:24px;display:block}
button{background:#214d75;border:0;color:white;border-radius:6px;padding:9px 16px;cursor:pointer}
input{width:min(60vw,520px);vertical-align:middle}svg{width:100%;height:580px}
.muted{color:#596b7a;font-size:14px}.legend{display:flex;gap:20px;font-size:13px;flex-wrap:wrap}
</style><main><h1>__TITLE__</h1><div class="muted">Independent DC steady-state model · public benchmark network</div>
<div class="card stats"><div><strong id="step"></strong>Failure round</div><div><strong id="shed"></strong>Demand shed</div>
<div><strong id="fraction"></strong>Share of original demand</div><div><strong id="served"></strong>Demand served</div></div>
<div class="card"><button id="back">Previous</button> <input id="slider" type="range" min="0" max="__MAX__" value="0"> <button id="next">Next</button>
<p id="sequence"></p><svg id="grid" viewBox="0 0 1000 580" role="img" aria-label="Power grid state"></svg>
<div class="legend"><span>Blue lines: available (width reflects flow)</span><span>Red dashed lines: failed</span><span>Orange nodes: shed demand</span><span>Outlined nodes: generators</span></div></div>
<p class="muted">Hover over components for values. This shows successive DC operating states, not frequency or voltage transients. Layout is schematic.</p></main>
<script>const D=__DATA__;const $=id=>document.getElementById(id),ns='http://www.w3.org/2000/svg';
function el(tag,attrs){let a=document.createElementNS(ns,tag);for(let k in attrs)a.setAttribute(k,attrs[k]);return a}
function draw(){const n=+$('slider').value,s=D.trace[n];$('step').textContent=n+' / '+(D.trace.length-1);$('shed').textContent=s.shed_mw.toFixed(2)+' MW';
$('fraction').textContent=(100*s.shed_fraction).toFixed(1)+'%';$('served').textContent=s.served_mw.reduce((a,b)=>a+b,0).toFixed(2)+' MW';
$('sequence').textContent='Sequence: '+D.sequence.map((x,i)=>(i<n?'✓ ':'')+'Line '+x).join(' → ');$('grid').replaceChildren();
const xy=i=>[500+D.nodes[i].x*415,290+D.nodes[i].y*235];
for(let e of D.edges){let [x1,y1]=xy(e.from),[x2,y2]=xy(e.to),off=s.failed_lines.includes(e.id),f=s.flow_mw[e.id-1];
let a=el('line',{x1,y1,x2,y2,stroke:off?'#d45050':'#397fbb','stroke-width':off?2:1+3*Math.min(1,Math.abs(f)/(e.rating_mw||1000)),'stroke-dasharray':off?'6 5':'none'});
let t=el('title',{});t.textContent='Line '+e.id+' | '+D.nodes[e.from].id+'–'+D.nodes[e.to].id+' | '+f.toFixed(2)+' MW'+(off?' | failed':'');a.append(t);$('grid').append(a)}
D.nodes.forEach((b,i)=>{let[x,y]=xy(i),shed=Math.max(0,b.demand_mw-s.served_mw[i]),a=el('circle',{cx:x,cy:y,r:b.generator?8:6,fill:shed>0.01?'#df923a':'#dde9f2',stroke:b.generator?'#183753':'#7192ac','stroke-width':b.generator?3:1});
let t=el('title',{});t.textContent='Bus '+b.id+' | demand '+b.demand_mw.toFixed(2)+' MW | shed '+shed.toFixed(2)+' MW';a.append(t);$('grid').append(a);
if(D.nodes.length<65){let z=el('text',{x:x+10,y:y+4,'font-size':11,fill:'#263a4b'});z.textContent=b.id;$('grid').append(z)}})}
$('slider').oninput=draw;$('back').onclick=()=>{$('slider').value=Math.max(0,+$('slider').value-1);draw()};$('next').onclick=()=>{$('slider').value=Math.min(D.trace.length-1,+$('slider').value+1);draw()};draw();</script></html>'''
    content = template.replace("__TITLE__", html.escape(title)).replace("__MAX__", str(len(trace) - 1))
    content = content.replace("__DATA__", json.dumps(payload, allow_nan=False).replace("<", "\\u003c"))
    Path(path).parent.mkdir(parents=True, exist_ok=True)
    Path(path).write_text(content, encoding="utf-8")


def order_plot(rows, simultaneous_shed, path):
    os.environ.setdefault("MPLCONFIGDIR", str(Path(__file__).resolve().parents[1] / ".mplconfig"))
    import matplotlib
    matplotlib.use("Agg")
    import matplotlib.pyplot as plt
    fig, ax = plt.subplots(figsize=(9, 4.8))
    ax.bar(range(len(rows)), [r["shed_mw"] for r in rows], color="#397fbb", label="Sequential response")
    ax.axhline(simultaneous_shed, color="#c44444", linestyle="--", label="Same set, simultaneous response")
    ax.set_xticks(range(len(rows)), [" → ".join(map(str, r["sequence"])) for r in rows], rotation=35, ha="right")
    ax.set_xlabel("Order of the same failed lines")
    ax.set_ylabel("Final demand shed (MW)")
    ax.set_title("Failure order changes the outcome")
    ax.legend()
    fig.tight_layout()
    fig.savefig(path, dpi=160)
    plt.close(fig)
