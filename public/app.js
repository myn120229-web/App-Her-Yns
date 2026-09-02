/* Younes Nazarian — app.js */
(() => {
  const $  = s => document.querySelector(s);
  const $$ = s => document.querySelectorAll(s);

  /* ---------- scroll: progress, nav bg, active link, cue ---------- */
  const nav = $('#nav'), prog = $('#progress'), cue = $('#scrollCue');
  const secIds = ['hero','about','skills','projects','process','contact'];
  const onScroll = () => {
    const max = document.documentElement.scrollHeight - innerHeight;
    prog.style.width = (scrollY / max * 100) + '%';
    nav.classList.toggle('scrolled', scrollY > 60);
    if (cue) cue.style.opacity = scrollY > 80 ? '0' : '1';
    let cur = 'hero';
    secIds.forEach(id => {
      const el = document.getElementById(id);
      if (el && scrollY + 140 >= el.offsetTop) cur = id;
    });
    $$('.nav-links a').forEach(a =>
      a.classList.toggle('active', a.getAttribute('href') === '#' + cur));
  };
  addEventListener('scroll', onScroll, { passive: true });
  onScroll();

  /* ---------- section reveal (once) ---------- */
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) { e.target.classList.add('visible'); io.unobserve(e.target); }
  }), { threshold: .15 });
  $$('.sec-reveal').forEach(el => io.observe(el));

  /* ---------- custom cursor ---------- */
  const cur = $('#cursor');
  if (cur && matchMedia('(hover:hover)').matches) {
    addEventListener('mousemove', e => { cur.style.left = e.clientX+'px'; cur.style.top = e.clientY+'px'; });
    $$('a,button,.skill,.proj-card').forEach(el => {
      el.addEventListener('mouseenter', () => cur.classList.add('on'));
      el.addEventListener('mouseleave', () => cur.classList.remove('on'));
    });
  }

  /* ---------- mobile menu ---------- */
  const ham = $('#ham'), mm = $('#mobileMenu'), cx = $('#closeX');
  ham?.addEventListener('click', () => { mm.classList.add('open'); ham.setAttribute('aria-expanded','true'); });
  cx?.addEventListener('click', () => { mm.classList.remove('open'); ham.setAttribute('aria-expanded','false'); });
  mm?.querySelectorAll('a').forEach(a => a.addEventListener('click', () => mm.classList.remove('open')));

  /* ---------- count-up ---------- */
  const countEl = $('.count');
  if (countEl) {
    const io2 = new IntersectionObserver(es => {
      if (es[0].isIntersecting) {
        const to = +countEl.dataset.to; let n = 0;
        const t = setInterval(() => { n++; countEl.textContent = n + '+'; if (n >= to) clearInterval(t); }, 70);
        io2.disconnect();
      }
    }, { threshold: .5 });
    io2.observe(countEl);
  }

  /* ---------- projects: try API, fallback static ---------- */
  const FALLBACK = {
    projects: [
      { id:'churn', domain:'SaaS / Telecom', name:'Customer Churn Predictor',
        description:'End-to-end classifier that flags at-risk subscribers before they leave, with a Streamlit business dashboard.',
        stack:['Python','Pandas','Scikit-learn','Seaborn','Streamlit'],
        metrics:[{value:'84%',label:'Recall (churn)'},{value:'$180k',label:'At-risk MRR flagged'}],
        github:'https://github.com/myn120229-web', snippet:'from sklearn.ensemble\nimport RandomForestClassifier\nrf = RandomForestClassifier(\n  n_estimators=200)', featured:true,
        details:'EDA uncovered tenure & contract type as top predictors. SMOTE balanced the 73/27 split. Tuned RF (200 trees, max_depth 12). Streamlit dashboard surfaces weekly risk cohorts for the retention team.' },
      { id:'forecast', domain:'E-Commerce / Retail', name:'Sales Forecasting Engine — Rossmann',
        description:'Time-series forecaster across 1,115 stores with promo and calendar features.',
        stack:['Python','Time Series','Feature Eng.','Scikit-learn'],
        metrics:[{value:'<12%',label:'MAPE'},{value:'23%',label:'Est. stockout cut'}],
        github:'https://github.com/myn120229-web', snippet:'import statsmodels.api as sm\nres = sm.tsa.ExponentialSmoothing(\n  y).fit(optimized=True)',
        details:'Engineered promo, holiday & rolling-mean features. Gradient Boosting beat ARIMA by 18%. Forecast feeds an inventory recommender.' },
      { id:'credit', domain:'Fintech / Banking', name:'Credit Risk Scorer + Explainability',
        description:'Imbalanced-classification pipeline with per-decision explanations for regulatory compliance.',
        stack:['Sklearn Pipeline','SMOTE','PR Analysis','SHAP'],
        metrics:[{value:'78%',label:'Precision (default)'},{value:'Audit',label:'Explainability'}],
        github:'https://github.com/myn120229-web', snippet:'from imblearn.pipeline\nimport Pipeline\npipe = Pipeline([\n  ("smote", SMOTE())])',
        details:'Heavy class imbalance (92/8). Impute → scale → SMOTE → calibrated classifier. PR threshold tuned at 78% precision. Per-decision feature contributions exported for review.' },
    ]
  };

  const grid = $('#projGrid');
  const cardHTML = (p, i) => `
    <article class="proj-card glass-chip ${p.featured ? 'featured' : ''}" style="transition-delay:${i*60}ms">
      <div class="watermark" aria-hidden="true">${p.snippet}</div>
      <span class="domain">${p.domain}</span>
      <h3>${p.name}</h3>
      <p>${p.description}</p>
      <div class="div"></div>
      <div class="metrics">${p.metrics.map(m => `<div class="m"><strong>${m.value}</strong><span>${m.label}</span></div>`).join('')}</div>
      <div class="stack">${p.stack.map(s => `<span>${s}</span>`).join('')}</div>
      <div class="proj-links">
        <a href="${p.github}" target="_blank" rel="noopener noreferrer">View on GitHub</a>
        <a href="#" class="case-toggle" data-idx="${i}">Case Study</a>
      </div>
      <div class="details" id="det-${i}">${p.details || ''}</div>
    </article>`;

  fetch('/api/projects').then(r => r.ok ? r.json() : FALLBACK).catch(() => FALLBACK)
    .then(data => {
      grid.innerHTML = data.projects.map(cardHTML).join('');
      grid.querySelectorAll('.case-toggle').forEach(btn =>
        btn.addEventListener('click', e => {
          e.preventDefault();
          $('#det-' + btn.dataset.idx).classList.toggle('open');
        }));
    });

  /* ---------- panels: fan + parallax ---------- */
  const panels = $$('.panel');
  if (panels.length && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    let tx=0, ty=0, cx2=0, cy2=0, t=0;
    addEventListener('mousemove', e => {
      tx = (e.clientX / innerWidth  - .5) * 14;
      ty = (e.clientY / innerHeight - .5) * -10;
    });
    const base = [-20, -7, 7, 20];
    (function loop() {
      t += .008; cx2 += (tx-cx2)*.06; cy2 += (ty-cy2)*.06;
      const fan = Math.sin(t) * 3;
      panels.forEach((p, i) => {
        p.style.transform =
          `translate(-50%,-50%) rotate(${base[i]+fan}deg) rotateY(${cx2}deg) rotateX(${cy2}deg) translateZ(${i*20}px)`;
      });
      requestAnimationFrame(loop);
    })();
  }

  /* ---------- particles ---------- */
  const cvs = $('#particles');
  if (cvs && !matchMedia('(prefers-reduced-motion: reduce)').matches) {
    const ctx = cvs.getContext('2d');
    let W, H, parts = [];
    const size = () => { W = cvs.width = cvs.parentElement.offsetWidth; H = cvs.height = cvs.parentElement.offsetHeight; };
    size(); addEventListener('resize', size);
    for (let i=0;i<40;i++) parts.push({ x:Math.random()*innerWidth, y:Math.random()*innerHeight, r:Math.random()*1.4+.5, vy:-(Math.random()*.3+.08), vx:(Math.random()-.5)*.08, o:Math.random()*.04+.04 });
    (function frame() {
      ctx.clearRect(0,0,W,H);
      parts.forEach(p => {
        p.y+=p.vy; p.x+=p.vx;
        if (p.y<-10){p.y=H+10;p.x=Math.random()*W}
        ctx.beginPath(); ctx.arc(p.x,p.y,p.r,0,7); ctx.fillStyle=`rgba(255,255,255,${p.o})`; ctx.fill();
      });
      requestAnimationFrame(frame);
    })();
  }

  /* ---------- contact form ---------- */
  const form = $('#contactForm'), btn = $('#sendBtn'), msg = $('#formMsg');
  form?.addEventListener('submit', async e => {
    e.preventDefault();
    const fd = new FormData(form);
    if (!fd.get('name') || !fd.get('email') || !fd.get('message')) {
      msg.textContent = 'Please fill in all fields.'; return;
    }
    if (fd.get('company')) return; // honeypot
    btn.classList.add('loading');
    try {
      const r = await fetch('/api/contact', {
        method:'POST', headers:{'Content-Type':'application/json'},
        body: JSON.stringify({ name:fd.get('name'), email:fd.get('email'), message:fd.get('message') })
      });
      if (!r.ok) throw new Error();
      btn.classList.remove('loading'); btn.classList.add('done');
      msg.textContent = 'Message received — thank you.';
      form.reset();
      setTimeout(() => { btn.classList.remove('done'); $('.btn-text').textContent = 'Send Message'; }, 3500);
    } catch {
      btn.classList.remove('loading');
      msg.textContent = 'Could not send — email me directly at younes@example.com';
    }
  });
})();
