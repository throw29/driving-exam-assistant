/**
 * 通用 UI 工具：DOM 构建、Toast、按钮状态、Markdown 纯文本渲染、本地存储
 * 所有动态文本一律使用 textContent，避免上传题库 / 聊天内容造成 XSS。
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  let toastTimer = null;

  function $(selector, root) {
    return (root || document).querySelector(selector);
  }

  function $$(selector, root) {
    return Array.prototype.slice.call((root || document).querySelectorAll(selector));
  }

  function create(tagName, className, text) {
    const node = document.createElement(tagName);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
  }

  function clear(node) {
    if (!node) return;
    while (node.firstChild) node.removeChild(node.firstChild);
  }

  function show(node, visible) {
    if (!node) return;
    node.hidden = !visible;
  }

  function toast(message, type, duration) {
    const node = $('#toast');
    if (!node) return;
    clearTimeout(toastTimer);
    node.textContent = message;
    node.className = 'toast is-visible' + (type === 'error' ? ' is-error' : '') + (type === 'success' ? ' is-success' : '');
    toastTimer = setTimeout(function () {
      node.className = 'toast';
    }, duration || 3400);
  }

  function setBusy(button, busy, busyText) {
    if (!button) return;
    if (busy) {
      if (!button.dataset.originalHtml) {
        button.dataset.originalHtml = button.innerHTML;
      }
      button.disabled = true;
      button.classList.add('is-loading');
      if (busyText) button.textContent = busyText;
    } else {
      button.disabled = false;
      button.classList.remove('is-loading');
      if (button.dataset.originalHtml) {
        button.innerHTML = button.dataset.originalHtml;
        delete button.dataset.originalHtml;
      }
    }
  }

  function formatBytes(bytes) {
    if (!bytes && bytes !== 0) return '';
    if (bytes < 1024) return bytes + ' B';
    if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB';
    return (bytes / 1024 / 1024).toFixed(2) + ' MB';
  }

  function formatScore(value) {
    const num = Number(value);
    if (!Number.isFinite(num)) return '0';
    return Number.isInteger(num) ? String(num) : num.toFixed(1);
  }

  function normalizeTypeName(type) {
    if (type === 'multiple') return '多选题';
    if (type === 'judge') return '判断题';
    return '单选题';
  }

  function typeClass(type) {
    if (type === 'multiple') return 'is-multiple';
    if (type === 'judge') return 'is-judge';
    return '';
  }

  function stripInlineMarkdown(text) {
    return String(text)
      .replace(/\*\*(.+?)\*\*/g, '$1')
      .replace(/`([^`]+)`/g, '$1')
      .replace(/^#{1,6}\s*/gm, '')
      .replace(/^\s*>\s?/gm, '')
      .trim();
  }

  /**
   * 将后端纯文本 / 轻量 Markdown 回复渲染为段落与列表（不使用 innerHTML）
   */
  function renderPlainReply(container, markdown) {
    const lines = String(markdown || '').split('\n');
    let list = null;
    lines.forEach(function (rawLine) {
      const line = rawLine.trim();
      if (!line || line === '---') {
        list = null;
        return;
      }
      if (/^[-*]\s+/.test(line)) {
        if (!list) {
          list = create('ul');
          container.appendChild(list);
        }
        list.appendChild(create('li', '', stripInlineMarkdown(line.replace(/^[-*]\s+/, ''))));
        return;
      }
      list = null;
      if (/^###\s+/.test(line) || /^\*\*[^*]+\*\*$/.test(line)) {
        const heading = create('strong', 'plain-title', stripInlineMarkdown(line));
        container.appendChild(heading);
        return;
      }
      container.appendChild(create('p', '', stripInlineMarkdown(line)));
    });
  }

  function loadStorage(key, fallback) {
    try {
      const raw = window.localStorage.getItem(key);
      if (!raw) return fallback;
      return JSON.parse(raw);
    } catch (error) {
      return fallback;
    }
  }

  function saveStorage(key, value) {
    try {
      window.localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (error) {
      return false;
    }
  }

  function removeStorage(key) {
    try {
      window.localStorage.removeItem(key);
    } catch (error) {
      /* ignore */
    }
  }

  function uid(prefix) {
    const cryptoObj = window.crypto || window.msCrypto;
    if (cryptoObj && typeof cryptoObj.randomUUID === 'function') {
      return prefix + '_' + cryptoObj.randomUUID().replace(/-/g, '').slice(0, 20);
    }
    return prefix + '_' + Date.now().toString(36) + Math.random().toString(36).slice(2, 10);
  }

  function scrollToTop() {
    window.scrollTo({ top: 0, behavior: 'auto' });
  }

  function isOnline() {
    return navigator.onLine !== false;
  }

  DKA.ui = {
    $: $,
    $$: $$,
    create: create,
    clear: clear,
    show: show,
    toast: toast,
    setBusy: setBusy,
    formatBytes: formatBytes,
    formatScore: formatScore,
    normalizeTypeName: normalizeTypeName,
    typeClass: typeClass,
    stripInlineMarkdown: stripInlineMarkdown,
    renderPlainReply: renderPlainReply,
    loadStorage: loadStorage,
    saveStorage: saveStorage,
    removeStorage: removeStorage,
    uid: uid,
    scrollToTop: scrollToTop,
    isOnline: isOnline
  };
})(window);
