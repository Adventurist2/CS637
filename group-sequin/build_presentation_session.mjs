// Execute inside an Artifact Session run callback with presentation and slideData.
// Editable charts and tables use literal measured values from slide_content.json.
export function build(presentation,slideData){
presentation.slides.keep([0]);
presentation.theme.defaultFont='Arial';
const text=(slide,value,left,top,width,height,size=28,bold=false,color='#183544')=>{
  const shape=slide.shapes.add({geometry:'textbox',position:{left,top,width,height},fill:'none',line:{fill:'none',width:0}});
  shape.text=value;
  shape.text.style={fontSize:size,bold,color,wrap:'word',insets:{left:0,right:0,top:0,bottom:0}};
  return shape;
};
for(const [index,d] of slideData.entries()){
  const slide=presentation.slides.add();slide.background.fill='#F5F3EE';
  text(slide,d.title,72,48,1136,110,42,true);
  if(d.table){
    const cols=d.table[0].length;
    const widths=cols===2?[330,806]:cols===3?[245,445,446]:[330,268,268,270];
    const rows=d.table.length;
    const height=Math.min(450,rows*74);
    const table=slide.tables.add({rows,columns:cols,left:72,top:185,width:1136,height,columnWidths:widths,values:d.table});
    table.borders.assign({style:'solid',fill:'#CED9DA',width:.7});
    for(let r=0;r<rows;r++)for(let c=0;c<cols;c++){
      const cell=table.getCell(r,c);cell.fill=r===0?'#DCE8E8':'#F5F3EE';
      cell.text.style={fontSize:22,bold:r===0,color:'#183544',verticalAlignment:'middle',insets:{left:12,right:12,top:8,bottom:8}};
    }
    if(d.body)d.body.forEach((p,j)=>text(slide,p,76,185+height+25+j*42,1120,44,24));
  }else if(d.charts){
    for(const [j,data] of d.charts.entries()){
      const double=d.charts.length===2;
      const chart=slide.charts.add(data.type||'line',{
        position:{left:double?72+j*590:72,top:180,width:double?546:1136,height:440},
        categories:data.categories,
        series:data.series.map(s=>({name:s.name,values:s.values,fill:s.color,line:{style:'solid',fill:s.color,width:3}})),
        hasLegend:true,legend:{position:'bottom',overlay:false,textStyle:{fontSize:21,fontFamily:'Arial',fill:'#183544'}},
        barOptions:{direction:'column',grouping:'clustered',gapWidth:70},
        lineOptions:{smooth:false},
        chartFill:'#F5F3EE',plotAreaFill:'#F5F3EE',
        title:double?data.y:undefined,titleTextStyle:{fontSize:26,fontFamily:'Arial',fill:'#183544'},
        xAxis:{title:double?undefined:data.x,textStyle:{fontSize:22,fontFamily:'Arial',fill:'#183544'},line:{fill:'#BAC8CB',width:1}},
        yAxis:{title:double?undefined:data.y,min:data.type==='bar'?0:undefined,textStyle:{fontSize:21,fontFamily:'Arial',fill:'#183544'},majorGridlines:{style:'solid',fill:'#D6DFDF',width:1},numberFormatCode:'0.0'},
      });
    }
  }else if(d.body){
    const step=d.body.length<=3?135:110;
    d.body.forEach((p,j)=>text(slide,p,78,198+j*step,1100,step-15,29));
  }
  if(d.footer)text(slide,d.footer,76,650,1090,40,19,false,'#586D75');
  text(slide,String(index+2),1195,673,36,22,17,false,'#62747B');
  slide.speakerNotes.text=d.notes;
}
}
