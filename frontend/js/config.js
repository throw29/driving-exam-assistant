/**
 * 全局前端配置
 * - 修改后端地址或 API-KEY 后，刷新页面生效；也可由部署脚本注入替换。
 * - API_KEY 必须与 backend/.env 中的 DT_API_KEY 保持一致。
 */
(function (window) {
  'use strict';

  window.DKA = window.DKA || {};

  window.DKA.config = {
    API_BASE_URL: 'http://127.0.0.1:8000',
    API_KEY: 'sk-dtk-local-2026-change-me',
    REQUEST_TIMEOUT: 30000,
    UPLOAD_TIMEOUT: 60000,
    CHAT_STORAGE_KEY: 'dka.chat.history.v1',
    CHAT_MAX_STORED: 40,
    CHAT_HISTORY_SEND: 10,
    APP_VERSION: '0.1.0'
  };
})(window);
