// New slides only. The uploaded deck's original parts are preserved by the
// separate Open XML assembler; this builder never rewrites original slides.
export function build(presentation,source,precision){
  const get=title=>structuredClone(source.find(x=>x.title===title));
  const slides=[];
  const add=(label,title,content)=>slides.push({label,title,...content});
  const navy='#102235',blue='#0074AF',muted='#607487';
  add('Critique','Limitations and three extensions',get('Critique and the three extensions'));
  add('Extension 1','Scenario-aware line protection',get('Extension 1: adaptive line protection'));
  add('Extension 1','Protection evaluation protocol',{
    table:[['Choice','Design and evaluation'],['Networks and attacks','Cases 14 / 39, all 380 / 2,070 ordered N-2 pairs'],['Scenario split','Design seeds 0 / 1 / 2; held-out seeds 100-104; +/-5% demand'],['Budgets and baselines','q=0-3; random x20, flow, betweenness, single-scenario, simultaneous design'],['Independent check','Exact outer design for q<=2; fresh exhaustive post-protection replay']],
    footer:'The attacker adapts after protection. Test outcomes never select the plan.',
    notes:'Protection makes a line ineligible for the modeled failure but does not change eligible sequence physics. This makes complete-table filtering exact under the fixed group response policy. Equal protection cost and perfect hardening are assumptions. Group results/extensions/protection.csv and defense_designs.json.'
  });
  const p14=get('Protection on case 14'),p39=get('Protection on case 39');
  p14.charts[0].title='Case 14';p39.charts[0].title='Case 39';
  add('Extension 1','Protection results on unseen demands',{
    charts:[p14.charts[0],p39.charts[0]],
    footer:'q=2: Case 14 robust 84.87% vs flow 93.32%. Case 39 robust 20.47% vs flow 20.35%.',
    notes:p14.notes+'\n'+p39.notes+'\nEach point averages the worst eligible attack loss per held-out demand scenario. Different plans can face different worst attacks.'
  });
  add('Robustness','Protection under shifted conditions',get('Protection under shifted conditions'));
  add('Extension 2','Variable response windows',get('Extension 2: matched response windows'));
  add('Extension 2','Timing changes the final loss and energy proxy',get('Timing: final MW and time weighting differ'));
  add('Extension 3','Critical-service operating objectives',get('Extension 3: critical-service response'));
  add('Extension 3','Critical service at the nominal setting',get('Critical service at the nominal setting'));
  add('Tradeoffs','Priority gains and adverse cases',get('Critical gains have costs and adverse cases'));
  const colors=['#646C73','#244BD6','#F28C35','#2CB6A8'];
  const policies=['total-tight','weight-2','weight-10','critical-first'];
  const charts=['39','118'].map(name=>({type:'line',title:'Case '+name,categories:['0.025','0.10','0.50'],
    series:policies.map((p,i)=>({name:p,values:[.025,.1,.5].map(r=>100*precision.find(x=>String(x.case)===name&&x.fraction===.25&&x.ramp===r&&x.policy===p).critical_retained_fraction),color:colors[i]})),
    x:'Ramp fraction',y:'Worst critical retained (%)',min:0,max:105}));
  add('Sensitivity','Critical service across response speeds',{
    charts,footer:'25% of positive-load buses, three demand seeds. Larger-grid results cover a shared sampled attack cohort.',
    notes:'The plot uses total-tight to match priority-policy MIP precision. Curves average per-seed cohort minima, not guarantees against all possible attacks. Synthetic groups use seed 17. Group size/composition also varies over 10%,25%,50% at ramp 0.1 in the saved CSV. Source: results/extensions/priority_precision_summary.csv.'
  });
  add('Evaluation','Correctness and boundaries of the results',{
    body:['16 extension tests pass. 26 state probes match the untouched group code exactly.','Fresh exhaustive protection replays agree with saved table maxima.','Priority policies and timing comparators share the same attack cohort.','Original benchmark checker: case 162, k=8 is missing after an infeasible response.'],
    footer:'Exact small cases and sampled larger cases support different levels of claim.',
    notes:'The original default driver produced 311 measured rows and seven plots. The unchanged checker fails the six-case flow-coverage assertion. Fresh replay of [83,5,19,228,196,177,212,219] confirms the eighth MILP is infeasible. This new run is separate from the earlier results retained in the first part. Extension experiments never silently skip failed responses. Source: validation.json, default_compatibility.json and original_benchmark_status.json.'
  });
  add('Code','Where the extensions are implemented',{
    table:[['File','What to review'],['grid_model.py','Optional weights and critical-first service floors in defend()'],['extensions.py','Ordered-prefix cache, outage tables, protection and timed_trace()'],['run_extensions.py','Scenario splits, common attack cohorts, sweeps and summaries'],['audit_extensions.py','Fresh exact replay, cohort pairing and total-tight numerical control']],
    footer:'All extension responses use the group repository\'s SciPy defender.',
    notes:'The original physical formulation and default single-objective policy remain intact. Prefix caches use full order, never only an unordered failed set. Line IDs are one-based MATPOWER branch rows. Bus groups export original bus IDs, while the API uses zero-based row indices. Source: EXTENSIONS_README.md, extensions.py and grid_model.py.'
  });
  add('Demo','Demonstration and interpretation',{
    body:['Protection: show the protected lines and the replacement worst attack.','Timing: compare 5 / 5 / 5 with 1 / 1 / 13 and 13 / 1 / 1 minute windows.','Priority: replay both the selected largest gain and the selected largest harm.'],
    footer:'Open output/demonstration.html. The browser selects saved traces; optimization runs offline.',
    notes:'The protection demo uses held-out demand seed 100. Timing illustrates case 39 with the same attack sequence across patterns. Priority compares total-tight with critical-first, including case39 [39,14] and adverse case14 [4,2]. Energy is an endpoint response-then-hold snapshot proxy, not integration of continuous physical ramps. Source: demo_protection.json, demo_timing.json and demo_priority_paired.json.'
  });
  add('Conclusion','Improvement, mixed evidence and failure',get('What the results establish'));
  add('Future Work','Next steps motivated by the results',get('Future work motivated by the failures'));
  // Content titles from the selected source records must not replace the
  // shorter titles above; all label/title geometry follows the supplied deck.
  const labels=['Critique','Extension 1','Extension 1','Extension 1','Robustness','Extension 2','Extension 2','Extension 3','Extension 3','Tradeoffs','Sensitivity','Evaluation','Code','Demo','Conclusion','Future Work'];
  const titles=['Limitations and three extensions','Scenario-aware line protection','Protection evaluation protocol','Protection results on unseen demands','Protection under shifted conditions','Variable response windows','Timing changes the final loss and energy proxy','Critical-service operating objectives','Critical service at the nominal setting','Priority gains and adverse cases','Critical service across response speeds','Correctness and boundaries of the results','Where the extensions are implemented','Demonstration and interpretation','Improvement, mixed evidence and failure','Next steps motivated by the results'];
  slides.forEach((s,i)=>{s.label=labels[i];s.title=titles[i];});
  presentation.slides.keep([]);
  presentation.theme.defaultFont='Inter';
  function text(slide,value,left,top,width,height,size=25,bold=false,color=navy,font='Inter',align='left'){
    const box=slide.shapes.add({geometry:'textbox',position:{left,top,width,height},fill:'none',line:{fill:'none',width:0}});
    box.text=[{runs:[{run:value,style:{typeface:font}}]}];
    box.text.style={fontSize:size,bold,color,alignment:align,wrap:'word',insets:{left:0,right:0,top:0,bottom:0}};
    return box;
  }
  for(const [i,data] of slides.entries()){
    const slide=presentation.slides.add();slide.background.fill='#FFFFFF';
    // Exact supplied freeform outline, from slideLayout11.xml, not a new motif.
    slide.shapes.add({name:'Supplied template header',geometry:'custom',
      position:{left:129521/9525,top:0,width:2749481/9525,height:1364786/9525},
      fill:'#000000',line:{fill:'none',width:0},customPaths:[{width:4741280,height:2353474,commands:[
        {moveTo:{x:0,y:0}},{lineTo:{x:4741280,y:0}},{lineTo:{x:4729949,y:224399}},
        {cubicBezTo:{x1:4608502,y1:1420269,x2:3598552,y2:2353474,x:2370640,y:2353474}},
        {cubicBezTo:{x1:1142728,y1:2353474,x2:132779,y2:1420269,x:11331,y:224399}}, {close:{}}]}]});
    text(slide,data.label,30,43,255,70,31,false,'#FFFFFF','Inter','center');
    text(slide,data.title,312,45,900,95,36,true,navy,'Inter Display');
    if(data.table){
      const cols=data.table[0].length,rows=data.table.length;
      const widths=cols===2?[310,858]:cols===3?[280,370,518]:[320,282,282,284];
      const height=Math.min(405,rows*73);
      const table=slide.tables.add({rows,columns:cols,left:56,top:180,width:1168,height,columnWidths:widths,values:data.table});
      table.borders.assign({style:'solid',fill:'#D9E2EC',width:.7});
      for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
        const cell=table.getCell(r,c);cell.fill=r===0?blue:'#FFFFFF';
        cell.text.style={fontSize:22,bold:r===0,color:r===0?'#FFFFFF':navy,verticalAlignment:'middle',insets:{left:14,right:14,top:10,bottom:10}};
      }
      if(data.body)data.body.forEach((p,j)=>text(slide,p,60,180+height+28+j*42,1140,42,23,false,muted));
    }else if(data.charts){
      for(const [j,c] of data.charts.entries()){
        const double=data.charts.length===2;
        const chart=slide.charts.add(c.type||'line',{
          position:{left:double?45+j*610:60,top:175,width:double?590:1160,height:420},
          categories:c.categories,series:c.series.map((s,k)=>({name:s.name,values:s.values,fill:s.color,line:{fill:s.color,style:'solid',width:3}})),
          title:c.title||(double?c.y:undefined),titleTextStyle:{fontFamily:'Inter',fontSize:25,fill:navy},
          hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{fontFamily:'Inter',fontSize:double?17:20,fill:navy}},
          lineOptions:{smooth:false},barOptions:{direction:'column',grouping:'clustered',gapWidth:60},
          chartFill:'#FFFFFF',plotAreaFill:'#FFFFFF',
          xAxis:{title:c.x,textStyle:{fontFamily:'Inter',fontSize:19,fill:muted},line:{fill:'#B8C7D6',width:1}},
          yAxis:{title:double?(c.title?c.y:undefined):c.y,min:c.min??(c.type==='bar'?0:undefined),max:c.max,
            textStyle:{fontFamily:'Inter',fontSize:18,fill:muted},numberFormatCode:'0.0',majorGridlines:{fill:'#D9E2EC',width:.7,style:'solid'}}
        });
      }
    }else if(data.body){
      const step=data.body.length===3?130:108;
      data.body.forEach((p,j)=>text(slide,p,76,195+j*step,1110,step-15,27,false,navy));
    }
    if(data.footer)text(slide,data.footer,62,634,1150,50,18,true,blue);
    text(slide,String(15+i),1205,680,40,22,14,false,'#3E7BE6','Inter','right');
    slide.speakerNotes.text=data.notes+'\nMeasured group-model experiments: source fingerprint 67cc294651c518a56c9ffbee8975e3c1aa1582e72a8af3478aa7bbf75be86d80. Upstream e03e8495fb67af50f00c52daa75908e34960f151.';
  }
  return slides.length;
}
