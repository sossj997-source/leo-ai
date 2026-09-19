const BRIDGE = 'http://127.0.0.1:8765';
let busy = false;

async function postResult(id, success, result = null, error = null) {
  try {
    await fetch(`${BRIDGE}/browser/result`, {
      method: 'POST',
      headers: {'Content-Type': 'application/json'},
      body: JSON.stringify({id, success, result, error})
    });
  } catch (_) {}
}

async function activeTab() {
  const tabs = await chrome.tabs.query({active: true, lastFocusedWindow: true});
  return tabs[0] || null;
}

async function openUrl(url) {
  const tab = await chrome.tabs.create({url, active: true});
  return `Opened ${url} in a new Chrome tab.`;
}

async function search(query) {
  const tab = await activeTab();
  if (!tab || !tab.id) throw new Error('No active Chrome tab is available.');
  const q = String(query || '').trim();
  if (!q) throw new Error('Search query is empty.');

  const host = new URL(tab.url || 'https://www.google.com').hostname;
  let target;
  if (host.includes('youtube.com')) {
    target = `https://www.youtube.com/results?search_query=${encodeURIComponent(q)}`;
  } else if (host.includes('google.')) {
    target = `https://www.google.com/search?q=${encodeURIComponent(q)}`;
  } else {
    target = `https://www.google.com/search?q=${encodeURIComponent(q)}`;
  }
  await chrome.tabs.update(tab.id, {url: target, active: true});
  return `Searched for '${q}'.`;
}

async function clickFirstResult() {
  const tab = await activeTab();
  if (!tab || !tab.id) throw new Error('No active Chrome tab is available.');

  const result = await chrome.scripting.executeScript({target: {tabId: tab.id}, func: () => {
    const host = location.hostname;
    if (host.includes('youtube.com')) {
      const candidates = [...document.querySelectorAll('ytd-video-renderer a#video-title, ytd-video-renderer a[href*="/watch?v="]')];
      const el = candidates.find(x => x.offsetParent !== null && x.href && x.href.includes('/watch?v='));
      if (!el) return {ok:false, error:'No visible YouTube video result found.'};
      el.scrollIntoView({block:'center'});
      el.click();
      return {ok:true, text:el.textContent?.trim() || 'first YouTube video'};
    }
    if (host.includes('google.')) {
      const links = [...document.querySelectorAll('#search a')].filter(a => a.querySelector('h3') && a.offsetParent !== null && a.href);
      const el = links[0];
      if (!el) return {ok:false, error:'No visible Google result found.'};
      el.click();
      return {ok:true, text:el.querySelector('h3')?.textContent?.trim() || 'first search result'};
    }
    return {ok:false, error:'First-result clicking is supported on YouTube and Google.'};
  }});

  const r = result?.[0]?.result;
  if (!r?.ok) throw new Error(r?.error || 'Could not click first result.');
  return `Opened ${r.text}.`;
}

async function handle(cmd) {
  switch (cmd.action) {
    case 'focus': {
      const tab = await activeTab();
      if (!tab) throw new Error('Chrome is open but no active tab was found.');
      return 'Existing Chrome is connected and ready.';
    }
    case 'open_url': return openUrl(cmd.params?.url);
    case 'search': return search(cmd.params?.query);
    case 'click_first_result': return clickFirstResult();
    default: throw new Error(`Unsupported browser action: ${cmd.action}`);
  }
}

async function poll() {
  if (busy) return;
  busy = true;
  try {
    const res = await fetch(`${BRIDGE}/browser/poll`, {cache: 'no-store'});
    const data = await res.json();
    if (data.command) {
      const cmd = data.command;
      try {
        const result = await handle(cmd);
        await postResult(cmd.id, true, result, null);
      } catch (e) {
        await postResult(cmd.id, false, null, e?.message || String(e));
      }
    }
  } catch (_) {
    // Leo may be starting; retry below.
  } finally {
    busy = false;
    setTimeout(poll, 200);
  }
}

poll();
