/* ESP32 Web Runner 前端逻辑（原生 JS，无构建） */
(function () {
  'use strict';

  /* ---------- 全局状态 ---------- */
  var state = {
    programs: [],
    current: null,        // 当前打开的程序名
    dirty: false,
    token: localStorage.getItem('token') || '',
    sys: null,
    ws: null,
    wsReady: false,
    queuedConsole: [],
  };

  var $ = function (id) { return document.getElementById(id); };

  /* ---------- 工具 ---------- */
  function toast(msg, kind) {
    var el = $('toast');
    el.textContent = msg;
    el.className = 'toast ' + (kind || '');
    el.classList.remove('hidden');
    clearTimeout(el._t);
    el._t = setTimeout(function () { el.classList.add('hidden'); }, 2600);
  }

  function api(path, opts) {
    opts = opts || {};
    var headers = { 'Content-Type': 'application/json' };
    if (state.token) headers['X-Auth-Token'] = state.token;
    var init = { method: opts.method || 'GET', headers: headers };
    if (opts.body !== undefined) init.body = JSON.stringify(opts.body);
    return fetch(path, init).then(function (res) {
      if (res.status === 401) { showLogin(); throw new Error('需要登录'); }
      return res.json().then(function (data) {
        if (data && data.error && res.status >= 400) {
          var err = new Error(data.error);
          err.status = res.status;
          throw err;
        }
        return data;
      });
    });
  }

  var esc = function (s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;')
      .replace(/>/g, '&gt;').replace(/"/g, '&quot;');
  };

  /* ---------- 编辑器 ---------- */
  var editor;
  function initEditor() {
    editor = CodeMirror($('editor'), {
      value: '',
      mode: { name: 'python', version: 3, singleLineStringErrors: false },
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      indentWithTabs: false,
      matchBrackets: true,
      autoCloseBrackets: true,
      extraKeys: {
        'Ctrl-Space': 'autocomplete',
        'Ctrl-S': function (cm) { saveProgram(false); },
      },
      hintOptions: { completeSingle: false },
    });
    editor.on('change', function () { state.dirty = true; updateTitle(); });
  }

  function updateTitle() {
    var name = state.current;
    $('current-file').textContent =
      (name ? name + '.py' : '未选择程序') + (state.dirty ? '  ●' : '');
    var running = currentRunning();
    $('btn-start').disabled = running;
    $('btn-stop').disabled = !running && !programMayRun(state.current);
    $('btn-save').disabled = !state.current;
    $('btn-save-run').disabled = !state.current;
  }

  function currentRunning() {
    if (!state.current) return false;
    var p = byName(state.current);
    return p && p.status === 'running';
  }
  function programMayRun(name) {
    var p = byName(name);
    return p && (p.status === 'stopped');
  }
  function byName(name) {
    for (var i = 0; i < state.programs.length; i++)
      if (state.programs[i].name === name) return state.programs[i];
    return null;
  }

  /* ---------- 程序列表 ---------- */
  function renderList(activeName) {
    var ul = $('program-list');
    ul.innerHTML = '';
    state.programs.forEach(function (p) {
      var li = document.createElement('li');
      if (p.name === activeName) li.className = 'active';

      var dot = document.createElement('span');
      dot.className = 'status-dot ' + p.status;

      var name = document.createElement('span');
      name.className = 'pname';
      name.textContent = p.name;
      name.title = p.error || p.name;

      var type = document.createElement('span');
      type.className = 'type-tag';
      type.textContent = p.type === 'async' ? '~' : '→';

      var btnS = document.createElement('button');
      btnS.className = 'plist-btn';
      btnS.textContent = '▶';
      btnS.title = '启动';
      btnS.onclick = function (e) { e.stopPropagation(); doAction(p.name, 'start'); };

      var btnT = document.createElement('button');
      btnT.className = 'plist-btn';
      btnT.textContent = '■';
      btnT.title = '停止';
      btnT.onclick = function (e) { e.stopPropagation(); doAction(p.name, 'stop'); };

      li.appendChild(dot);
      li.appendChild(name);
      li.appendChild(type);
      li.appendChild(btnS);
      li.appendChild(btnT);

      li.onclick = function () { openProgram(p.name); };
      ul.appendChild(li);
    });
    if (!state.programs.length) {
      var li = document.createElement('li');
      li.className = 'muted';
      li.textContent = '（空）点击"新建"添加程序';
      ul.appendChild(li);
    }
  }

  function refreshPrograms(keepSelection, after) {
    api('/api/programs').then(function (data) {
      state.programs = data.programs || [];
      renderList(state.current || (keepSelection && after));
      if (after) after();
    }).catch(function (err) { console.error(err); });
  }

  /* ---------- 打开 / 保存 ---------- */
  function openProgram(name) {
    if (state.dirty) {
      if (!confirm('当前程序有未保存的修改，继续会丢失。确定？')) return;
    }
    api('/api/programs/' + encodeURIComponent(name)).then(function (data) {
      editor.setValue(data.code || '');
      state.current = data.name;
      state.dirty = false;
      renderList(state.current);
      updateTitle();
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  function saveProgram(andRun) {
    if (!state.current) return Promise.resolve();
    var body = { code: editor.getValue() };
    var method = 'PUT';
    var p = byName(state.current);
    if (andRun && p && p.status === 'running') {
      if (!confirm('保存并重启正在运行的程序？')) return Promise.resolve();
    }
    api('/api/programs/' + encodeURIComponent(state.current), { method: method, body: body })
      .then(function () {
        state.dirty = false;
        toast('已保存 ' + state.current, 'ok');
        if (andRun) return doAction(state.current, 'restart');
      })
      .then(function () {
        if (andRun) refreshPrograms();
        else updateTitle();
      })
      .catch(function (err) { toast(err.message, 'error'); });
  }

  /* ---------- 启停 ---------- */
  function doAction(name, action) {
    return api('/api/programs/' + encodeURIComponent(name) + '/' + action,
      { method: 'POST', body: {} }).then(function (data) {
        toast(data.message || action, 'ok');
        refreshPrograms();
      }).catch(function (err) { toast(err.message, 'error'); });
  }

  /* ---------- 新建 / 重命名 / 复制 / 删除 ---------- */
  var modalMode = 'new';
  function openCreate() {
    modalMode = 'new';
    $('modal-title').textContent = '新建程序';
    $('modal-input').value = '';
    document.querySelector('input[name=tmpl][value=async]').checked = true;
    show('modal');
    $('modal-input').focus();
  }

  function openRename() {
    if (!state.current) return;
    modalMode = 'rename';
    $('modal-title').textContent = '重命名 ' + state.current;
    $('modal-input').value = state.current;
    show('modal');
    $('modal-input').focus();
  }

  function modalOk() {
    var input = $('modal-input').value.trim();
    if (!input) { toast('名字不能为空', 'error'); return; }
    hide('modal');
    if (modalMode === 'new') {
      var isAsync = document.querySelector('input[name=tmpl]:checked').value === 'async';
      api('/api/programs', { method: 'POST', body: { name: input, template: isAsync ? 'async' : 'sync' } })
        .then(function () { refreshPrograms(); openProgram(input); })
        .catch(function (err) { toast(err.message, 'error'); });
    } else {
      api('/api/programs/' + encodeURIComponent(state.current) + '/rename',
        { method: 'POST', body: { name: input } })
        .then(function (data) {
          state.current = data.name;
          state.dirty = false;
          refreshPrograms();
          toast('已重命名', 'ok');
        })
        .catch(function (err) { toast(err.message, 'error'); });
    }
  }

  function duplicateProgram() {
    if (!state.current) return;
    var cnt = 1, nn = state.current + '_copy';
    while (byName(nn)) { cnt++; nn = state.current + '_copy' + cnt; }
    api('/api/programs', { method: 'POST', body: { name: nn, code: editor.getValue() } })
      .then(function () { refreshPrograms(); toast('已复制为 ' + nn, 'ok'); })
      .catch(function (err) { toast(err.message, 'error'); });
  }

  function deleteProgram() {
    if (!state.current) return;
    if (!confirm('确定删除 ' + state.current + ' ？')) return;
    var nm = state.current;
    var wasDirty = state.dirty;
    if (wasDirty && !confirm('该程序尚未保存，继续删除？')) return;
    api('/api/programs/' + encodeURIComponent(nm), { method: 'DELETE' })
      .then(function () {
        if (state.current === nm) { state.current = null; state.dirty = false; editor.setValue(''); }
        refreshPrograms(); updateTitle(); toast('已删除', 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
  }

  function downloadCurrent() {
    if (!state.current) return;
    var blob = new Blob([editor.getValue()], { type: 'text/x-python' });
    var a = document.createElement('a');
    a.href = URL.createObjectURL(blob);
    a.download = state.current + '.py';
    a.click();
    setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
  }

  /* ---------- 控制台 ---------- */
  var consoleEl = $('console');
  function appendConsole(line, cls) {
    var div = document.createElement('div');
    div.className = 'c-line ' + (cls || '');
    div.textContent = line;
    consoleEl.appendChild(div);
    while (consoleEl.childNodes.length > 2000) consoleEl.removeChild(consoleEl.firstChild);
    if ($('console-follow').checked) consoleEl.scrollTop = consoleEl.scrollHeight;
  }

  function connectWS() {
    if (state.wsReady) return;
    var proto = location.protocol === 'https:' ? 'wss://' : 'ws://';
    var url = proto + location.host + '/ws?token=' + encodeURIComponent(state.token);
    var ws;
    try { ws = new WebSocket(url); } catch (e) { setTimeout(connectWS, 3000); return; }
    state.ws = ws;
    ws.onopen = function () { state.wsReady = true; state.queuedConsole.forEach(function (l) { appendConsole(l.line, l.cls); }); state.queuedConsole = []; };
    ws.onmessage = function (ev) {
      try {
        var msg = JSON.parse(ev.data);
        if (msg.type === 'console') {
          if (msg.action === 'cleared') { consoleEl.innerHTML = ''; appendConsole('— 控制台已清空 —'); return; }
          if (!state.wsReady) { state.queuedConsole.push({ line: msg.line, cls: null }); return; }
          appendConsole(msg.line);
        }
      } catch (e) { }
    };
    ws.onclose = function () { state.wsReady = false; state.ws = null; setTimeout(connectWS, 3000); };
    ws.onerror = function () { try { ws.close(); } catch (e) { } };
  }

  /* ---------- 状态轮询 ---------- */
  function pollStatus() {
    api('/api/status').then(function (data) {
      state.sys = data.sys;
      var wasRunning = currentRunning();
      state.programs = data.programs || [];
      renderList(state.current);
      updateTitle();

      var ip = state.sys && state.sys.net ? state.sys.net : {};
      var host = location.hostname;
      var badge = $('ip-badge');
      badge.className = 'badge ' + (host === ip.sta_ip ? 'on' : '');
      badge.textContent = ip.sta_connected ? ('STA ' + ip.sta_ip) : ('AP ' + ip.ap_ip);

      var mem = state.sys ? (state.sys.mem_free / 1024) : 0;
      var fs = state.sys && state.sys.filesystem ? state.sys.filesystem.free / 1024 / 1024 : 0;
      $('sys-info').textContent = '内存 ' + mem.toFixed(0) + ' KB  ·  Flash 余 ' + fs.toFixed(1) + ' MB  ·  ' +
        (state.sys ? state.sys.version.split('(')[0] : '');
      if (state.dirty) updateTitle();
    }).catch(function (err) {
      // 401 handled by api()
    });
  }

  /* ---------- 设置 ---------- */
  function loadSettings() {
    api('/api/config').then(function (cfg) {
      $('cfg-sta-ssid').value = cfg.wifi.ssid || '';
      $('cfg-sta-pass').value = '';
      $('cfg-ap-ssid').value = cfg.ap.ssid || '';
      $('cfg-ap-pass').value = '';
      $('cfg-auth-enabled').checked = !!cfg.auth.enabled;
      $('cfg-auth-pass').value = '';
      var wrap = $('cfg-autostart-wrap');
      wrap.innerHTML = '<legend>开机自启动程序</legend>';
      state.programs.forEach(function (p) {
        var lab = document.createElement('label');
        lab.className = 'chk';
        var cb = document.createElement('input');
        cb.type = 'checkbox';
        cb.value = p.name;
        cb.checked = cfg.autostart.indexOf(p.name) >= 0;
        lab.appendChild(cb);
        lab.appendChild(document.createTextNode(p.name));
        wrap.appendChild(lab);
      });
      $('settings-msg').textContent = '';
    }).catch(function (err) { $('settings-msg').textContent = err.message; });
  }

  function saveSettings() {
    var autostart = [];
    Array.prototype.forEach.call(
      $('cfg-autostart-wrap').querySelectorAll('input[type=checkbox]:checked'),
      function (cb) { autostart.push(cb.value); });
    var body = {
      wifi: { ssid: $('cfg-sta-ssid').value.trim(), password: $('cfg-sta-pass').value },
      ap: { ssid: $('cfg-ap-ssid').value.trim(), password: $('cfg-ap-pass').value },
      auth: { enabled: $('cfg-auth-enabled').checked, password: $('cfg-auth-pass').value },
      autostart: autostart,
    };
    api('/api/config', { method: 'POST', body: body }).then(function (data) {
      $('settings-msg').textContent = data.message + '；若改了 WiFi，板子将在后台重连。';
      toast('设置已保存', 'ok');
    }).catch(function (err) { $('settings-msg').textContent = err.message; });
  }

  /* ---------- 登录 ---------- */
  function showLogin() { show('login-modal'); $('login-input').focus(); }

  function doLogin() {
    var pw = $('login-input').value;
    api('/api/login', { method: 'POST', body: { password: pw } }).then(function (data) {
      if (data.token) {
        state.token = data.token;
        localStorage.setItem('token', data.token);
      }
      hide('login-modal');
      connectWS();
      pollStatus();
      toast('欢迎回来', 'ok');
    }).catch(function (err) { $('login-input').value = ''; toast(err.message, 'error'); });
  }

  function doLogout() {
    api('/api/logout', { method: 'POST', body: {} }).catch(function () { });
    state.token = '';
    localStorage.removeItem('token');
    toast('已退出登录');
  }

  /* ---------- 弹窗辅助 ---------- */
  function show(id) { $(id).classList.remove('hidden'); }
  function hide(id) { $(id).classList.add('hidden'); }

  /* ---------- 事件绑定 ---------- */
  function bind() {
    $('btn-new').addEventListener('click', openCreate);
    $('btn-start').addEventListener('click', function () { if (state.current) doAction(state.current, 'start'); });
    $('btn-stop').addEventListener('click', function () { if (state.current) doAction(state.current, 'stop'); });
    $('btn-save').addEventListener('click', function () { saveProgram(false); });
    $('btn-save-run').addEventListener('click', function () { saveProgram(true); });
    $('btn-rename').addEventListener('click', openRename);
    $('btn-duplicate').addEventListener('click', duplicateProgram);
    $('btn-download').addEventListener('click', downloadCurrent);
    $('btn-delete').addEventListener('click', deleteProgram);
    $('btn-reboot').addEventListener('click', function () {
      if (!confirm('重启整个板子？')) return;
      api('/api/reboot', { method: 'POST', body: {} }).then(function () { toast('正在重启...'); });
    });
    $('btn-clear-console').addEventListener('click', function () { consoleEl.innerHTML = ''; });
    $('btn-settings').addEventListener('click', function () { loadSettings(); show('settings-modal'); });
    $('settings-save').addEventListener('click', saveSettings);
    $('settings-cancel').addEventListener('click', function () { hide('settings-modal'); });
    $('btn-login').addEventListener('click', showLogin);

    $('modal-ok').addEventListener('click', modalOk);
    $('modal-cancel').addEventListener('click', function () { hide('modal'); });
    $('modal-input').addEventListener('keydown', function (e) { if (e.key === 'Enter') modalOk(); });

    $('login-ok').addEventListener('click', doLogin);
    $('login-cancel').addEventListener('click', function () { hide('login-modal'); });
    $('login-input').addEventListener('keydown', function (e) { if (e.key === 'Enter') doLogin(); });

    $('file-upload').addEventListener('change', function (e) {
      var f = e.target.files[0];
      if (!f) return;
      var rd = new FileReader();
      rd.onload = function () {
        var nm = f.name.replace(/\.py$/i, '').replace(/[^\w]/g, '_');
        api('/api/programs', { method: 'POST', body: { name: nm, code: rd.result } })
          .then(function () { refreshPrograms(); openProgram(nm); toast('已导入 ' + nm, 'ok'); })
          .catch(function (err) { toast(err.message, 'error'); });
      };
      rd.readAsText(f);
      e.target.value = '';
    });

    window.addEventListener('beforeunload', function (ev) {
      if (state.dirty) { ev.preventDefault(); ev.returnValue = ''; }
    });
  }

  /* ---------- 启动 ---------- */
  initEditor();
  bind();
  refreshPrograms();
  pollStatus();
  connectWS();
  setInterval(function () { pollStatus(); }, 2000);
  setInterval(function () { if (state.wsReady && state.ws) { try { state.ws.send(JSON.stringify({ type: 'ping' })); } catch (e) { } } }, 15000);
})();