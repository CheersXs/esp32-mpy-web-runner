/* ESP32 Web Runner frontend logic (vanilla JS, no build) */
(function () {
  'use strict';

  /* ---------- i18n ---------- */
  var I18N_KEY = 'lang';
  var I18N = {
    zh: {
      'top.brand': 'ESP32 Web Runner',
      'top.ipBadge': '访问地址',
      'top.langTitle': '切换语言',
      'top.settings': '⚙ 设置',
      'top.settingsTitle': '设置',
      'top.login': '登录',
      'top.reboot': '↻ 重启',
      'top.rebootTitle': '重启板子',
      'side.programs': '程序',
      'side.new': '＋ 新建',
      'side.newTitle': '新建程序',
      'side.typeHint': '类型: <code>#type:async</code> 异步 / <code>#type:sync</code> 同步',
      'editor.placeholder': '未选择程序',
      'editor.start': '▶ 启动',
      'editor.startTitle': '启动',
      'editor.stop': '■ 停止',
      'editor.stopTitle': '停止',
      'editor.save': '💾 保存',
      'editor.saveTitle': '保存 (Ctrl+S)',
      'editor.saveRun': '保存＋重启',
      'editor.saveRunTitle': '保存并重启',
      'editor.rename': '✎ 重命名',
      'editor.renameTitle': '重命名',
      'editor.duplicate': '⧉ 复制',
      'editor.duplicateTitle': '复制为新程序',
      'editor.downloadTitle': '下载到电脑',
      'editor.deleteTitle': '删除',
      'editor.ready': '就绪',
      'console.title': '📟 实时控制台',
      'console.follow': '自动滚动',
      'console.clear': '清空',
      'common.cancel': '取消',
      'common.ok': '确定',
      'common.save': '保存',
      'common.qmark': '？',
      'modal.newTitle': '新建程序',
      'modal.renameTitle': '重命名',
      'modal.nameLabel': '程序名（字母/数字/下划线）',
      'modal.namePlaceholder': '如 blink',
      'modal.asyncRadio': '异步程序（可随时停止，需 async def main()）',
      'modal.syncRadio': '同步脚本（线程运行，跑完即止）',
      'login.title': '需要登录',
      'login.passLabel': '访问密码',
      'login.passPlaceholder': '密码',
      'login.ok': '登录',
      'settings.title': '设置',
      'settings.langFieldset': '界面语言',
      'settings.wifiFieldset': 'WiFi（STA，连你家路由器）',
      'settings.ssidLabel': 'SSID',
      'settings.scanBtn': '扫描附近 WiFi',
      'settings.scanSelectTitle': '附近可用的 WiFi',
      'settings.routerPlaceholder': '路由器名称',
      'settings.passLabel': '密码（留空保持原密码不变）',
      'settings.apFieldset': '热点（AP，板上自建）',
      'settings.apNameLabel': '热点名',
      'settings.apPassLabel': '热点密码（留空 = 开放热点）',
      'settings.authFieldset': '访问密码保护',
      'settings.authEnable': '启用访问密码',
      'settings.authPassPlaceholder': '新密码（留空则不改）',
      'settings.autostartFieldset': '开机自启动程序',
      'settings.msgSavedNote': '；若改了 WiFi，板子将在后台重连。',
      'err.loginRequired': '需要登录',
      'err.emptyResponse': '空响应',
      'list.empty': '（空）点击"新建"添加程序',
      'confirm.unsaved': '当前程序有未保存的修改，继续会丢失。确定？',
      'confirm.saveRunRunning': '保存并重启正在运行的程序？',
      'confirm.delete': '确定删除',
      'confirm.deleteUnsaved': '该程序尚未保存，继续删除？',
      'confirm.reboot': '重启整个板子？',
      'toast.savedAndRun': '已保存并重启',
      'toast.saved': '已保存',
      'toast.nameEmpty': '名字不能为空',
      'toast.renamed': '已重命名',
      'toast.duplicated': '已复制为',
      'toast.deleted': '已删除',
      'toast.settingsSaved': '设置已保存',
      'toast.welcomeBack': '欢迎回来',
      'toast.loggedOut': '已退出登录',
      'toast.rebooting': '正在重启...',
      'toast.imported': '已导入',
      'console.cleared': '— 控制台已清空 —',
      'net.notConnected': '未连接',
      'sys.mem': '内存',
      'sys.flash': 'Flash 余',
      'wifi.connected': '当前已连接 WiFi：',
      'wifi.connecting': '正在连接 WiFi…',
      'wifi.notConnectedApOnly': '未连接 WiFi（仅热点模式）',
      'wifi.scanning': '扫描中…',
      'wifi.noneFound': '附近没有发现可用 WiFi',
      'wifi.scanHint': '点击下拉选择要连接的 WiFi，然后填密码',
      'wifi.scanFailed': '扫描失败：',
    },
    en: {
      'top.brand': 'ESP32 Web Runner',
      'top.ipBadge': 'Access address',
      'top.langTitle': 'Switch language',
      'top.settings': '⚙ Settings',
      'top.settingsTitle': 'Settings',
      'top.login': 'Login',
      'top.reboot': '↻ Reboot',
      'top.rebootTitle': 'Reboot board',
      'side.programs': 'Programs',
      'side.new': '＋ New',
      'side.newTitle': 'New program',
      'side.typeHint': 'Type: <code>#type:async</code> async / <code>#type:sync</code> sync',
      'editor.placeholder': 'No program selected',
      'editor.start': '▶ Start',
      'editor.startTitle': 'Start',
      'editor.stop': '■ Stop',
      'editor.stopTitle': 'Stop',
      'editor.save': '💾 Save',
      'editor.saveTitle': 'Save (Ctrl+S)',
      'editor.saveRun': 'Save & Restart',
      'editor.saveRunTitle': 'Save and restart',
      'editor.rename': '✎ Rename',
      'editor.renameTitle': 'Rename',
      'editor.duplicate': '⧉ Duplicate',
      'editor.duplicateTitle': 'Duplicate as new program',
      'editor.downloadTitle': 'Download to PC',
      'editor.deleteTitle': 'Delete',
      'editor.ready': 'Ready',
      'console.title': '📟 Live console',
      'console.follow': 'Auto-scroll',
      'console.clear': 'Clear',
      'common.cancel': 'Cancel',
      'common.ok': 'OK',
      'common.save': 'Save',
      'common.qmark': '?',
      'modal.newTitle': 'New program',
      'modal.renameTitle': 'Rename',
      'modal.nameLabel': 'Program name (letters/digits/underscores)',
      'modal.namePlaceholder': 'e.g. blink',
      'modal.asyncRadio': 'Async program (stoppable anytime, needs async def main())',
      'modal.syncRadio': 'Sync script (runs in a thread, ends when done)',
      'login.title': 'Login required',
      'login.passLabel': 'Access password',
      'login.passPlaceholder': 'Password',
      'login.ok': 'Login',
      'settings.title': 'Settings',
      'settings.langFieldset': 'Language',
      'settings.wifiFieldset': 'WiFi (STA, connect to your router)',
      'settings.ssidLabel': 'SSID',
      'settings.scanBtn': 'Scan nearby WiFi',
      'settings.scanSelectTitle': 'Available WiFi networks',
      'settings.routerPlaceholder': 'Router name',
      'settings.passLabel': 'Password (leave blank to keep current)',
      'settings.apFieldset': 'Access point (AP, hosted by the board)',
      'settings.apNameLabel': 'AP name',
      'settings.apPassLabel': 'AP password (blank = open hotspot)',
      'settings.authFieldset': 'Access password protection',
      'settings.authEnable': 'Enable access password',
      'settings.authPassPlaceholder': 'New password (leave blank to keep)',
      'settings.autostartFieldset': 'Auto-start programs on boot',
      'settings.msgSavedNote': ' If WiFi was changed, the board will reconnect in the background.',
      'err.loginRequired': 'Login required',
      'err.emptyResponse': 'empty response',
      'list.empty': '(empty) Click "New" to add a program',
      'confirm.unsaved': 'The current program has unsaved changes. Continue will lose them. Are you sure?',
      'confirm.saveRunRunning': 'Save and restart the running program?',
      'confirm.delete': 'Delete',
      'confirm.deleteUnsaved': 'This program has unsaved changes. Delete anyway?',
      'confirm.reboot': 'Reboot the whole board?',
      'toast.savedAndRun': 'Saved and restarted',
      'toast.saved': 'Saved',
      'toast.nameEmpty': 'Name cannot be empty',
      'toast.renamed': 'Renamed',
      'toast.duplicated': 'Duplicated as',
      'toast.deleted': 'Deleted',
      'toast.settingsSaved': 'Settings saved',
      'toast.welcomeBack': 'Welcome back',
      'toast.loggedOut': 'Logged out',
      'toast.rebooting': 'Rebooting...',
      'toast.imported': 'Imported',
      'console.cleared': '— Console cleared —',
      'net.notConnected': 'Not connected',
      'sys.mem': 'Mem',
      'sys.flash': 'Flash free',
      'wifi.connected': 'Connected to WiFi:',
      'wifi.connecting': 'Connecting to WiFi…',
      'wifi.notConnectedApOnly': 'Not connected to WiFi (AP mode only)',
      'wifi.scanning': 'Scanning…',
      'wifi.noneFound': 'No WiFi networks found nearby',
      'wifi.scanHint': 'Pick a network from the dropdown, then enter the password',
      'wifi.scanFailed': 'Scan failed:',
    },
  };

  var lang = localStorage.getItem(I18N_KEY) ||
    (navigator.language && navigator.language.toLowerCase().indexOf('zh') === 0 ? 'zh' : 'en');

  function t(key) {
    var d = I18N[lang] || I18N.zh;
    return d[key] != null ? d[key] : key;
  }

  function applyI18n() {
    document.documentElement.lang = lang === 'zh' ? 'zh-CN' : 'en';
    document.querySelectorAll('[data-i18n]').forEach(function (el) {
      el.textContent = t(el.getAttribute('data-i18n'));
    });
    document.querySelectorAll('[data-i18n-title]').forEach(function (el) {
      el.setAttribute('title', t(el.getAttribute('data-i18n-title')));
    });
    document.querySelectorAll('[data-i18n-placeholder]').forEach(function (el) {
      el.setAttribute('placeholder', t(el.getAttribute('data-i18n-placeholder')));
    });
    var foot = $('side-foot');
    if (foot) foot.innerHTML = t('side.typeHint');
    var lb = $('btn-lang');
    if (lb) lb.textContent = lang === 'zh' ? 'EN' : '中文';
    var sel = $('cfg-lang');
    if (sel) sel.value = lang;
  }

  function setLang(l) {
    if (l !== 'zh' && l !== 'en') l = 'zh';
    lang = l;
    localStorage.setItem(I18N_KEY, l);
    applyI18n();
    renderList(state.current);
    updateTitle();
    showWifiStatus();
    if (!$('settings-modal').classList.contains('hidden')) loadSettings();
  }

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
      if (res.status === 401) { showLogin(); throw new Error(t('err.loginRequired')); }
      return res.text().then(function (text) {
        var data = null;
        try { data = text ? JSON.parse(text) : null; } catch (e) { data = null; }
        if (!data && res.status >= 400) {
          var err = new Error('HTTP ' + res.status + ': ' + (text || t('err.emptyResponse')));
          err.status = res.status;
          throw err;
        }
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
      (name ? name + '.py' : t('editor.placeholder')) + (state.dirty ? '  ●' : '');
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
      btnS.title = t('editor.startTitle');
      btnS.onclick = function (e) { e.stopPropagation(); doAction(p.name, 'start'); };

      var btnT = document.createElement('button');
      btnT.className = 'plist-btn';
      btnT.textContent = '■';
      btnT.title = t('editor.stopTitle');
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
      li.textContent = t('list.empty');
      ul.appendChild(li);
    }
  }

  function refreshPrograms(keepSelection, after) {
    api('/api/programs').then(function (data) {
      state.programs = data.programs || [];
      renderList(state.current);
      if (after) after();
    }).catch(function (err) { console.error(err); });
  }

  /* ---------- 打开 / 保存 ---------- */
  function openProgram(name) {
    if (state.dirty) {
      if (!confirm(t('confirm.unsaved'))) return;
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
    var p = byName(state.current);
    if (andRun && p && p.status === 'running') {
      if (!confirm(t('confirm.saveRunRunning'))) return Promise.resolve();
    }
    if (andRun) {
      // 保存并重启：后端会先停止（若在运行）→ 保存 → 启动
      return api('/api/programs/' + encodeURIComponent(state.current) + '/restart',
        { method: 'POST', body: body })
        .then(function () {
          state.dirty = false;
          toast(t('toast.savedAndRun') + ' ' + state.current, 'ok');
          refreshPrograms();
        })
        .catch(function (err) { toast(err.message, 'error'); });
    }
    // 普通保存
    return api('/api/programs/' + encodeURIComponent(state.current), { method: 'PUT', body: body })
      .then(function () {
        state.dirty = false;
        toast(t('toast.saved') + ' ' + state.current, 'ok');
        updateTitle();
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
    $('modal-title').textContent = t('modal.newTitle');
    $('modal-input').value = '';
    document.querySelector('input[name=tmpl][value=async]').checked = true;
    show('modal');
    $('modal-input').focus();
  }

  function openRename() {
    if (!state.current) return;
    modalMode = 'rename';
    $('modal-title').textContent = t('modal.renameTitle') + ' ' + state.current;
    $('modal-input').value = state.current;
    show('modal');
    $('modal-input').focus();
  }

  function modalOk() {
    var input = $('modal-input').value.trim();
    if (!input) { toast(t('toast.nameEmpty'), 'error'); return; }
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
          toast(t('toast.renamed'), 'ok');
        })
        .catch(function (err) { toast(err.message, 'error'); });
    }
  }

  function duplicateProgram() {
    if (!state.current) return;
    var cnt = 1, nn = state.current + '_copy';
    while (byName(nn)) { cnt++; nn = state.current + '_copy' + cnt; }
    api('/api/programs', { method: 'POST', body: { name: nn, code: editor.getValue() } })
      .then(function () { refreshPrograms(); toast(t('toast.duplicated') + ' ' + nn, 'ok'); })
      .catch(function (err) { toast(err.message, 'error'); });
  }

  function deleteProgram() {
    if (!state.current) return;
    if (!confirm(t('confirm.delete') + ' ' + state.current + t('common.qmark'))) return;
    var nm = state.current;
    var wasDirty = state.dirty;
    if (wasDirty && !confirm(t('confirm.deleteUnsaved'))) return;
    api('/api/programs/' + encodeURIComponent(nm), { method: 'DELETE' })
      .then(function () {
        if (state.current === nm) { state.current = null; state.dirty = false; editor.setValue(''); }
        refreshPrograms(); updateTitle(); toast(t('toast.deleted'), 'ok');
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
          if (msg.action === 'cleared') { consoleEl.innerHTML = ''; appendConsole(t('console.cleared')); return; }
          if (!state.wsReady) {
            state.queuedConsole.push({ line: msg.line, cls: null });
            if (state.queuedConsole.length > 500) state.queuedConsole.shift();
            return;
          }
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
      if (ip.sta_connected) badge.textContent = 'STA ' + ip.sta_ip;
      else if (ip.ap_ip) badge.textContent = 'AP ' + ip.ap_ip;
      else badge.textContent = t('net.notConnected');

      var mem = state.sys ? (state.sys.mem_free / 1024) : 0;
      var fs = state.sys && state.sys.filesystem ? state.sys.filesystem.free / 1024 / 1024 : 0;
      $('sys-info').textContent = t('sys.mem') + ' ' + mem.toFixed(0) + ' KB  ·  ' +
        t('sys.flash') + ' ' + fs.toFixed(1) + ' MB  ·  ' +
        (state.sys ? state.sys.version.split('(')[0] : '');
      if (state.dirty) updateTitle();
    }).catch(function (err) {
      // 401 handled by api()
    });
  }

  /* ---------- 设置 ---------- */
  function loadSettings() {
    api('/api/config').then(function (cfg) {
      $('cfg-sta-ssid-manual').value = cfg.wifi.ssid || '';
      $('cfg-sta-pass').value = '';
      $('cfg-ap-ssid').value = cfg.ap.ssid || '';
      $('cfg-ap-pass').value = '';
      // AP 被禁用（如 C3 纯 STA 模式）时隐藏整个热点设置区块
      var apWrap = $('cfg-ap-wrap');
      if (apWrap) apWrap.style.display = (cfg.ap && cfg.ap.enabled === false) ? 'none' : '';
      $('cfg-auth-enabled').checked = !!cfg.auth.enabled;
      $('cfg-auth-pass').value = '';
      $('cfg-lang').value = lang;
      showWifiStatus();
      var wrap = $('cfg-autostart-wrap');
      wrap.innerHTML = '<legend>' + t('settings.autostartFieldset') + '</legend>';
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

  function showWifiStatus() {
    var el = $('wifi-status');
    var net = (state.sys && state.sys.net) ? state.sys.net : {};
    var txt = '';
    if (net.sta_connected) txt = t('wifi.connected') + ' ' + net.sta_ip;
    else if (net.sta_ip) txt = t('wifi.connecting');
    else txt = t('wifi.notConnectedApOnly');
    el.textContent = txt;
  }

  function scanWifi() {
    var msgEl = $('wifi-scan-msg');
    msgEl.textContent = t('wifi.scanning');
    var sel = $('cfg-sta-ssid');
    sel.innerHTML = '';
    sel.classList.remove('hidden');
    api('/api/scan').then(function (data) {
      var nets = data.networks || [];
      if (!nets.length) { msgEl.textContent = t('wifi.noneFound'); return; }
      nets.sort(function (a, b) { return (b.rssi || -200) - (a.rssi || -200); });
      nets.forEach(function (n) {
        var opt = document.createElement('option');
        opt.value = n.ssid;
        opt.textContent = n.ssid + '  (' + n.rssi + 'dBm)';
        sel.appendChild(opt);
      });
      sel.classList.remove('hidden');
      msgEl.textContent = t('wifi.scanHint');
    }).catch(function (err) { msgEl.textContent = t('wifi.scanFailed') + ' ' + err.message; });
  }

  function useScanSelection() {
    var sel = $('cfg-sta-ssid');
    if (sel.value) $('cfg-sta-ssid-manual').value = sel.value;
  }

  function saveSettings() {
    var autostart = [];
    Array.prototype.forEach.call(
      $('cfg-autostart-wrap').querySelectorAll('input[type=checkbox]:checked'),
      function (cb) { autostart.push(cb.value); });
    var body = {
      wifi: { ssid: $('cfg-sta-ssid-manual').value.trim(), password: $('cfg-sta-pass').value },
      ap: { ssid: $('cfg-ap-ssid').value.trim(), password: $('cfg-ap-pass').value },
      auth: { enabled: $('cfg-auth-enabled').checked, password: $('cfg-auth-pass').value },
      autostart: autostart,
    };
    // 若 AP 区块被隐藏（C3 纯 STA），不提交 AP 修改，保持 ap.enabled=false
    var apWrap = $('cfg-ap-wrap');
    if (apWrap && apWrap.style.display === 'none') delete body.ap;
    api('/api/config', { method: 'POST', body: body }).then(function (data) {
      $('settings-msg').textContent = data.message + t('settings.msgSavedNote');
      toast(t('toast.settingsSaved'), 'ok');
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
      toast(t('toast.welcomeBack'), 'ok');
    }).catch(function (err) { $('login-input').value = ''; toast(err.message, 'error'); });
  }

  function doLogout() {
    api('/api/logout', { method: 'POST', body: {} }).catch(function () { });
    state.token = '';
    localStorage.removeItem('token');
    toast(t('toast.loggedOut'));
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
      if (!confirm(t('confirm.reboot'))) return;
      api('/api/reboot', { method: 'POST', body: {} }).then(function () { toast(t('toast.rebooting')); });
    });
    $('btn-clear-console').addEventListener('click', function () { consoleEl.innerHTML = ''; });
    $('btn-settings').addEventListener('click', function () { loadSettings(); show('settings-modal'); });
    $('btn-scan').addEventListener('click', function (e) { e.preventDefault(); scanWifi(); });
    $('cfg-sta-ssid').addEventListener('change', useScanSelection);
    $('settings-save').addEventListener('click', saveSettings);
    $('settings-cancel').addEventListener('click', function () { hide('settings-modal'); });
    $('btn-login').addEventListener('click', showLogin);
    $('btn-lang').addEventListener('click', function () { setLang(lang === 'zh' ? 'en' : 'zh'); });
    $('cfg-lang').addEventListener('change', function () { setLang($('cfg-lang').value); });

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
          .then(function () { refreshPrograms(); openProgram(nm); toast(t('toast.imported') + ' ' + nm, 'ok'); })
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
  applyI18n();
  initEditor();
  bind();
  refreshPrograms();
  pollStatus();
  connectWS();
  setInterval(function () { pollStatus(); }, 2000);
  setInterval(function () { if (state.wsReady && state.ws) { try { state.ws.send(JSON.stringify({ type: 'ping' })); } catch (e) { } } }, 15000);
})();