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
      'top.filemgr': '📁 文件管理',
      'top.filemgrTitle': '浏览/编辑设备文件，远程更新应用层代码',
      'fm.close': '✕ 返回',
      'fm.title': '📁 文件管理',
      'fm.tabBrowse': '浏览',
      'fm.tabUpdate': '更新',
      'fm.up': '⬆ 上级',
      'fm.newFile': '＋ 新建文件',
      'fm.newDir': '＋ 新建目录',
      'fm.upload': '⬆ 上传',
      'fm.refresh': '↻ 刷新',
      'fm.save': '💾 保存',
      'fm.rename': '✎ 重命名',
      'fm.download': '⬇ 下载',
      'fm.delete': '🗑 删除',
      'fm.upWarn': '⚠️ 上传将覆盖设备上的同名文件！修改 lib/ 与 www/ 应用层代码后，需重启板子才会生效。',
      'fm.upPick': '📂 选择本地文件夹或文件',
      'fm.upBaseLabel': '目标根目录（设备端，默认 /）',
      'fm.upStart': '🚀 开始上传',
      'fm.upHint': '选择文件后这里会显示将上传到设备的文件与目标路径。',
      'fm.listEmpty': '（空目录）',
      'fm.nofile': '在左侧选择文件进行编辑',
      'fm.fileDanger': '系统文件！修改需谨慎，重启后生效',
      'fm.warnDanger': '🔴 当前目录包含系统文件/应用层代码（lib、www），修改需谨慎，重启板子后生效。',
      'fm.toastSaved': '已保存',
      'fm.toastCreated': '已创建',
      'fm.toastDeleted': '已删除',
      'fm.toastRenamed': '已重命名',
      'fm.toastUploaded': '已上传',
      'fm.confirmDelete': '确定删除',
      'fm.confirmDeleteDanger': '🔴 这是系统文件，删除可能导致设备无法启动！确定删除',
      'fm.confirmRenameDanger': '🔴 这是系统文件，重命名可能导致设备无法启动！确定重命名？',
      'fm.confirmLeave': '当前文件有未保存的修改，继续会丢失。确定？',
      'fm.renamePrompt': '新文件名：',
      'fm.newFilePrompt': '新文件名（如 test.py）：',
      'fm.newDirPrompt': '新目录名：',
      'fm.emptyName': '名字不能为空',
      'fm.upCount': '将上传',
      'fm.upTotal': '共',
      'fm.upConfirm': '开始上传？将覆盖设备上的同名文件！',
      'fm.upProgress': '上传中',
      'fm.upDone': '全部上传完成，共',
      'fm.upFiles': '个文件',
      'fm.upPartial': '部分失败，成功',
      'fm.upFailOne': '上传失败',
      'fm.upReboot': '↻ 重启板子使新代码生效',
      'fm.upRebootNote': 'lib/、www/ 等应用层代码需重启后才生效。',
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
      'top.filemgr': '📁 File Manager',
      'top.filemgrTitle': 'Browse/edit device files, remotely update app code',
      'fm.close': '✕ Back',
      'fm.title': '📁 File Manager',
      'fm.tabBrowse': 'Browse',
      'fm.tabUpdate': 'Update',
      'fm.up': '⬆ Up',
      'fm.newFile': '＋ New file',
      'fm.newDir': '＋ New folder',
      'fm.upload': '⬆ Upload',
      'fm.refresh': '↻ Refresh',
      'fm.save': '💾 Save',
      'fm.rename': '✎ Rename',
      'fm.download': '⬇ Download',
      'fm.delete': '🗑 Delete',
      'fm.upWarn': '⚠️ Uploads will overwrite files with the same name on the device! Changes to lib/ and www/ take effect only after a reboot.',
      'fm.upPick': '📂 Pick local folder or files',
      'fm.upBaseLabel': 'Target root (device path, default /)',
      'fm.upStart': '🚀 Start upload',
      'fm.upHint': 'After picking files, the target paths on the device are shown here.',
      'fm.listEmpty': '(empty folder)',
      'fm.nofile': 'Select a file on the left to edit',
      'fm.fileDanger': 'System file! Edit with care; takes effect after reboot',
      'fm.warnDanger': '🔴 This folder contains system/app-layer files (lib, www). Edit with care; changes take effect after reboot.',
      'fm.toastSaved': 'Saved',
      'fm.toastCreated': 'Created',
      'fm.toastDeleted': 'Deleted',
      'fm.toastRenamed': 'Renamed',
      'fm.toastUploaded': 'Uploaded',
      'fm.confirmDelete': 'Delete',
      'fm.confirmDeleteDanger': '🔴 This is a system file; deleting it may brick the device! Delete',
      'fm.confirmRenameDanger': '🔴 This is a system file; renaming it may brick the device! Rename?',
      'fm.confirmLeave': 'Current file has unsaved changes. Continue will lose them. OK?',
      'fm.renamePrompt': 'New file name:',
      'fm.newFilePrompt': 'New file name (e.g. test.py):',
      'fm.newDirPrompt': 'New folder name:',
      'fm.emptyName': 'Name cannot be empty',
      'fm.upCount': 'Uploading',
      'fm.upTotal': 'total',
      'fm.upConfirm': 'Start upload? Files with the same name on the device will be overwritten!',
      'fm.upProgress': 'Uploading',
      'fm.upDone': 'All uploaded,',
      'fm.upFiles': 'files',
      'fm.upPartial': 'Some failed, succeeded',
      'fm.upFailOne': 'Upload failed',
      'fm.upReboot': '↻ Reboot board to apply',
      'fm.upRebootNote': 'App-layer code (lib/, www/) only takes effect after reboot.',
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
  var editorHost;
  var fmEditorHost;

  function editorCfg() {
    return {
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
    };
  }

  function fmEditorCfg() {
    return {
      mode: null,
      lineNumbers: true,
      indentUnit: 4,
      tabSize: 4,
      matchBrackets: true,
      autoCloseBrackets: true,
      extraKeys: { 'Ctrl-S': function () { fmSave(); } },
    };
  }

  /* C3 上 CodeMirror 由 cm 分片（cm-partK.js.gz）延迟加载，先给 textarea
     兜底，保证页面可用。 */
  function makeFallback(host, onChange) {
    var ta = document.createElement('textarea');
    ta.className = 'ta-fallback';
    ta.spellcheck = false;
    host.appendChild(ta);
    if (onChange) ta.addEventListener('input', onChange);
    return {
      isFallback: true,
      getValue: function () { return ta.value || ''; },
      setValue: function (v) { ta.value = v || ''; },
      refresh: function () {},
      setOption: function () {},
      on: function () {},
    };
  }

  function cmOrFallback(host, cfg, onChange) {
    if (typeof CodeMirror === 'function') {
      var cm = CodeMirror(host, cfg);
      cm.on('change', onChange);
      return cm;
    }
    return makeFallback(host, onChange);
  }

  function initEditor() {
    editorHost = $('editor');
    editor = cmOrFallback(editorHost, editorCfg(),
      function () { state.dirty = true; updateTitle(); });
  }

  /* cm 分片全部到达并 eval 后，把 textarea 兜底升级为 CodeMirror，保留已编辑内容。 */
  function upgradeToCm(name) {
    if (typeof CodeMirror !== 'function') return false;
    var host = name === 'fm' ? fmEditorHost : editorHost;
    var cur = name === 'fm' ? fmEditor : editor;
    if (!host || !cur || !cur.isFallback) return false;
    var val = cur.getValue();
    host.innerHTML = '';
    if (name === 'fm') {
      fmEditor = CodeMirror(host, fmEditorCfg());
      fmEditor.on('change', function () { fm.dirty = true; fmUpdateUi(); });
    } else {
      editor = CodeMirror(host, editorCfg());
      editor.on('change', function () { state.dirty = true; updateTitle(); });
    }
    var cm = name === 'fm' ? fmEditor : editor;
    cm.setValue(val);
    cm.refresh();
    return true;
  }

  /* C3：打开编辑器（openProgram / fmOpenFile）时自动拉取 CodeMirror 合并包。
     ~193KB 单次传输会压垮单核 C3 的 lwIP 缓冲，故切成多个 ~8KB gzip 分片
     逐个 fetch，片间保留 600ms 间隔给 lwIP pbuf 释放窗口。后端另有并发上限
     （C3 限 3 并发，超限关闭连接）兜底，前端不再做任何限制/暂停。
     S3 已同步加载 CodeMirror，此函数直接跳过。分片数由 build_inline.py
     生成内联页时按实际值替换。 */
  var CM_PARTS = 4;
  var CM_GAP = 600;
  var cmLoading = false;
  var _cmParts = [];
  function loadCodeMirror() {
    if (cmLoading || typeof CodeMirror === 'function' ||
        !((editor && editor.isFallback) || (fmEditor && fmEditor.isFallback))) {
      return;
    }
    cmLoading = true;
    _cmParts.length = 0;
    _fetchCmPart(0);
  }
  function _fetchCmPart(i) {
    fetch('/cm/cm-part' + i + '.js', {cache: 'no-store'}).then(function (r) {
      if (!r.ok) throw new Error('cm-part' + i + ' HTTP ' + r.status);
      return r.text();
    }).then(function (text) {
      _cmParts[i] = text;
      if (i + 1 < CM_PARTS) {
        setTimeout(function () { _fetchCmPart(i + 1); }, CM_GAP);
        return;
      }
      var code = _cmParts.join('');
      _cmParts.length = 0;
      /* 间接 eval：在全局作用域执行，CodeMirror 的 var 声明成为全局。 */
      (0, eval)(code);
      cmLoading = false;
      upgradeToCm('editor');
      upgradeToCm('fm');
    }).catch(function () {
      cmLoading = false;
      /* 分片失败不自动重试：保持安静降级 textarea。 */
    });
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
    loadCodeMirror();
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
      var ver = state.sys ? state.sys.app_version : '';
      var brd = state.sys ? state.sys.board : '';
      if (brd === 'esp32c3') brd = 'C3';
      else if (brd === 'esp32s3') brd = 'S3';
      else if (brd) brd = brd.toUpperCase();
      var tv = $('title-ver');
      if (tv) tv.textContent = ver ? (' ' + ver + (brd ? ' · ' + brd : '')) : '';
      document.title = 'ESP32 Web Runner' + (ver ? ' ' + ver : '');
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

    /* 文件管理 / 远程更新 */
    $('btn-filemgr').addEventListener('click', openFilemgr);
    $('fm-close').addEventListener('click', closeFilemgr);
    $('fm-tab-browse').addEventListener('click', function () { fmSwitchTab('browse'); });
    $('fm-tab-update').addEventListener('click', function () { fmSwitchTab('update'); });
    $('fm-up').addEventListener('click', function () {
      if (!fmConfirmLeave()) return;
      var p = fm.path;
      if (p === '/') return;
      fm.path = p.replace(/\/+$/, '').replace(/\/[^/]*$/, '') || '/';
      fm.currentFile = null; fm.dirty = false;
      fmEditor.setValue('');
      fmUpdateUi();
      fmList();
    });
    $('fm-refresh').addEventListener('click', fmList);
    $('fm-newfile').addEventListener('click', fmNewFile);
    $('fm-newdir').addEventListener('click', fmNewDir);
    $('fm-upload').addEventListener('click', fmUpload);
    $('fm-save').addEventListener('click', fmSave);
    $('fm-rename').addEventListener('click', fmRename);
    $('fm-download').addEventListener('click', fmDownload);
    $('fm-delete').addEventListener('click', fmDelete);
    $('up-pick').addEventListener('click', function () { $('up-files').click(); });
    $('up-files').addEventListener('change', onUpFilesChange);
    $('up-base').addEventListener('input', onUpFilesChange);
    $('up-start').addEventListener('click', startUpload);

    window.addEventListener('beforeunload', function (ev) {
      if (state.dirty) { ev.preventDefault(); ev.returnValue = ''; }
    });
  }

  /* ---------- 文件管理 / 远程更新 ---------- */
  var fm = {
    path: '/',
    currentFile: null,   // {name, path, dangerous, size}
    dirty: false,
    rows: [],
    uploading: false,
  };

  function el(tag, text, cls) {
    var n = document.createElement(tag);
    if (text !== undefined && text !== null) n.textContent = text;
    if (cls) n.className = cls;
    return n;
  }

  function fmJoin(base, name) {
    var b = String(base == null ? '/' : base);
    b = b.replace(/\/+$/, '') || '/';
    if (b === '/') return '/' + name;
    return b + '/' + name;
  }

  function fmSize(n) {
    if (n == null) return '?';
    if (n < 1024) return n + ' B';
    if (n < 1024 * 1024) return (n / 1024).toFixed(1) + ' KB';
    return (n / 1024 / 1024).toFixed(2) + ' MB';
  }

  function isDangerPath(p) {
    var boots = ['/main.py', '/boot.py', '/c3_config.py', '/config.json'];
    if (boots.indexOf(p) >= 0) return true;
    return p === '/lib' || p.indexOf('/lib/') === 0 ||
      p === '/www' || p.indexOf('/www/') === 0;
  }

  function putRaw(path, content, extraQuery) {
    var headers = { 'X-Auth-Token': state.token, 'Content-Type': 'application/octet-stream' };
    return fetch('/api/fs/file?path=' + encodeURIComponent(path) + (extraQuery || ''), {
      method: 'PUT', headers: headers, body: content,
    }).then(function (res) {
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

  var fmEditor;
  function initFmEditor() {
    fmEditorHost = $('fm-editor');
    fmEditor = cmOrFallback(fmEditorHost, fmEditorCfg(),
      function () { fm.dirty = true; fmUpdateUi(); });
  }

  function openFilemgr() {
    show('filemgr');
    fmSwitchTab('browse');
    fmList();
  }

  function closeFilemgr() {
    if (fm.dirty && fm.currentFile) {
      if (!confirm(t('fm.confirmLeave'))) return;
    }
    hide('filemgr');
    refreshPrograms();
  }

  function fmSwitchTab(tab) {
    $('fm-tab-browse').classList.toggle('active', tab === 'browse');
    $('fm-tab-update').classList.toggle('active', tab === 'update');
    $('fm-browse').classList.toggle('hidden', tab !== 'browse');
    $('fm-update').classList.toggle('hidden', tab !== 'update');
    if (tab === 'browse') setTimeout(function () { fmEditor.refresh(); }, 50);
  }

  function fmConfirmLeave() {
    if (fm.dirty && fm.currentFile) return confirm(t('fm.confirmLeave'));
    return true;
  }

  function fmList() {
    api('/api/fs/list?path=' + encodeURIComponent(fm.path)).then(function (data) {
      fm.path = data.path || fm.path;
      $('fm-path').textContent = fm.path;
      var warn = $('fm-warn');
      if (data.dangerous) { warn.classList.remove('hidden'); warn.textContent = t('fm.warnDanger'); }
      else warn.classList.add('hidden');
      renderFmList(data.entries || []);
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  function renderFmList(entries) {
    var ul = $('fm-list');
    ul.innerHTML = '';
    entries.forEach(function (e) {
      var li = document.createElement('li');
      var full = fmJoin(fm.path, e.name);
      if (fm.currentFile && fm.currentFile.path === full) li.className = 'active';
      var name = el('span', (e.dir ? '📁 ' : '📄 ') + e.name, 'fm-name ' + (e.dir ? 'dir' : 'file'));
      var size = el('span', e.dir ? '—' : fmSize(e.size), 'fm-size muted');
      var danger = el('span', isDangerPath(full) ? '🔴' : '', 'fm-danger');
      li.appendChild(name);
      li.appendChild(danger);
      li.appendChild(size);
      li.onclick = function () {
        if (!fmConfirmLeave()) return;
        if (e.dir) {
          fm.path = full;
          fm.currentFile = null; fm.dirty = false;
          fmEditor.setValue('');
          fmUpdateUi();
          fmList();
        } else {
          fmOpenFile(e.name);
        }
      };
      ul.appendChild(li);
    });
    if (!entries.length) ul.appendChild(el('li', t('fm.listEmpty'), 'muted'));
  }

  /* 文件管理器大文件分段读：单次 read 限制 limit 字节（C3 弱射频大响应
     会停滞），循环拉取后前端拼接。每段在 UTF-8 字符边界切开，拼接无损。 */
  var FM_CHUNK = 8192;
  function fmFetchText(p) {
    return api('/api/fs/read?path=' + encodeURIComponent(p) + '&limit=' + FM_CHUNK)
      .then(function (first) {
        if (first.done) return { meta: first, text: first.text || '' };
        var parts = [first.text || ''];
        var off = first.offset;
        function next() {
          return api('/api/fs/read?path=' + encodeURIComponent(p) +
              '&offset=' + off + '&limit=' + FM_CHUNK).then(function (d) {
            parts.push(d.text || '');
            off = d.offset;
            if (!d.done) return next();
            return { meta: first, text: parts.join('') };
          });
        }
        return next();
      });
  }

  function fmOpenFile(name) {
    loadCodeMirror();
    var p = fmJoin(fm.path, name);
    fmFetchText(p).then(function (r) {
      var data = r.meta;
      fm.currentFile = { name: data.name, path: data.path, dangerous: data.dangerous, size: data.size };
      fm.dirty = false;
      fmEditor.setValue(r.text || '');
      fmEditor.setOption('mode',
        name.toLowerCase().slice(-3) === '.py' ? { name: 'python', version: 3 } : null);
      fmUpdateUi();
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  function fmUpdateUi() {
    var has = fm.currentFile != null;
    $('fm-save').disabled = !has;
    $('fm-rename').disabled = !has;
    $('fm-download').disabled = !has;
    $('fm-delete').disabled = !has;
    var info = $('fm-fileinfo');
    if (has) {
      var danger = fm.currentFile.dangerous ? ' 🔴 ' + t('fm.fileDanger') : '';
      info.textContent = fm.currentFile.path + '  (' + fmSize(fm.currentFile.size) + ')' + danger;
      info.className = fm.currentFile.dangerous ? 'fm-fileinfo danger' : 'fm-fileinfo muted';
      $('fm-save').textContent = (fm.dirty ? '● ' : '') + t('fm.save');
    } else {
      info.textContent = t('fm.nofile');
      info.className = 'fm-fileinfo muted';
      $('fm-save').textContent = t('fm.save');
    }
  }

  function fmSave() {
    if (!fm.currentFile) return;
    var text = fmEditor.getValue();
    var bytes = new TextEncoder().encode(text);
    if (bytes.length <= FM_CHUNK) {
      putRaw(fm.currentFile.path, bytes).then(fmSaved)
        .catch(function (err) { toast(err.message, 'error'); });
      return;
    }
    /* 大文件分片保存：首片 append=0（后端开 .tmp 覆盖），后续 append=1
       追加，最后一片 final=1 提交。严格顺序，失败中止。 */
    var off = 0;
    function next(append) {
      var chunk = bytes.subarray(off, Math.min(off + FM_CHUNK, bytes.length));
      var final = (off + chunk.length >= bytes.length);
      var q = '&append=' + (append ? '1' : '0') + (final ? '&final=1' : '');
      return putRaw(fm.currentFile.path, chunk, q).then(function () {
        off += chunk.length;
        if (off < bytes.length) return next(true);
      });
    }
    next(false).then(fmSaved)
      .catch(function (err) { toast(err.message, 'error'); });
  }

  function fmSaved() {
    fm.dirty = false;
    fmUpdateUi();
    toast(t('fm.toastSaved') + ' ' + fm.currentFile.name, 'ok');
  }

  function fmRename() {
    if (!fm.currentFile) return;
    var newName = prompt(t('fm.renamePrompt'), fm.currentFile.name);
    if (!newName) return;
    newName = newName.trim();
    if (!newName) { toast(t('fm.emptyName'), 'error'); return; }
    if (newName === fm.currentFile.name) return;
    var to = fmJoin(fm.path, newName);
    var danger = fm.currentFile.dangerous || isDangerPath(to);
    if (danger && !confirm(t('fm.confirmRenameDanger'))) return;
    api('/api/fs/rename', { method: 'POST', body: { from: fm.currentFile.path, to: to, force: danger || undefined } })
      .then(function () {
        fm.currentFile.path = to;
        fm.currentFile.name = newName;
        fm.currentFile.dangerous = isDangerPath(to);
        fmList();
        fmUpdateUi();
        toast(t('fm.toastRenamed'), 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
  }

  function fmDelete() {
    if (!fm.currentFile) return;
    var p = fm.currentFile.path;
    var danger = fm.currentFile.dangerous;
    var msg = (danger ? t('fm.confirmDeleteDanger') : t('fm.confirmDelete')) + ' ' + p + '?';
    if (!confirm(msg)) return;
    api('/api/fs/delete?path=' + encodeURIComponent(p) + (danger ? '&force=1' : ''),
      { method: 'POST', body: {} })
      .then(function () {
        fm.currentFile = null; fm.dirty = false;
        fmEditor.setValue('');
        fmUpdateUi();
        fmList();
        toast(t('fm.toastDeleted'), 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
  }

  function fmDownload() {
    if (!fm.currentFile) return;
    fetch('/api/fs/file?path=' + encodeURIComponent(fm.currentFile.path),
      { headers: { 'X-Auth-Token': state.token } })
      .then(function (res) {
        if (res.status === 401) { showLogin(); throw new Error(t('err.loginRequired')); }
        if (!res.ok) throw new Error('HTTP ' + res.status);
        return res.blob();
      })
      .then(function (blob) {
        var url = URL.createObjectURL(blob);
        var a = document.createElement('a');
        a.href = url;
        a.download = fm.currentFile.name;
        a.click();
        setTimeout(function () { URL.revokeObjectURL(url); }, 2000);
      })
      .catch(function (err) { toast(err.message, 'error'); });
  }

  function fmNewFile() {
    var name = prompt(t('fm.newFilePrompt'), 'newfile.txt');
    if (!name) return;
    name = name.trim();
    if (!name) { toast(t('fm.emptyName'), 'error'); return; }
    var p = fmJoin(fm.path, name);
    putRaw(p, '').then(function () {
      fmList();
      toast(t('fm.toastCreated') + ' ' + name, 'ok');
    }).catch(function (err) { toast(err.message, 'error'); });
  }

  function fmNewDir() {
    var name = prompt(t('fm.newDirPrompt'), 'newdir');
    if (!name) return;
    name = name.trim();
    if (!name) { toast(t('fm.emptyName'), 'error'); return; }
    var p = fmJoin(fm.path, name);
    api('/api/fs/mkdir?path=' + encodeURIComponent(p), { method: 'POST', body: {} })
      .then(function () {
        fmList();
        toast(t('fm.toastCreated') + ' ' + name, 'ok');
      }).catch(function (err) { toast(err.message, 'error'); });
  }

  function fmUpload() {
    var input = document.createElement('input');
    input.type = 'file';
    input.onchange = function () {
      var f = input.files[0];
      if (!f) return;
      var p = fmJoin(fm.path, f.name);
      var rd = new FileReader();
      rd.onload = function () {
        putRaw(p, rd.result).then(function () {
          fmList();
          toast(t('fm.toastUploaded') + ' ' + f.name, 'ok');
        }).catch(function (err) { toast(err.message, 'error'); });
      };
      rd.onerror = function () { toast(t('err.emptyResponse'), 'error'); };
      rd.readAsText(f);
    };
    input.click();
  }

  /* ---------- 更新（批量上传覆盖） ---------- */
  function onUpFilesChange() {
    var files = Array.prototype.slice.call($('up-files').files || []);
    var base = ($('up-base').value || '/').trim() || '/';
    fm.rows = files.map(function (f) {
      var rel = f.webkitRelativePath || f.name;
      return { file: f, rel: rel, target: fmJoin(base, rel), size: f.size };
    });
    renderUpPreview(fm.rows);
    $('up-start').disabled = fm.rows.length === 0 || fm.uploading;
  }

  function renderUpPreview(rows) {
    var elBox = $('up-preview');
    elBox.innerHTML = '';
    if (!rows.length) {
      elBox.appendChild(el('div', t('fm.upHint'), 'muted'));
      return;
    }
    var total = rows.reduce(function (s, r) { return s + r.size; }, 0);
    elBox.appendChild(el('div',
      t('fm.upCount') + ' ' + rows.length + '  ·  ' + t('fm.upTotal') + ' ' + fmSize(total),
      'up-count'));
    rows.forEach(function (r) {
      var row = el('div', '', 'up-row');
      row.appendChild(el('span', r.target, 'up-target'));
      row.appendChild(el('span', fmSize(r.size), 'up-size muted'));
      elBox.appendChild(row);
    });
  }

  function readFileText(file) {
    return new Promise(function (resolve, reject) {
      var rd = new FileReader();
      rd.onload = function () { resolve(rd.result); };
      rd.onerror = function () { reject(new Error('read failed')); };
      rd.readAsText(file);
    });
  }

  function startUpload() {
    if (fm.uploading || !fm.rows.length) return;
    if (!confirm(t('fm.upConfirm'))) return;
    fm.uploading = true;
    $('up-start').disabled = true;
    var prog = $('up-progress');
    var result = $('up-result');
    prog.innerHTML = '';
    result.innerHTML = '';
    var rows = fm.rows;
    var ok = 0, fail = 0, i = 0;

    function draw() {
      prog.innerHTML = '<div class="up-bar"><div class="up-bar-inner" style="width:' +
        Math.round(i / rows.length * 100) + '%"></div></div>' +
        '<div class="muted">' + t('fm.upProgress') + ' ' + i + '/' + rows.length +
        ' — ' + esc(rows[i - 1] ? rows[i - 1].target : '') + '</div>';
    }

    function next() {
      if (i >= rows.length) {
        fm.uploading = false;
        $('up-start').disabled = false;
        finishUpload(ok, fail);
        return;
      }
      var r = rows[i];
      readFileText(r.file).then(function (text) {
        return putRaw(r.target, text);
      }).then(function () {
        ok++; i++; draw(); next();
      }).catch(function (err) {
        fail++; i++;
        result.appendChild(el('div', t('fm.upFailOne') + ' ' + r.target + ' — ' + err.message, 'up-fail'));
        draw(); next();
      });
    }
    draw();
    next();
  }

  function finishUpload(ok, fail) {
    var result = $('up-result');
    result.appendChild(el('div',
      fail === 0
        ? t('fm.upDone') + ' ' + ok + ' ' + t('fm.upFiles')
        : t('fm.upPartial') + ' ' + ok + '/' + (ok + fail),
      fail === 0 ? 'up-ok' : 'up-warn'));
    var btn = document.createElement('button');
    btn.className = 'btn primary';
    btn.textContent = t('fm.upReboot');
    btn.onclick = function () {
      if (!confirm(t('confirm.reboot'))) return;
      api('/api/reboot', { method: 'POST', body: {} }).then(function () { toast(t('toast.rebooting')); });
    };
    result.appendChild(btn);
    result.appendChild(el('div', t('fm.upRebootNote'), 'muted'));
  }

  /* ---------- 启动 ---------- */
  applyI18n();
  initEditor();
  initFmEditor();
  bind();
  refreshPrograms();
  pollStatus();
  connectWS();
  setInterval(function () { pollStatus(); }, 2000);
  setInterval(function () { if (state.wsReady && state.ws) { try { state.ws.send(JSON.stringify({ type: 'ping' })); } catch (e) { } } }, 15000);
})();