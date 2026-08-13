const tg = window.Telegram?.WebApp;
if (tg) { tg.expand(); tg.ready(); }

const $ = (id) => document.getElementById(id);

// ---- tabs ----
document.querySelectorAll('.tab-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
        btn.classList.add('active');
        const tab = btn.dataset.tab;
        document.querySelectorAll('main section').forEach(s => s.classList.add('hidden'));
        $(tab).classList.remove('hidden');
        if (tab === 'profile') loadProfile();
        if (tab === 'config') loadConfig();
    });
});

async function api(path, opts = {}) {
    const r = await fetch(path, {
        headers: { 'Content-Type': 'application/json' },
        ...opts
    });
    return r.json();
}

// ---- profile ----
async function loadProfile() {
    const p = await api('/api/profile');
    $('profile-json').value = JSON.stringify(p, null, 2);
}

$('save-profile').addEventListener('click', async () => {
    try {
        const profile = JSON.parse($('profile-json').value);
        const r = await api('/api/profile', { method: 'POST', body: JSON.stringify({ profile }) });
        $('profile-msg').textContent = r.success ? '✅ ذخیره شد' : '❌ خطا';
    } catch (e) {
        $('profile-msg').textContent = '❌ JSON نامعتبر: ' + e.message;
    }
});

// ---- search ----
$('run-search').addEventListener('click', async () => {
    const kw = $('search-kw').value.trim();
    $('search-msg').textContent = '⏳ در حال جستجو...';
    const r = await api('/api/search', { method: 'POST', body: JSON.stringify({ keyword: kw }) });
    if (r.success) {
        $('search-msg').textContent = `✅ ${r.count} شغل منطبق پیدا شد`;
        // switch to matches
        document.querySelector('[data-tab="matches"]').click();
        renderMatches(r.jobs);
    } else {
        $('search-msg').textContent = '❌ خطا';
    }
});

function renderMatches(jobs) {
    const el = $('matches-list');
    if (!jobs.length) { el.innerHTML = '<p class="text-slate-500">هیچ موردی یافت نشد.</p>'; return; }
    el.innerHTML = jobs.map(j => `
        <div class="border border-slate-700 rounded-lg p-3">
            <div class="flex justify-between items-start">
                <div>
                    <p class="font-semibold text-sky-300">${j.title}</p>
                    <p class="text-xs text-slate-400">${j.company} · ${j.location}</p>
                </div>
                <span class="text-emerald-400 font-bold">${j.total_score ?? '—'}</span>
            </div>
            ${j.exclusion_reasons?.length ? `<p class="text-xs text-rose-400 mt-1">رد شد: ${j.exclusion_reasons.join(' | ')}</p>` : ''}
            <a href="${j.url}" target="_blank" class="text-xs text-sky-500 underline">مشاهده آگهی</a>
        </div>
    `).join('');
}

// ---- resume ----
$('gen-resume').addEventListener('click', async () => {
    const r = await api('/api/resume');
    if (r.success) {
        $('resume-out').innerHTML = r.bullets.map(b =>
            `<p>▪ ${b.title}: ${b.text} <span class="text-slate-500">(${b.source})</span></p>`
        ).join('') + (r.warnings.length ? `<p class="text-amber-400">⚠ ${r.warnings.join('; ')}</p>` : '');
        $('resume-link').classList.remove('hidden');
    }
});

// ---- config ----
async function loadConfig() {
    const c = await api('/api/config');
    $('cfg-url').value = c.base_url;
    $('cfg-key').value = '';
    $('cfg-model').value = c.model;
    $('model-badge').textContent = 'model: ' + c.model;
}

$('save-config').addEventListener('click', async () => {
    const body = {
        base_url: $('cfg-url').value.trim(),
        api_key: $('cfg-key').value.trim() || 'ollama',
        model: $('cfg-model').value.trim()
    };
    const r = await api('/api/config', { method: 'POST', body: JSON.stringify(body) });
    $('cfg-msg').textContent = r.success ? '✅ تنظیمات ذخیره شد' : '❌ خطا';
    if (r.success) $('model-badge').textContent = 'model: ' + body.model;
});
