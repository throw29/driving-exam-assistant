/**
 * API 封装（原生 fetch）
 * - 所有请求统一携带 Authorization: Bearer {API_KEY}
 * - 统一解析后端 { code, msg, data } 响应
 * - 文件下载：带鉴权 fetch -> Blob -> 浏览器下载
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  const config = DKA.config;

  class ApiError extends Error {
    constructor(message, options) {
      super(message);
      this.name = 'ApiError';
      const opts = options || {};
      this.code = opts.code !== undefined ? opts.code : 'UNKNOWN';
      this.status = opts.status || 0;
      this.data = opts.data !== undefined ? opts.data : null;
    }
  }

  function apiBase() {
    return String(config.API_BASE_URL || '').replace(/\/+$/, '');
  }

  function buildUrl(path) {
    if (/^https?:\/\//i.test(path)) return path;
    return apiBase() + (path.charAt(0) === '/' ? path : '/' + path);
  }

  function authHeaders(extra) {
    return Object.assign(
      {
        Authorization: 'Bearer ' + config.API_KEY,
        Accept: 'application/json'
      },
      extra || {}
    );
  }

  function networkErrorMessage() {
    return '无法连接后端服务，请确认后端已启动，且「' + apiBase() + '」地址与跨域配置正确。';
  }

  async function parseJsonResponse(response) {
    const type = response.headers.get('content-type') || '';
    if (!type.includes('application/json')) return null;
    try {
      return await response.json();
    } catch (error) {
      return null;
    }
  }

  /**
   * 发起 API 请求
   * @param {string} path
   * @param {{method?:string, body?:*, headers?:Object, timeout?:number}} [options]
   * @returns {Promise<*>} 返回统一响应中的 data
   */
  async function request(path, options) {
    const opts = options || {};
    const controller = new AbortController();
    const timeout = opts.timeout || config.REQUEST_TIMEOUT;
    const timer = setTimeout(function () {
      controller.abort();
    }, timeout);

    const headers = authHeaders(opts.headers);
    const fetchOptions = {
      method: opts.method || 'GET',
      headers: headers,
      signal: controller.signal
    };

    if (opts.body instanceof FormData) {
      fetchOptions.body = opts.body;
    } else if (opts.body !== undefined) {
      headers['Content-Type'] = 'application/json';
      fetchOptions.body = JSON.stringify(opts.body);
    }

    let response;
    try {
      response = await fetch(buildUrl(path), fetchOptions);
    } catch (error) {
      clearTimeout(timer);
      if (error && error.name === 'AbortError') {
        throw new ApiError('请求超时，请稍后重试。', { code: 'TIMEOUT' });
      }
      throw new ApiError(networkErrorMessage(), { code: 'NETWORK' });
    }
    clearTimeout(timer);

    const payload = await parseJsonResponse(response);

    if (!response.ok) {
      const message =
        (payload && payload.msg) || '请求失败（HTTP ' + response.status + '）';
      throw new ApiError(message, {
        code: payload && payload.code !== undefined ? payload.code : response.status,
        status: response.status,
        data: payload ? payload.data : null
      });
    }

    if (!payload) {
      throw new ApiError('服务器返回的数据格式不正确，请检查后端服务。', {
        code: 'BAD_RESPONSE',
        status: response.status
      });
    }

    if (payload.code !== 0) {
      throw new ApiError(payload.msg || '请求失败', {
        code: payload.code,
        status: response.status,
        data: payload.data
      });
    }

    return payload.data;
  }

  function decodeFilename(contentDisposition, fallback) {
    if (!contentDisposition) return fallback;
    const utf8 = /filename\*=UTF-8''([^;]+)/i.exec(contentDisposition);
    if (utf8 && utf8[1]) {
      try {
        return decodeURIComponent(utf8[1]);
      } catch (error) {
        /* ignore */
      }
    }
    const plain = /filename="?([^";]+)"?/i.exec(contentDisposition);
    if (plain && plain[1]) {
      try {
        return decodeURIComponent(plain[1]);
      } catch (error) {
        return plain[1];
      }
    }
    return fallback;
  }

  /**
   * 带鉴权下载文件（浏览器直出）
   * @param {string} path
   * @param {string} fallbackName
   * @returns {Promise<string>} 实际下载文件名
   */
  async function download(path, fallbackName) {
    let response;
    try {
      response = await fetch(buildUrl(path), {
        method: 'GET',
        headers: authHeaders({ Accept: 'text/markdown, application/octet-stream' })
      });
    } catch (error) {
      throw new ApiError(networkErrorMessage(), { code: 'NETWORK' });
    }

    if (!response.ok) {
      const payload = await parseJsonResponse(response);
      throw new ApiError(
        (payload && payload.msg) || '下载失败（HTTP ' + response.status + '）',
        {
          code: payload && payload.code !== undefined ? payload.code : response.status,
          status: response.status,
          data: payload ? payload.data : null
        }
      );
    }

    const blob = await response.blob();
    const filename = decodeFilename(
      response.headers.get('content-disposition'),
      fallbackName || 'download.md'
    );
    const url = URL.createObjectURL(blob);
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = filename;
    anchor.style.display = 'none';
    document.body.appendChild(anchor);
    anchor.click();
    anchor.remove();
    setTimeout(function () {
      URL.revokeObjectURL(url);
    }, 4000);
    return filename;
  }

  const api = {
    ApiError: ApiError,
    health: function () {
      return request('/api/v1/health');
    },
    getExamMeta: function () {
      return request('/api/v1/exams/meta');
    },
    generateExam: function (payload) {
      return request('/api/v1/exams/generate', { method: 'POST', body: payload });
    },
    getExam: function (examId) {
      return request('/api/v1/exams/' + encodeURIComponent(examId));
    },
    previewExamMarkdown: function (examId) {
      return request('/api/v1/exams/' + encodeURIComponent(examId) + '/preview');
    },
    downloadExam: function (examId, includeAnswers, fallbackName) {
      const suffix = includeAnswers ? 'download' : 'download?include_answers=false';
      return download(
        '/api/v1/exams/' + encodeURIComponent(examId) + '/' + suffix,
        fallbackName
      );
    },
    getChatSuggestions: function () {
      return request('/api/v1/chat/suggestions');
    },
    sendChat: function (payload) {
      return request('/api/v1/chat', { method: 'POST', body: payload });
    },
    uploadQuestions: function (file) {
      const form = new FormData();
      form.append('file', file, file.name);
      return request('/api/v1/questions/upload', {
        method: 'POST',
        body: form,
        timeout: config.UPLOAD_TIMEOUT
      });
    },
    submitGrading: function (payload) {
      return request('/api/v1/grading/submit', { method: 'POST', body: payload });
    },
    downloadWrongAnswers: function (resultId, fallbackName) {
      return download(
        '/api/v1/grading/' + encodeURIComponent(resultId) + '/wrong-answers/download',
        fallbackName
      );
    }
  };

  DKA.api = api;
  DKA.ApiError = ApiError;
})(window);
