/* Younes Nazarian — The Learning System · app.js */
(() => {
  const $  = s => document.querySelector(s);
  const $$ = s => [...document.querySelectorAll(s)];

  /* ── helpers ──────────────────────── */
  const clamp = (v,a,b) => Math.max(a,Math.min(b,v));

  /* ── progress + nav + active + date ──────── */
  const nav = $('#nav'), prog = $('#progress'), cue = document.querySelector('.scroll-cue');
  const secIds = ['hero','system','toolchain','work','loop','human','contact'];
  const navLinks = $$('.nav-links a');

  const ds = $('#dateStamp');
  if (ds) ds.textContent = new Date().toLocaleDateString('en-US',{month:'short',year:'numeric'}).toUpperCase();

  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    prog.style.width = (scrollY / max * 100) + '%';
    nav.classList.toggle('solid', scrollY > 60);
    if (cue) cue.style.opacity = scrollY > 80 ? '0' : '1';
    let cur = 'hero';
    secIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && scrollY + 140 >= el.offsetTop) cur = id;
    });
    navLinks.forEach(a => a.classList.toggle('active', a.getAttribute('href') === '#'+cur));
  };
  addEventListener('scroll', onScroll, {passive:true});
  onScroll();

  /* ── reveal (clip-path, once) ──────────── */
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting){ e.target.classList.add('visible'); io.unobserve(e.target); }
  }), {threshold:.12});
  $$('.sec-reveal').forEach(el => io.observe(el));

  /* ── cursor ─────────────────────────────── */
  const cur = $('#cursor');
  if (cur && matchMedia('(hover:hover)').matches){
    addEventListener('mousemove', e => { cur.style.left=e.clientX+'px'; cur.style.top=e.clientY+'px'; });
    $$('a,button,.tc-node,.proj').forEach(el=>{
      el.addEventListener('mouseenter',()=>cur.classList.add('on'));
      el.addEventListener('mouseleave',()=>cur.classList.remove('on'));
    });
  }

  /* ── mobile ─────────────────────────────── */
  const burger=$('#burger'), mnav=$('#mnav'), mclose=$('#mclose');
  burger?.addEventListener('click',()=>mnav.classList.add('open'));
  mclose?.addEventListener('click',()=>mnav.classList.remove('open'));
  $$('#mnav a').forEach(a=>a.addEventListener('click',()=>mnav.classList.remove('open')));

  /* ── The Learning Field — heavy, slow, physical ─────── */
  const field = $('#theField');
  const planes = field ? [...field.querySelectorAll('.plane')] : [];
  if (planes.length && !matchMedia('(prefers-reduced-motion: reduce)').matches){
    let tx=0, ty=0, cx=0, cy=0, t=0;
    addEventListener('mousemove', e=>{
      tx = (e.clientX/innerWidth -.5)*14;
      ty = (e.clientY/innerHeight -.5)*-10;
    });
    const base=[-22,-8,8,22];
    const zs=[0,26,52,78];
    // entrance: compressed → unfold
    planes.forEach((p,i)=>{
      p.style.transform = `translate(-50%,-50%) rotate(${0}deg) translateZ(${zs[i]}px) scale(.6)`;
    });
    setTimeout(()=>{
      planes.forEach((p,i)=>{
        p.style.transition = `transform 1.4s cubic-bezier(.16,1,.3,1)`;
        setTimeout(()=>{ p.style.transform=''; p.style.transition=''; },80+i*100);
      });
    },600);

    const loop=()=>{
      t+=.006;
      cx+=(tx-cx)*.045; cy+=(ty-cy)*.045;
      const breath=Math.sin(t)*2.4;
      planes.forEach((p,i)=>{
        const a = base[i]+breath*(1-Math.abs(base[i])/30);
        p.style.transform =
          `translate(-50%,-50%) rotate(${a}deg) rotateY(${cx}deg) rotateX(${cy}deg) translateZ(${zs[i]}px)`;
      });
      requestAnimationFrame(loop);
    };
    requestAnimationFrame(loop);
    // animate field-wrap entrance opacity handled by CSS already
  }

  /* ── toolchain tooltip ──────────────────── */
  const hint = $('#tcHint');
  $$('.tc-node').forEach(n=>{
    n.addEventListener('mouseenter',()=>{
      const t=n.dataset.tip || '';
      if(!t||!hint) return;
      hint.textContent=t; hint.classList.add('show');
    });
    n.addEventListener('mouseleave',()=>hint?.classList.remove('show'));
  });

  /* ── projects — fetch + research artifact layout ── */
  const FALLBACK={
    projects:[
      {id:'01',label:'Classification',name:'Customer Churn Predictor',domain:'SaaS · Telecom',
        problem:'Which subscribers will leave before they do.',
        approach:'Classification pipeline with cohort analysis and a Streamlit business dashboard.',
        signal:'Tenure & contract type dominate the decision boundary.',
        result:'Evaluation metric in case study — recall tuned for proactive retention.',
        stack:['Python','Pandas','Scikit-learn','Seaborn','Streamlit'],
        visual:'branch'},
      {id:'02',label:'Temporal',name:'Sales Forecasting Engine',domain:'E-Commerce · Rossmann Stores',
        problem:'What will 1,115 stores sell tomorrow, and next week.',
        approach:'Temporal modeling with promo, calendar, and rolling statistics.',
        signal:'Seasonal waveform modulated by promo pulses.',
        result:'Evaluation metric in case study — rolling-origin cross-validation.',
        stack:['Python','Time Series','Feature Eng.','Scikit-learn'],
        visual:'wave'},
      {id:'03',label:'Probability',name:'Credit Risk Scorer',domain:'Fintech · Banking',
        problem:'Who will default, and why does the model believe so.',
        approach:'Imbalanced classification with per-decision explanations for compliance.',
        signal:'A probability distribution with a deliberate threshold.',
        result:'Evaluation metric in case study — precision tuned at the operating point.',
        stack:['Sklearn Pipeline','SMOTE','PR Analysis','Explainability'],
        visual:'dist'},
    ]
  };

  const vizSVG = v=>{
    if(v==='branch') return `<svg viewBox="0 0 360 140"><path d="M20 70 H110 M110 70 L180 30 L260 30 M110 70 L180 70 L260 70 M110 70 L180 110 L260 110" stroke="rgba(79,141,255,.45)" stroke-width="1.2" stroke-dasharray="6 6" fill="none"/><circle cx="260" cy="30" r="5" fill="var(--b4)" opacity=".9"/><circle cx="260" cy="70" r="5" fill="var(--b4)" opacity=".9"/><circle cx="260" cy="110" r="5" fill="var(--b4)" opacity=".9"/></svg>`;
    if(v==='wave') return `<svg viewBox="0 0 360 140"><path d="M10 80 C60 40, 110 100, 160 70 S260 110, 320 60" stroke="rgba(79,141,255,.45)" stroke-width="1.2" stroke-dasharray="5 5" fill="none"/><circle cx="80" cy="65" r="3" fill="var(--b4)"/><circle cx="160" cy="70" r="4" fill="var(--gold)"/><circle cx="250" cy="88" r="3" fill="var(--b4)"/></svg>`;
    return `<svg viewBox="0 0 360 140"><path d="M30 100 Q90 10, 150 60 T270 60" stroke="rgba(79,141,255,.45)" stroke-width="1.2" stroke-dasharray="5 5" fill="none"/><line x1="150" y1="12" x2="150" y2="100" stroke="var(--gold)" stroke-width="1" opacity=".7" stroke-dasharray="3 3"/><circle cx="150" cy="60" r="4" fill="var(--gold)"/></svg>`;
  };

  const projHTML = (p,i)=>`
    <article class="proj" data-idx="${i}">
      <div class="proj-head">
        <div class="proj-num">${p.id}</div>
        <h3 class="proj-name">${p.name}</h3>
        <div class="proj-domain">${p.domain}</div>
      </div>
      <div class="proj-body">
        <div class="proj-facts">
          <div class="fact"><span class="k">Problem</span><span class="v">${p.problem}</span></div>
          <div class="fact"><span class="k">Approach</span><span class="v">${p.approach}</span></div>
          <div class="fact"><span class="k">Signal</span><span class="v">${p.signal}</span></div>
          <div class="fact"><span class="k">Result</span><span class="v">${p.result}</span></div>
          <div class="proj-stack">${p.stack.map(s=>`<span>${s}</span>`).join('')}</div>
        </div>
        <div class="proj-visual">${vizSVG(p.visual)}</div>
      </div>
      <button class="proj-toggle" aria-expanded="false"><span class="plus"></span> Explore case</button>
      <div class="proj-expand">
        <div class="expand-grid">
          <div><h5>Data</h5><p>Real-world, messy data requiring careful cleaning and leakage controls.</p></div>
          <div><h5>Exploration</h5><p>Distributions, outliers, and the features that carry actual signal.</p></div>
          <div><h5>Modeling</h5><p>Baselines → ensembles → rigorous cross-validation. No leaderboard theatre.</p></div>
          <div><h5>Lessons</h5><p>What broke, what taught, and what the next iteration carries forward.</p></div>
        </div>
      </div>
    </article>`;

  const grid=$('#workGrid');
  fetch('/api/projects').then(r=>r.ok?r.json():FALLBACK).catch(()=>FALLBACK)
    .then(data=>{
      grid.innerHTML=data.projects.map(projHTML).join('');
      grid.querySelectorAll('.proj-toggle').forEach(btn=>{
        btn.addEventListener('click',()=>{
          const proj=btn.closest('.proj');
          const open=proj.classList.toggle('open');
          btn.setAttribute('aria-expanded',String(open));
          btn.innerHTML=`<span class="plus"></span> ${open?'Close case':'Explore case'}`;
        });
      });
    });

  /* ── contact ──────────────────────────── */
  const form=$('#contactForm'), sendBtn=$('#sendBtn'), fmsg=$('#fmsg');
  form?.addEventListener('submit',async e=>{
    e.preventDefault();
    const fd=new FormData(form);
    if(!fd.get('name')||!fd.get('email')||!fd.get('message')){
      fmsg.textContent='Please fill in all fields.'; fmsg.className='form-msg'; return;
    }
    if(fd.get('company')) return; // honeypot
    sendBtn.classList.add('loading');
    try{
      const r=await fetch('/api/contact',{
        method:'POST',headers:{'Content-Type':'application/json'},
        body:JSON.stringify({name:fd.get('name'),email:fd.get('email'),message:fd.get('message')})
      });
      if(!r.ok) throw 0;
      sendBtn.classList.remove('loading'); sendBtn.classList.add('done');
      fmsg.textContent='Message received.'; fmsg.className='form-msg ok';
      form.reset();
      setTimeout(()=>{ sendBtn.classList.remove('done'); fmsg.textContent=''; },4000);
    }catch{
      sendBtn.classList.remove('loading');
      fmsg.textContent='Could not send — reach me at younes@example.com'; fmsg.className='form-msg';
    }
  });

})();
