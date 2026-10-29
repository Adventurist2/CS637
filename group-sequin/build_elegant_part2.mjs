// Editable second-part slides, using the uploaded deck's type and colour palette.
// Source results remain unchanged. The Open XML assembler preserves original slides.
export function buildElegant(presentation, source, precision, stress, assets) {
 const C={ink:'#102235',blue:'#0074AF',royal:'#244BD6',orange:'#F28C35',teal:'#2CB6A8',red:'#DF5540',muted:'#607487',line:'#D9E2EC',gold:'#FFC000',gray:'#8A8D91'};
 const get=title=>structuredClone(source.find(x=>x.title===title));
 const all=[];
 presentation.slides.keep([]);presentation.theme.defaultFont='Inter';
 const text=(s,t,x,y,w,h,size=26,bold=false,color=C.ink,align='left')=>{
  const b=s.shapes.add({name:t.slice(0,55),geometry:'textbox',position:{left:x,top:y,width:w,height:h},fill:'none',line:{fill:'none',width:0}});
  b.text=[{runs:[{run:t,style:{typeface:'Inter'}}]}];
  b.text.style={fontSize:size,bold,color,alignment:align,wrap:'word',insets:{left:0,right:0,top:0,bottom:0}};return b;
 };
 // Shapes below repeat the reference's black header, yellow dividers and thin cards.
 const rule=(s,x,y,w,color=C.gold)=>s.shapes.add({geometry:'rect',position:{left:x,top:y,width:w,height:1.5},fill:color,line:{width:0,fill:'none'}});
 const card=(s,x,y,w,h)=>s.shapes.add({geometry:'roundRect',position:{left:x,top:y,width:w,height:h},fill:'#FFFFFF',line:{width:1,fill:C.line},borderRadius:12});
 const metric=(s,value,label,x,y,w=350,color=C.royal)=>{text(s,value,x,y,w,64,49,true,color);text(s,label,x,y+72,w,70,23,false,C.ink);};
 const foot=(s,t)=>text(s,t,62,644,1140,45,18,false,C.muted);
 function base(label,title,notes) {
  const s=presentation.slides.add();s.background.fill='#FFFFFF';
  // Coordinates supplied to Artifact Tool are CSS px. Using EMU values here
  // overflowed PowerPoint's custom-path coordinates in the previous export.
  const u=9525,pt=(x,y)=>({x:x/u,y:y/u});
  s.shapes.add({name:'Original black template tab',geometry:'custom',position:{left:129521/u,top:0,width:2749481/u,height:1364786/u},fill:'#000000',line:{fill:'none',width:0},customPaths:[{width:4741280/u,height:2353474/u,commands:[{moveTo:pt(0,0)},{lineTo:pt(4741280,0)},{lineTo:pt(4729949,224399)},{cubicBezTo:{x1:4608502/u,y1:1420269/u,x2:3598552/u,y2:2353474/u,x:2370640/u,y:2353474/u}},{cubicBezTo:{x1:1142728/u,y1:2353474/u,x2:132779/u,y2:1420269/u,x:11331/u,y:224399/u}},{close:{}}]}]});
  text(s,label,31,43,250,70,30,false,'#FFFFFF','center');
  const heading=text(s,title,321,40,900,105,36,true);heading.text=[{runs:[{run:title,style:{typeface:'Inter Display'}}]}];
  text(s,String(15+all.length),1205,681,38,22,14,false,C.blue,'right');
  s.speakerNotes.text=notes||'';all.push(s);return s;
 }
 function chart(s,d,x,y,w,h,{legend=true,min=0,max,labels=false}={}) {
  const palette=[C.royal,C.orange,C.teal,C.gray];
  const chart=s.charts.add(d.type||'line',{
   position:{left:x,top:y,width:w,height:h},categories:d.categories,
   series:d.series.map((r,i)=>({name:r.name,values:r.values.map(x=>Number(x.toPrecision(14))),fill:r.color||palette[i],line:{fill:r.color||palette[i],width:3,style:'solid'}})),
   hasLegend:legend,legend:{position:'bottom',overlay:false,textStyle:{fontFamily:'Inter',fontSize:18,fill:C.ink}},
   title:d.title,titleTextStyle:{fontFamily:'Inter',fontSize:25,fill:C.blue},
   chartFill:'#FFFFFF',chartLine:{fill:'none',width:0},plotAreaFill:'#FFFFFF',plotAreaLine:{fill:'none',width:0},
   barOptions:d.barOptions||{direction:'column',grouping:'clustered',gapWidth:85},lineOptions:{smooth:false},
   dataLabels:d.dataLabels||(labels?{showValue:true,position:'outEnd',numberFormatCode:'0.0',textStyle:{fontSize:17,fill:C.ink}}:undefined),
   xAxis:{title:d.x?{text:d.x,textStyle:{fontSize:20,fill:C.muted}}:undefined,textStyle:{fontFamily:'Inter',fontSize:19,fill:C.muted},line:{fill:C.line,width:1}},
   yAxis:{title:d.y?{text:d.y,textStyle:{fontSize:20,fill:C.muted}}:undefined,min,max,numberFormatCode:'0',textStyle:{fontFamily:'Inter',fontSize:18,fill:C.muted},majorGridlines:{fill:C.line,width:.6,style:'solid'}}
  });
  for(const style of [chart.legend?.textStyle,chart.dataLabels?.textStyle,chart.xAxis?.textStyle,chart.yAxis?.textStyle,chart.titleTextStyle])if(style)style.typeface='Inter';
  for(const axis of [chart.xAxis,chart.yAxis])if(axis.title?.textStyle)axis.title.textStyle.typeface='Inter';
  return chart;
 }
 const recolor=d=>({...d,series:d.series.map((r,i)=>({...r,color:[C.royal,C.orange,C.teal,C.gray][i]}))});
 let s=base('CRITIQUE','Limitations and three extensions',get('Critique and the three extensions').notes);
 const gaps=[['01','Line protection','No investment selection','Which few lines should we protect?'],['02','Response timing','Fixed response epochs','What changes when failures arrive closer together?'],['03','Critical services','All megawatts valued equally','Which services should retain power first?']];
 gaps.forEach(([n,h,g,q],i)=>{const x=65+i*407;text(s,n,x,194,350,58,47,true,C.orange);text(s,h,x,271,350,48,29,true,C.blue);rule(s,x,330,350);text(s,g,x,354,350,72,25,true);text(s,q,x,449,350,105,27);});
 foot(s,'Three implemented studies on the group repository’s SciPy defender');

 s=base('EXTENSION 1','Scenario-aware line protection',get('Extension 1: adaptive line protection').notes);
 text(s,'The attacker adapts after protection',65,175,660,45,28,true,C.blue);
 const steps=[['01','Build complete attack tables','Every eligible ordered pair, for each design demand.'],['02','Choose the next protected line','Minimize the worst loss across design scenarios.'],['03','Search again after protection','Re-evaluate every pair that remains eligible.']];
 steps.forEach(([n,h,b],i)=>{const y=246+i*111;text(s,n,66,y,66,48,34,true,C.orange);text(s,h,150,y,615,38,26,true);text(s,b,150,y+42,585,57,23,false,C.muted);});
 card(s,812,198,402,365);text(s,'Protection budget',839,229,350,42,28,true,C.blue);metric(s,'q = 0–3','Equal cost per protected line',839,304,340);text(s,'Protected lines become ineligible for the modeled failure.',839,468,340,77,23);
 foot(s,'Perfect hardening is a modeling assumption. Greedy selection has no general global guarantee.');

 s=base('EVALUATION','Protection evaluation protocol','Protection: results/extensions/protection.csv, defense_designs.json and validation.json. Exact attack search and exact outer protection enumeration are different checks.');
 [['Case 14','380'],['Case 39','2,070']].forEach(([h,n],i)=>{card(s,64,190+i*201,310,177);text(s,h,88,210+i*201,262,38,27,true,C.blue);text(s,n,88,253+i*201,262,62,43,true);text(s,'ordered failure pairs',88,318+i*201,262,32,21,false,C.muted);});
 const protocol=[['Design / test split','Design seeds 0, 1, 2; test seeds 100–104. Demand varies by ±5%.'],['Six baseline families','Random ×20, flow, betweenness, single-scenario, simultaneous design and exact outer design (q ≤ 2).'],['Independent replay','Fresh exhaustive post-protection searches. Test outcomes never choose the plan.']];
 protocol.forEach(([h,b],i)=>{const y=188+i*139;text(s,h,429,y,778,40,27,true,C.blue);rule(s,429,y+48,777);text(s,b,429,y+64,778,73,25);});
 foot(s,'Attack order matters: (A, B) and (B, A) can produce different physical responses');

 const p14=recolor(get('Protection on case 14').charts[0]),p39=recolor(get('Protection on case 39').charts[0]);
 s=base('RESULTS','Protection on unseen demands',get('Protection on case 14').notes+'\n'+get('Protection on case 39').notes);
 chart(s,{...p14,title:'Case 14'},46,164,588,385,{min:75,max:100});chart(s,{...p39,title:'Case 39'},649,164,588,385,{min:15,max:24});
 text(s,'84.87% vs 93.32%',81,565,540,50,32,true,C.royal);text(s,'Scenario design vs flow, q = 2',81,612,540,31,21,false,C.muted);
 text(s,'20.47% vs 20.35%',685,565,540,50,32,true,C.orange);text(s,'Flow is slightly better at q = 2',685,612,540,31,21,false,C.muted);
 foot(s,'Lower loss is better. Points average the worst eligible attack in each held-out demand scenario.');

 s=base('ROBUSTNESS','Protection under shifted conditions',get('Protection under shifted conditions').notes);
 const keys=['case','seed','ramp','perturb','budget'];const cells=new Map();
 for(const r of stress.filter(r=>r.status==='ok')){const k=keys.map(a=>r[a]).join('|');if(!cells.has(k))cells.set(k,{});cells.get(k)[r.policy]=Number(r.shed_fraction);}
 const deltas=[...cells.values()].filter(r=>r['robust-sequential']!==undefined&&r['initial-flow']!==undefined).map(r=>100*(r['robust-sequential']-r['initial-flow'])).sort((a,b)=>a-b);
 chart(s,{type:'bar',title:'Shifted demand and ramp limits',categories:deltas.map((_,i)=>String(i+1)),series:[{name:'Scenario design minus flow',values:deltas,color:C.orange}],y:'Extra worst loss (percentage points)',x:'Feasible stress comparisons, sorted'},60,179,770,425,{min:Math.floor(Math.min(...deltas)/5)*5,max:40,legend:false});
 metric(s,'10 / 36','Feasible comparisons where scenario design loses to flow',871,205,330,C.orange);
 metric(s,'35.48 pp','Largest excess loss against flow',871,422,330,C.red);
 foot(s,'Plans stay fixed. 36 policy rows have infeasible intact starts and remain separate from attack losses.');

 s=base('EXTENSION 2','Variable response windows',get('Extension 2: matched response windows').notes);
 const patterns=[['Even',[5,5,5]],['Early cluster',[1,1,13]],['Late cluster',[13,1,1]]];
 const d={type:'bar',title:'Same horizon: 15 minutes',categories:patterns.map(x=>x[0]),series:[0,1,2].map((j)=>({name:'Window '+(j+1),values:patterns.map(x=>x[1][j]),color:[C.royal,C.teal,C.orange][j]})),y:'Window duration (minutes)'};
 d.barOptions={direction:'bar',grouping:'stacked',gapWidth:75};d.dataLabels={showValue:true,position:'center',numberFormatCode:'0',textStyle:{fontSize:21,fill:'#FFFFFF'}};chart(s,d,62,184,770,421,{max:15});
 text(s,'Three decisions each',871,224,340,50,29,true,C.blue);text(s,'Sequential: one new failure in each window.',871,303,330,92,26);text(s,'Simultaneous: all failures in the first window, then two more responses.',871,419,330,134,26);
 foot(s,'Longer windows allow more generator adjustment. Sensitivity horizons: 7.5, 15 and 30 minutes.');

 s=base('TIMING','Final loss and the energy proxy',get('Timing: final MW and time weighting differ').notes);
 get('Timing: final MW and time weighting differ').charts.forEach((d,i)=>chart(s,{...recolor(d),title:i?'Snapshot energy proxy (%)':'Final load loss (%)',y:undefined},49+i*604,181,580,385,{max:40,labels:true}));
 text(s,'26.3% to 35.4%',74,577,540,45,30,true,C.royal);text(s,'Sequential final loss: even vs late',74,618,540,29,21,false,C.muted);
 text(s,'16.0% to 7.1%',680,577,540,45,30,true,C.orange);text(s,'Sequential snapshot proxy: even vs late',680,618,540,29,21,false,C.muted);
 foot(s,'Case 118, H = 15 min. Mean per-seed cohort maxima. The proxy does not integrate continuous ramps.');

 s=base('EXTENSION 3','Critical-service operating objectives',get('Extension 3: critical-service response').notes);
 const policies=[['Total-tight','Every MW counts equally','Matched 10⁻⁸ solver precision'],['Weight 2','Critical MW counts twice','A moderate service preference'],['Weight 10','Critical MW counts ten times','A stronger service preference'],['Critical-first','Maximize critical service first','Then maximize total service']];
 policies.forEach(([h,a,b],i)=>{const x=64+i*304;card(s,x,218,280,322);text(s,h,x+22,248,236,52,29,true,i===3?C.orange:C.blue);rule(s,x+22,316,236);text(s,a,x+22,348,236,91,27,true);text(s,b,x+22,458,236,60,22,false,C.muted);});
 foot(s,'Synthetic groups of positive-demand buses. All policies share initial dispatch and attack sequences.');

 s=base('PRIORITY','Critical service at the nominal setting',get('Critical service at the nominal setting').notes);
 const priorityChart=get('Critical service at the nominal setting').charts[0];priorityChart.title='Critical service by policy';priorityChart.series.forEach((r,i)=>r.color=[C.gray,C.royal,C.teal,C.orange][i]);
 chart(s,priorityChart,56,178,838,434,{max:110,labels:false});
 text(s,'67% to 100%',935,226,280,57,41,true,C.royal);text(s,'Case 39 critical service retained',935,300,280,82,23);
 text(s,'77% to 100%',935,440,280,57,41,true,C.teal);text(s,'Case 118 critical service retained',935,514,280,82,23);
 foot(s,'25% of positive-demand buses, ramp 0.1. Larger cases use a shared sampled cohort, not all attacks.');

 s=base('TRADE-OFFS','Priority gains and adverse cases',get('Critical gains have costs and adverse cases').notes);
 const examples=[{x:64,heading:'Selected positive case',sub:'Case 39, attack [39, 14]',value:'+1,573 MW',label:'more critical demand preserved',cost:'+121 MW total loss',color:C.royal},{x:674,heading:'Selected adverse case',sub:'Case 14, attack [4, 2]',value:'−240 MW',label:'critical service lost versus baseline',cost:'+323 MW total loss',color:C.red}];
 examples.forEach(a=>{card(s,a.x,187,546,401);text(s,a.heading,a.x+28,213,490,45,28,true,C.blue);text(s,a.sub,a.x+28,265,490,32,22,false,C.muted);rule(s,a.x+28,310,490);metric(s,a.value,a.label,a.x+28,342,480,a.color);text(s,a.cost,a.x+28,509,480,46,28,true,C.orange);});
 foot(s,'Selected extremes against total-tight. Current-step priorities can create a worse state after a later failure.');

 s=base('SENSITIVITY','Critical service across response speeds','Source: results/extensions/priority_precision_summary.csv. Group fraction 0.25, three demand seeds. Each curve averages per-seed minima over shared attack cohorts, not a guarantee against every possible attack. One synthetic assignment per group size.');
 for(const [j,name] of ['39','118'].entries()) {
  const ps=['total-tight','weight-2','weight-10','critical-first'];
  const d={type:'line',title:'Case '+name,categories:['0.025','0.10','0.50'],series:ps.map((p,i)=>({name:['Total-tight','Weight 2','Weight 10','Critical-first'][i],values:[.025,.1,.5].map(r=>100*precision.find(x=>String(x.case)===name&&x.fraction===.25&&x.ramp===r&&x.policy===p).critical_retained_fraction),color:[C.gray,C.royal,C.teal,C.orange][i]})),x:'Ramp fraction',y:'Worst critical retained (%)'};
  chart(s,d,48+j*605,177,585,435,{max:105});
 }
 foot(s,'Faster response changes the result. Group sizes also vary over 10%, 25% and 50% of load buses.');

 s=base('VERIFICATION','Correctness and boundaries of the results','Sources: results/extensions/validation.json, default_compatibility.json and original_benchmark_status.json. Unchanged original checker fails missing case162 k=8 after an infeasible eighth response. Passing extension tests and reproducing every paper result are separate claims.');
 metric(s,'16','Extension tests pass',67,208,350,C.royal);metric(s,'26','State probes match untouched group code',475,208,350,C.blue);metric(s,'Exact replay','Saved protection maxima agree with fresh exhaustive searches',883,208,330,C.teal);
 rule(s,65,419,1148);text(s,'Evaluation boundaries',65,456,525,46,29,true,C.blue);
 text(s,'Shared attack cohorts support fair comparisons. Small protection cases use exhaustive search.',65,518,520,104,26);
 text(s,'Original benchmark: case 162 at k = 8 is missing after an infeasible response.',672,463,535,103,27,true,C.orange);text(s,'The full paper benchmark remains incomplete.',672,579,535,42,23,false,C.muted);
 foot(s,'Numerical checks support these measured studies. They do not remove the search and model limitations.');

 s=base('CODE','Where the extensions are implemented','Files: grid_model.py, extensions.py, run_extensions.py, audit_extensions.py. Full ordered prefixes form cache keys. Source architecture figure reproduced from the uploaded deck, originally Chio et al., ICCPS 2025. All extension responses use the group SciPy defender.');
 const files=[['grid_model.py','Physical response, optional service weights and critical-first floors'],['extensions.py','Attack tables, protection selection and timed traces'],['run_extensions.py','Scenarios, common cohorts, sweeps and summaries'],['audit_extensions.py','Fresh replay and matched-precision comparisons']];
 files.forEach(([f,b],i)=>{const y=181+i*108;text(s,f,65,y,465,40,27,true,C.blue);text(s,b,65,y+44,490,58,23,false,C.muted);});
 text(s,'Same physical defender',643,194,565,48,29,true,C.blue);
 s.images.add({blob:assets.architecture,contentType:'image/png',alt:'SEQUIN architecture figure from the uploaded presentation',fit:'contain',position:{left:640,top:279,width:576,height:226}});
 text(s,'New experiments wrap the group implementation’s existing response model.',643,543,565,85,26);
 foot(s,'Code and results: group-sequin/EXTENSIONS_README.md');

 s=base('DEMONSTRATION','Demonstration and interpretation','The screenshot is the local output/demonstration.html with recorded SciPy traces. It selects saved data, with no optimizer in the browser. The priority panel includes both selected positive and adverse cases.');
 s.images.add({blob:assets.demo,contentType:'image/png',alt:'Actual offline demonstration showing protected lines and adaptive attack results',fit:'contain',position:{left:62,top:183,width:738,height:425}});
 const demoSteps=[['Protection','Protected lines and the replacement worst attack'],['Timing','The same attack under even, early and late windows'],['Priority','One selected gain and one selected harm']];
 demoSteps.forEach(([h,b],i)=>{const y=192+i*143;text(s,h,849,y,363,39,28,true,C.blue);text(s,b,849,y+48,363,85,24);});
 foot(s,'Open output/demonstration.html. Selectors replay saved traces; CSV and JSON retain the detailed evidence.');

 s=base('CONCLUSIONS','Improvement, mixed evidence and failure',get('What the results establish').notes);
 const conclusions=[['Protection','Useful gains','Case 14 improves; held-out and stress failures remain.'],['Timing','Different outcomes','Failure spacing changes final loss and the energy proxy.'],['Critical service','Benefits with costs','Selected service improves; other loss and later harm can increase.']];
 conclusions.forEach(([h,a,b],i)=>{const x=65+i*407;text(s,h,x,202,350,48,30,true,C.blue);rule(s,x,268,350);text(s,a,x,302,350,76,30,true,[C.royal,C.orange,C.teal][i]);text(s,b,x,410,350,145,27);});
 foot(s,'The contribution is a measured investigation of when these choices help, tie or fail.');

 s=base('FUTURE WORK','Next steps motivated by the results',get('Future work motivated by the failures').notes);
 const future=[['Stress failures','Train protection across demand and response-speed uncertainty.'],['Sampled larger cases','Search more strongly for attacks against critical demand. Vary priority groups.'],['Model assumptions','Compare restart rules and dispatch ties. Add lookahead, continuous ramps, restoration, storage and AC checks.']];
 future.forEach(([h,b],i)=>{const y=190+i*141;text(s,String(i+1).padStart(2,'0'),66,y,82,48,39,true,C.orange);text(s,h,170,y,1035,40,29,true,C.blue);text(s,b,170,y+54,1035,77,26);});
 foot(s,'The strongest next experiments follow the failures and uncertainties already observed.');
 return {slides:all.length,nativeCharts:all.reduce((n,s)=>n+s.charts.items.length,0)};
}
