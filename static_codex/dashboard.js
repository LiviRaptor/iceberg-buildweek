const RATES={{rates_js}};
    const START={{invested_start}};
    const RETIRE_YEAR=2043,CHART_END={{CHART_END}},RET_FLOAT=2043+11/12;
    const MSK=['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
    const $=id=>document.getElementById(id);
    const fmt=v=>Math.round(v).toLocaleString('sk-SK')+' €';
    const grid='rgba(180,160,120,.08)';
    Chart.defaults.color='#b2a68d'; Chart.defaults.font.family="'Hanken Grotesk',sans-serif";
    function fillY(sel,none){let h=none?'<option value="0">-</option>':'';
    for(let y=2027;y<=RETIRE_YEAR;y++)h+=`<option>${y}</option>`;sel.innerHTML=h;}
    function fillM(sel){
      const mn=['—','Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'];
      sel.innerHTML=mn.slice(1).map((m,i)=>`<option value="${i+1}">${m}</option>`).join('');
    }
    // Pause chip grid
    function buildPauseGrid(){
      const g=$('pause-grid');
      for(let y=2027;y<=RETIRE_YEAR;y++){
        const b=document.createElement('button');
        b.className='py-chip';b.textContent=y;b.dataset.y=y;
        b.onclick=()=>{b.classList.toggle('on');draw();};
        g.appendChild(b);
      }
    }
    fillY($('incYear'),false);fillY($('lumpYear'),false);
    fillM($('incMonth'));fillM($('lumpMonth'));

    // Consensus scale 5% -> 20% by 0.5
    const kSel=$('kRate');
    for(let r=5;r<=20;r+=0.5){
      const o=document.createElement('option');
      o.value=(r/100).toFixed(3);
      o.textContent=r.toFixed(1).replace('.',',')+' %';
      if(r===8.5) o.selected=true;
      kSel.appendChild(o);
    }

    buildPauseGrid();

    (function(){
      const now=new Date();
      const ret=new Date('2043-11-06');

      let years=ret.getFullYear()-now.getFullYear();
      let months=ret.getMonth()-now.getMonth();

      if(months<0){
        years--;
        months+=12;
      }

      $('ret-countdown').innerHTML=
        `→ Retirement in <span style="color:var(--teal);font-weight:700">${years}</span> years and <span style="color:var(--teal);font-weight:700">${months}</span> months`;
    })();
    // Trajectory table
    function getT(){
      const kr=+($('kRate')?$('kRate').value:0.085);
      const kr2=Math.max(0.065,kr-0.01);
      return{tlmeny:{p1:0.048,p2:0.050},konsenzus:{p1:kr,p2:kr2},aiboom:{p1:0.1175,p2:0.090}};
    }
    const BIRTH=1978;
    function calcS(R){
      const mo=+$('monthly').value||0;
      const iY=+$('incYear').value, iM=+$('incMonth').value||1, iA=+$('incAmt').value||0;
      const lA=+$('lumpAmt').value||0, lY=+$('lumpYear').value, lM=+$('lumpMonth').value||1;
      // pause: collect all checked chips
      const pauseSet=new Set([...$('pause-grid').querySelectorAll('.py-chip.on')].map(b=>+b.dataset.y));
      let v=START;
      const rows=[{yr:2026,age:48,contrib:0,val:Math.round(v)}];
      for(let y=2027;y<=CHART_END;y++){
        const r=(y-2026)<=10?R.p1:R.p2;
        let c=0,l=0;
        if(y<=RETIRE_YEAR){
          // apply increase: full year if y>iY, partial if y===iY based on month
          let inc=0;
          if(iA>0&&y>iY) inc=iA;
          else if(iA>0&&y===iY) inc=iA*(13-iM)/12; // partial year
          const m=mo+inc;
          c=pauseSet.has(y)?0:m*12;
          // lump: apply in the lumpYear, approximate at month lM
          if(lA>0&&y===lY) l=lA;
        }
        v=v*(1+r)+c+l;
        rows.push({yr:y,age:y-BIRTH,contrib:Math.round(c+l),val:Math.round(v)});
      }
      return rows;
    }
    function beTable(ko){
      const R=getT().konsenzus;
      for(let i=1;i<ko.length;i++){
        const yr=ko[i].yr,V=ko[i].val;
        if(yr>RETIRE_YEAR) break;
        const yL=RET_FLOAT-yr; if(yL<=0) return'teraz!';
        const p1=Math.min(yL,Math.max(0,2036-yr)),p2=Math.max(0,yL-p1);
        if(V*(1+R.p1)**p1*(1+R.p2)**p2>=750000){
          const pv=ko[i-1];
          for(let m=0;m<=12;m++){
            const yL2=RET_FLOAT-(pv.yr+m/12); if(yL2<=0) return MSK[0]+' '+pv.yr;
            const q1=Math.min(yL2,Math.max(0,2036-pv.yr-m/12)),q2=Math.max(0,yL2-q1);
            if(pv.val*(1+R.p1)**q1*(1+R.p2)**q2>=750000)
              return MSK[m%12]+' '+(m<12?pv.yr:yr);
          }
          return'early '+yr;
        }
      }
      return'after 2043';
    }
    function fcell(v,isAfter){
      const over=v>=750000;
      const c=over?'var(--teal)':isAfter?'var(--dim)':'';
      return`<td class="r" style="color:${c};font-weight:${over?600:400}">${fmt(v)}${over?' ✓':''}</td>`;
    }
    function draw(){
      const T=getT();
      const tl=calcS(T.tlmeny),ko=calcS(T.konsenzus),ai=calcS(T.aiboom);
      const goalKo=ko.find(r=>r.val>=750000);
      const retKo=ko.find(r=>r.yr===RETIRE_YEAR)||ko[ko.length-1];
      const gVal=goalKo?goalKo.yr:'after 2043';
      $('rGoal').textContent=gVal;
      const gEl=$('rGoal');
      gEl.style.color=(!goalKo||goalKo.yr>2043)?'var(--red)':'var(--green)';
      $('rFinal').textContent=fmt(retKo.val);
      $('rBreak').textContent=beTable(ko);
      let html='';
      for(let i=0;i<ko.length;i++){
        const yr=ko[i].yr,isRet=(yr===RETIRE_YEAR),isAfter=(yr>RETIRE_YEAR);
        const rc=isRet?' class="rr"':isAfter?' class="ra"':'';
        html+=`<tr${rc}>`;
        html+=`<td style="font-weight:${isRet?600:400};color:${isAfter?'var(--dim)':''}">${yr}</td>`;
        html+=`<td class="r" style="color:var(--dim);width:52px;padding-right:4px">${ko[i].age}</td>`;
        html+=`<td class="r" style="color:var(--soft)">${!isAfter&&ko[i].contrib>0?fmt(ko[i].contrib):'—'}</td>`;
        html+=fcell(tl[i].val,isAfter);
        html+=fcell(ko[i].val,isAfter);
        html+=fcell(ai[i].val,isAfter);
        html+='</tr>';
      }
      $('traj-tbody').innerHTML=html;
    }
    ['monthly','kRate','incYear','incAmt','incMonth','lumpAmt','lumpMonth','lumpYear'].forEach(id=>{
      $(id).addEventListener('input',draw); $(id).addEventListener('change',draw);
    });
    new Chart($('spark'),{type:'line',
    data:{labels:['2019','2020','2021','2022','2023','2024','2025','today'],
    datasets:[{data:[5000,13000,65000,50000,95000,130000,143000,{{invested_spark}}],
    borderColor:'#d4a14c',borderWidth:2.5,pointRadius:3,pointBackgroundColor:'#d4a14c',
    fill:true,backgroundColor:'rgba(212,161,76,.10)',tension:.4}]},
    options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:false},
    annotationRetirement:true,tooltip:{callbacks:{label:c=>fmt(c.raw)}}},
    scales:{x:{ticks:{font:{size:10}},grid:{display:false}},y:{ticks:{font:{size:9},callback:v=>(v/1000)+'k'},grid:{color:grid}}}}});
    const mc={{mc_js}};const lims=[{{lim_prices}}];const lc=['#edc676','#df9270','#d87f50','#c96a4d','#b69ae8'];
    const lqqScaleValues=[...mc,...lims,{{lqq_price_1}}].filter(v=>Number.isFinite(v));
    const lqqYMin=Math.max(0,Math.floor(Math.min(...lqqScaleValues)*0.8));
    const lqqYMax=Math.ceil(Math.max(...lqqScaleValues)*1.15);
    new Chart($('lqq'),{type:'line',
    data:{labels:mc.map((_,i)=>i%12===0?String(2021+Math.floor(i/12)):''),
    datasets:[
    {label:'LQQ',data:mc,borderColor:'#b69ae8',borderWidth:2.5,pointRadius:0,fill:true,backgroundColor:'rgba(182,154,232,.07)',tension:.3},
    {label:'today {{lqq_price_0}} €',data:mc.map(()=>{{lqq_price_1}}),borderColor:'#5fcca7',borderWidth:1,borderDash:[3,3],pointRadius:0,fill:false},
    ...lims.map((l,i)=>{return{label:l+' €',data:mc.map(()=>l),borderColor:lc[i],borderWidth:1,borderDash:[5,3],pointRadius:0,fill:false}})
    ]},
    options:{responsive:true,maintainAspectRatio:false,
    plugins:{legend:{display:true,position:'top',align:'end',labels:{color:'#b2a68d',font:{size:10},boxWidth:14,padding:10}},
    tooltip:{filter:i=>i.dataset.label==='LQQ',callbacks:{label:c=>'LQQ: '+Math.round(c.raw)+' €'}}},
    scales:{x:{ticks:{font:{size:9},autoSkip:false,maxRotation:0},grid:{color:grid}},y:{min:lqqYMin,max:lqqYMax,ticks:{font:{size:9},callback:v=>v.toFixed(0)},grid:{color:grid}}}}});

    Chart.register({
    id:'retirementLine',
    afterDraw(chart,args,opts){
      if(!chart.options.plugins.annotationRetirement) return;

      const xScale=chart.scales.x;
      const yScale=chart.scales.y;
      const labels=chart.data.labels||[];

      const idx=labels.indexOf('2043');
      if(idx===-1) return;

      const x=xScale.getPixelForValue(idx);
      const ctx=chart.ctx;

      ctx.save();

      ctx.strokeStyle='rgba(212,161,76,.55)';
      ctx.setLineDash([5,5]);
      ctx.lineWidth=1;

      ctx.beginPath();
      ctx.moveTo(x,yScale.top);
      ctx.lineTo(x,yScale.bottom);
      ctx.stroke();

      ctx.setLineDash([]);
      ctx.fillStyle='rgba(237,198,118,.95)';
      ctx.font='12px Inter';

      ctx.fillText('Retirement • Nov 2043',x+8,yScale.top+18);

      ctx.restore();
    }
    });

    const trajChart=new Chart($('trajChart'),{
    type:'line',
    data:{
    labels:[],
    datasets:[
    {label:'Damped',data:[],borderColor:'#edc676',backgroundColor:'rgba(237,198,118,.08)',borderWidth:2,tension:.35,pointRadius:0,fill:false},
    {label:'Consensus',data:[],borderColor:'#d08cff',backgroundColor:'rgba(208,140,255,.08)',borderWidth:2.4,tension:.35,pointRadius:0,fill:false},
    {label:'AI boom',data:[],borderColor:'#5fcca7',backgroundColor:'rgba(95,204,167,.10)',borderWidth:2.6,tension:.35,pointRadius:0,fill:false},
    {label:'750k target',data:[],borderColor:'rgba(212,161,76,.45)',borderWidth:1.5,borderDash:[6,6],pointRadius:0,fill:false}
    ]},
    options:{
    responsive:true,
    maintainAspectRatio:false,
    plugins:{
    legend:{display:false},
    annotationRetirement:true,
    tooltip:{callbacks:{label:c=>c.dataset.label+': '+fmt(c.raw)}}
    },
    scales:{
    x:{grid:{color:grid},ticks:{font:{size:10}}},
    y:{
    min:0,
    max:1000000,
    grid:{color:grid},
    ticks:{callback:v=>v===0?'0':(v/1000)+'k'}
    }
    }
    }
    });

    function updateTrajChart(){
      const T=getT();
      const tl=calcS(T.tlmeny);
      const ko=calcS(T.konsenzus);
      const ai=calcS(T.aiboom);

      trajChart.data.labels=ko.map(r=>String(r.yr));
      trajChart.data.datasets[0].data=tl.map(r=>r.val);
      trajChart.data.datasets[1].data=ko.map(r=>r.val);
      trajChart.data.datasets[2].data=ai.map(r=>r.val);
      trajChart.data.datasets[3].data=ko.map(()=>750000);

      trajChart.update();
    }

    const oldDraw=draw;
    draw=function(){
      oldDraw();
      updateTrajChart();
    };

    draw();

    function setTheme(theme,btn){
      document.body.classList.remove(
        'theme-bloomberg',
        'theme-minimal',
        'theme-institutional',
        'theme-timeline'
      );

      document.body.classList.add(theme);

      document.querySelectorAll('.theme-btn')
        .forEach(b=>b.classList.remove('active'));

      if(btn) btn.classList.add('active');

      localStorage.setItem('dashboard-theme',theme);
    }

    (function(){
      const saved=localStorage.getItem('dashboard-theme');

      if(saved){
        document.body.classList.remove(
          'theme-bloomberg',
          'theme-minimal',
          'theme-institutional',
          'theme-timeline'
        );

        document.body.classList.add(saved);

        const map={
          'theme-bloomberg':0,
          'theme-minimal':1,
          'theme-institutional':2,
          'theme-timeline':3
        };

        const btns=document.querySelectorAll('.theme-btn');

        btns.forEach(b=>b.classList.remove('active'));

        if(btns[map[saved]]) {
          btns[map[saved]].classList.add('active');
        }
      }
    })();


    function setTheme(theme,btn){

      document.querySelectorAll('.hero-variant')
        .forEach(el=>el.classList.remove('active'));

      const target=document.getElementById(theme);

      if(target){
        target.classList.add('active');
      }

      document.querySelectorAll('.theme-btn')
        .forEach(b=>b.classList.remove('active'));

      if(btn){
        btn.classList.add('active');
      }

      localStorage.setItem('dashboard-theme',theme);
    }

    (function(){

      const saved=localStorage.getItem('dashboard-theme');

      if(saved){

        document.querySelectorAll('.hero-variant')
          .forEach(el=>el.classList.remove('active'));

        const target=document.getElementById(saved);

        if(target){
          target.classList.add('active');
        }

      }

    })();


    (function(){
    const spyy={{spyy_value_raw}};
    const lqq={{lqq_value_raw}};
    const share=(lqq/(spyy+lqq))*100;

    const el=document.getElementById('lqqShare');
    const st=document.getElementById('lqqStatus');

    if(el){
    el.textContent=share.toFixed(1)+'%';
    }

    if(st){
    if(share<25){
    st.className='risk-status st-ok';
    st.textContent='OK · LQQ exposure under control';
    }else if(share<35){
    st.className='risk-status st-warn';
    st.textContent='Watch · volatility is rising';
    }else{
    st.className='risk-status st-danger';
    st.textContent='Reduce LQQ';
    }
    }
    })();

    function updateDecision(){
      const checks=[...document.querySelectorAll('.chkbox')];
      const checked=checks.filter(c=>c.checked).length;
      const box=document.getElementById('DecisionBox');

      if(!box) return;

      if(checked===5){
        box.innerHTML='🟢 HOLD · your risk parameters are stable for now.';
        box.style.color='var(--teal)';
      }
      else if(checked>=3){
        box.innerHTML='🟡 CONSIDER REDUCING LQQ · some risks are rising.';
        box.style.color='var(--gold)';
      }
      else{
        box.innerHTML='🔴 PRIORITY = STABILITY · leverage may be too demanding right now.';
        box.style.color='var(--red)';
      }
    }

    document.addEventListener('change',e=>{
      if(e.target.classList.contains('chkbox')){
        updateDecision();
      }
    });


// Temporary visual preview mode: open URL with ?regimePreview=1
(function(){
  const params = new URLSearchParams(window.location.search);
  if (!params.has('regimePreview')) return;
  const badge = document.getElementById('live-regime-badge');
  const label = document.getElementById('live-regime-text');
  if (!badge || !label) return;
  const states = [
    ['BULL', 'is-bull'],
    ['NEUTRAL', 'is-neutral'],
    ['BEAR', 'is-bear'],
  ];
  let i = 0;
  function renderRegimePreview(){
    const [text, cls] = states[i % states.length];
    badge.classList.remove('is-bull', 'is-neutral', 'is-bear');
    badge.classList.add(cls);
    label.textContent = text;
    i += 1;
  }
  renderRegimePreview();
  setInterval(renderRegimePreview, 1000);
})();


(function(){
  const btn = document.getElementById('ai-review-button');
  const out = document.getElementById('ai-review-output');
  const mode = document.getElementById('ai-review-mode');
  if (!btn || !out) return;

  btn.addEventListener('click', async () => {
    btn.disabled = true;
    btn.textContent = 'Reviewing...';
    out.textContent = 'Checking risk guardrails against the current dashboard state...';
    if (mode) mode.textContent = '';
    try {
      const res = await fetch('/api/ai-review', {method:'POST', cache:'no-store'});
      const data = await res.json();
      out.textContent = data.review || 'No review returned.';
      if (mode) mode.textContent = data.mode || 'AI review';
    } catch (err) {
      out.textContent = 'Start the live demo server to run the AI guardrail review. Demo fallback is available without an API key.';
      if (mode) mode.textContent = 'offline';
    } finally {
      btn.disabled = false;
      btn.textContent = 'Run AI review';
    }
  });
})();
