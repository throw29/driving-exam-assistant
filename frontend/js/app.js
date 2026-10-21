/**
 * 应用入口：Tab 导航、后端连接状态、各功能模块初始化
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  const api = DKA.api;
  const ui = DKA.ui;

  const TAB_NAMES = ['exam', 'chat', 'grading'];
  let currentTab = 'exam';
  let healthTimer = null;

  function validTab(name) {
    return TAB_NAMES.indexOf(name) !== -1;
  }

  function setHash(name) {
    try {
      window.history.replaceState(null, '', '#' + name);
    } catch (error) {
      /* file:// 等环境可能限制 history，忽略即可 */
    }
  }

  function activateTab(name, options) {
    const opts = options || {};
    if (!validTab(name)) name = 'exam';
    currentTab = name;

    ui.$$('.tab').forEach(function (button) {
      const active = button.dataset.tab === name;
      button.classList.toggle('is-active', active);
      button.setAttribute('aria-selected', active ? 'true' : 'false');
      button.tabIndex = active ? 0 : -1;
    });

    ui.$$('.panel').forEach(function (panel) {
      const active = panel.id === 'panel-' + name;
      panel.classList.toggle('is-active', active);
      panel.setAttribute('aria-hidden', active ? 'false' : 'true');
    });

    if (opts.updateHash !== false) setHash(name);

    if (name === 'chat' && DKA.chat && typeof DKA.chat.onShow === 'function') {
      window.setTimeout(DKA.chat.onShow, 60);
    }
    if (opts.scroll !== false) {
      window.scrollTo({ top: 0, behavior: 'auto' });
    }
  }

  function bindTabs() {
    ui.$$('.tab').forEach(function (button) {
      button.addEventListener('click', function () {
        activateTab(button.dataset.tab);
      });
      button.addEventListener('keydown', function (event) {
        const index = TAB_NAMES.indexOf(button.dataset.tab);
        let next = null;
        if (event.key === 'ArrowRight') next = (index + 1) % TAB_NAMES.length;
        if (event.key === 'ArrowLeft') next = (index - 1 + TAB_NAMES.length) % TAB_NAMES.length;
        if (event.key === 'Home') next = 0;
        if (event.key === 'End') next = TAB_NAMES.length - 1;
        if (next === null) return;
        event.preventDefault();
        const targetTab = TAB_NAMES[next];
        activateTab(targetTab);
        const target = ui.$('#tab-' + targetTab);
        if (target) target.focus();
      });
    });

    ui.$$('[data-tab-link]').forEach(function (link) {
      link.addEventListener('click', function (event) {
        event.preventDefault();
        activateTab(link.dataset.tabLink);
      });
    });
  }

  function setStatus(state, text, title) {
    const pill = ui.$('#serverStatus');
    const label = ui.$('#serverStatusText');
    if (!pill || !label) return;
    pill.classList.remove('is-ok', 'is-error', 'is-checking');
    pill.classList.add('is-' + state);
    label.textContent = text;
    pill.title = title || '点击重新检测后端连接';
  }

  async function checkHealth() {
    setStatus('checking', '连接检测中', '正在检测 ' + DKA.config.API_BASE_URL);
    try {
      const data = await api.health();
      setStatus(
        'ok',
        '服务正常',
        '后端：' + DKA.config.API_BASE_URL + ' · ' + (data.time || '') + ' · 点击重新检测'
      );
    } catch (error) {
      if (error.status === 401) {
        setStatus(
          'error',
          'API-KEY 无效',
          '请检查 frontend/js/config.js 中的 API_KEY 与后端 .env 是否一致'
        );
      } else if (error.code === 'NETWORK' || error.code === 'TIMEOUT') {
        setStatus(
          'error',
          '后端未连接',
          '请启动后端服务：cd backend && uv run serve。当前地址：' + DKA.config.API_BASE_URL
        );
      } else {
        setStatus('error', '连接异常', error.message || '后端连接异常');
      }
    }
  }

  function bindStatus() {
    const pill = ui.$('#serverStatus');
    if (pill) {
      pill.addEventListener('click', function () {
        checkHealth();
      });
    }
    healthTimer = window.setInterval(checkHealth, 60000);
    window.addEventListener('beforeunload', function () {
      if (healthTimer) window.clearInterval(healthTimer);
    });
  }

  function initModules() {
    [
      ['exam', DKA.exam],
      ['chat', DKA.chat],
      ['grading', DKA.grading]
    ].forEach(function (pair) {
      const name = pair[0];
      const module = pair[1];
      if (!module || typeof module.init !== 'function') {
        console.error('模块未正确加载：' + name);
        return;
      }
      try {
        const result = module.init();
        if (result && typeof result.catch === 'function') {
          result.catch(function (error) {
            console.error('模块初始化失败：' + name, error);
          });
        }
      } catch (error) {
        console.error('模块初始化异常：' + name, error);
      }
    });
  }

  function init() {
    const hash = (window.location.hash || '').replace(/^#/, '');
    const initial = validTab(hash) ? hash : 'exam';

    bindTabs();
    bindStatus();
    activateTab(initial, { updateHash: false, scroll: false });
    initModules();
    checkHealth();

    window.addEventListener('hashchange', function () {
      const next = (window.location.hash || '').replace(/^#/, '');
      if (validTab(next) && next !== currentTab) {
        activateTab(next, { updateHash: false });
      }
    });
  }

  if (document.readyState === 'loading') {
    document.addEventListener('DOMContentLoaded', init);
  } else {
    init();
  }

  DKA.app = {
    activateTab: activateTab,
    checkHealth: checkHealth
  };
})(window);
