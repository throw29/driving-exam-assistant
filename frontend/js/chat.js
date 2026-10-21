/**
 * 功能二：对话式驾考知识点智能查询
 * - 左右气泡、多轮对话
 * - 历史记录 localStorage 持久化，刷新恢复
 * - 结构化知识点渲染（讲解 / 要点 / 记忆技巧 / 易错提醒）
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  const api = DKA.api;
  const ui = DKA.ui;
  const config = DKA.config;

  const FALLBACK_HOT = [
    '闯红灯扣几分？',
    '高速公路最低限速是多少？',
    '酒驾和醉驾有什么区别？',
    '科目二坡道起步怎么不熄火？'
  ];

  const FALLBACK_CAPABILITIES = [
    '交通信号、标志标线的含义与记忆方法',
    '路口让行、超车、掉头、高速公路通行规则',
    '酒驾、超速、肇事逃逸等违法处罚与记分',
    '驾驶证实习期、换证等车管业务',
    '科目二 / 科目三操作技巧与灯光模拟',
    '爆胎、制动失灵、事故急救等应急处置',
    '科目一 / 科目四答题技巧与易错点'
  ];

  const FALLBACK_CATEGORIES = [
    '交通信号与标志',
    '通行规则与让行',
    '违法处罚与记分',
    '驾驶证与车管业务',
    '安全行车与操作技巧',
    '科目二 / 科目三',
    '紧急情况与事故处理',
    '文明驾驶与答题技巧'
  ];

  const state = {
    initialized: false,
    sessionId: null,
    messages: [],
    suggestions: null,
    loading: false,
    typingEl: null,
    storageWarned: false
  };

  let els = {};

  function cacheElements() {
    els = {
      messages: ui.$('#chatMessages'),
      form: ui.$('#chatForm'),
      input: ui.$('#chatInput'),
      sendBtn: ui.$('#sendChatBtn'),
      clearBtn: ui.$('#clearChatBtn'),
      hotQuestions: ui.$('#hotQuestions'),
      categories: ui.$('#chatCategories'),
      kbTotal: ui.$('#chatKbTotal'),
      kbTotalTop: ui.$('#kbTotal')
    };
  }

  function formatTime(value) {
    const date = value ? new Date(value) : new Date();
    if (Number.isNaN(date.getTime())) return '';
    return (
      String(date.getHours()).padStart(2, '0') +
      ':' +
      String(date.getMinutes()).padStart(2, '0')
    );
  }

  function buildWelcome() {
    const hot = (state.suggestions && state.suggestions.hot_questions) || FALLBACK_HOT;
    const capabilities =
      (state.suggestions && state.suggestions.capabilities) || FALLBACK_CAPABILITIES;
    return {
      role: 'assistant',
      welcome: true,
      text: '',
      at: new Date().toISOString(),
      data: {
        welcome: true,
        hot_questions: hot.slice(0, 4),
        capabilities: capabilities
      }
    };
  }

  function loadStoredHistory() {
    const stored = ui.loadStorage(config.CHAT_STORAGE_KEY, null);
    if (!stored || !Array.isArray(stored.messages)) return [];
    if (stored.sessionId && /^[A-Za-z0-9_-]{4,64}$/.test(stored.sessionId)) {
      state.sessionId = stored.sessionId;
    }
    return stored.messages
      .filter(function (message) {
        return (
          message &&
          (message.role === 'user' || message.role === 'assistant') &&
          !message.welcome &&
          !message.error &&
          typeof message.text === 'string'
        );
      })
      .slice(-config.CHAT_MAX_STORED);
  }

  function saveHistory() {
    const payload = {
      version: 1,
      sessionId: state.sessionId,
      messages: state.messages
        .filter(function (message) {
          return !message.welcome && !message.error;
        })
        .slice(-config.CHAT_MAX_STORED)
    };
    const saved = ui.saveStorage(config.CHAT_STORAGE_KEY, payload);
    if (!saved && !state.storageWarned) {
      state.storageWarned = true;
      ui.toast('浏览器本地存储空间不足，聊天记录可能无法保存。', 'error', 5000);
    }
  }

  function scrollToBottom() {
    if (!els.messages) return;
    els.messages.scrollTop = els.messages.scrollHeight;
  }

  function renderSidebar() {
    if (!els.hotQuestions || !els.categories) return;
    const hot =
      (state.suggestions && state.suggestions.hot_questions) || FALLBACK_HOT;
    const categories =
      (state.suggestions && state.suggestions.categories) ||
      FALLBACK_CATEGORIES.map(function (name) {
        return { name: name };
      });

    ui.clear(els.hotQuestions);
    hot.slice(0, 7).forEach(function (question) {
      const button = ui.create('button', 'hot-question', question);
      button.type = 'button';
      button.addEventListener('click', function () {
        sendMessage(question);
      });
      els.hotQuestions.appendChild(button);
    });

    ui.clear(els.categories);
    categories.forEach(function (category) {
      els.categories.appendChild(ui.create('span', 'category-pill', category.name));
    });
    if (!categories.length) {
      els.categories.appendChild(
        ui.create('span', 'loading-text', '知识分类加载失败')
      );
    }
    if (els.kbTotal && state.suggestions) {
      els.kbTotal.textContent = String(state.suggestions.total_knowledge_points);
    }
    if (els.kbTotalTop && state.suggestions) {
      els.kbTotalTop.textContent = String(state.suggestions.total_knowledge_points);
    }
  }

  function addMessage(role, text, extra) {
    const message = Object.assign(
      {
        role: role,
        text: text || '',
        at: new Date().toISOString()
      },
      extra || {}
    );
    state.messages.push(message);
    return message;
  }

  function renderWelcome(bubble) {
    const wrap = ui.create('div', 'topic');
    const head = ui.create('div', 'topic-head');
    head.appendChild(ui.create('span', 'topic-title', '你好，我是驾考知识助手'));
    head.appendChild(ui.create('span', 'topic-category', '驾考专用'));
    wrap.appendChild(head);
    wrap.appendChild(
      ui.create(
        'p',
        'topic-summary',
        '我可以按知识点为你讲解交规、标志、处罚、操作技巧和应试方法。试着从下面的问题开始：'
      )
    );

    const welcomeData = (state.messages[0] && state.messages[0].data) || {};
    const capabilities = welcomeData.capabilities || FALLBACK_CAPABILITIES;
    const list = ui.create('ul', 'topic-points');
    capabilities.slice(0, 4).forEach(function (capability) {
      list.appendChild(ui.create('li', '', capability));
    });
    wrap.appendChild(list);

    const chips = ui.create('div', 'topic-suggestions');
    (welcomeData.hot_questions && welcomeData.hot_questions.length
      ? welcomeData.hot_questions
      : FALLBACK_HOT
    ).forEach(function (question) {
      const chip = ui.create('button', 'suggestion-chip', question);
      chip.type = 'button';
      chip.addEventListener('click', function () {
        sendMessage(question);
      });
      chips.appendChild(chip);
    });
    wrap.appendChild(chips);

    const note = ui.create('p', 'chat-disclaimer', '回答仅覆盖驾考知识范围；未收录的问题会明确提示。');
    wrap.appendChild(note);
    bubble.appendChild(wrap);
  }

  function renderStructuredAnswer(bubble, data) {
    if (data.context_used) {
      bubble.appendChild(
        ui.create('p', 'chat-disclaimer', '已结合上一轮对话理解你的问题。')
      );
    }

    (data.topics || []).forEach(function (topic, index) {
      const wrap = ui.create('div', 'topic');
      if (index > 0) wrap.style.marginTop = '18px';

      const head = ui.create('div', 'topic-head');
      head.appendChild(ui.create('span', 'topic-title', topic.title));
      head.appendChild(ui.create('span', 'topic-category', topic.category));
      wrap.appendChild(head);

      wrap.appendChild(ui.create('p', 'topic-summary', topic.summary));

      if (topic.points && topic.points.length) {
        wrap.appendChild(ui.create('div', 'topic-label', '知识点'));
        const list = ui.create('ul', 'topic-points');
        topic.points.forEach(function (point) {
          list.appendChild(ui.create('li', '', point));
        });
        wrap.appendChild(list);
      }

      if (topic.memory_tip) {
        const tip = ui.create('div', 'tip-box');
        tip.appendChild(ui.create('strong', '', '记忆技巧：'));
        tip.appendChild(document.createTextNode(topic.memory_tip));
        wrap.appendChild(tip);
      }

      if (topic.pitfalls && topic.pitfalls.length) {
        const box = ui.create('div', 'pitfall-box');
        box.appendChild(ui.create('strong', '', '易错提醒：'));
        const list = ui.create('ul');
        topic.pitfalls.forEach(function (pitfall) {
          list.appendChild(ui.create('li', '', pitfall));
        });
        box.appendChild(list);
        wrap.appendChild(box);
      }

      if (topic.note) {
        wrap.appendChild(ui.create('p', 'chat-disclaimer', topic.note));
      }

      if (topic.suggested_questions && topic.suggested_questions.length) {
        const chips = ui.create('div', 'topic-suggestions');
        topic.suggested_questions.slice(0, 3).forEach(function (question) {
          const chip = ui.create('button', 'suggestion-chip', question);
          chip.type = 'button';
          chip.addEventListener('click', function () {
            sendMessage(question);
          });
          chips.appendChild(chip);
        });
        wrap.appendChild(chips);
      }

      bubble.appendChild(wrap);
    });

    if (data.related_topics && data.related_topics.length) {
      const related = ui.create('div', 'related-line');
      related.appendChild(document.createTextNode('相关知识点：'));
      data.related_topics.forEach(function (topic, index) {
        const button = ui.create('button', '', topic.title);
        button.type = 'button';
        button.addEventListener('click', function () {
          sendMessage(topic.title);
        });
        related.appendChild(button);
        if (index < data.related_topics.length - 1) {
          related.appendChild(document.createTextNode('、'));
        }
      });
      bubble.appendChild(related);
    }

    if (data.suggestions && data.suggestions.length) {
      const chips = ui.create('div', 'topic-suggestions');
      data.suggestions.slice(0, 4).forEach(function (question) {
        const chip = ui.create('button', 'suggestion-chip', question);
        chip.type = 'button';
        chip.addEventListener('click', function () {
          sendMessage(question);
        });
        chips.appendChild(chip);
      });
      bubble.appendChild(chips);
    }

    if (data.disclaimer) {
      bubble.appendChild(ui.create('p', 'chat-disclaimer', data.disclaimer));
    }
  }

  function renderMessage(message) {
    const wrapper = ui.create('div', 'message ' + (message.role === 'user' ? 'is-user' : 'is-assistant'));
    wrapper.appendChild(
      ui.create('span', 'message-avatar', message.role === 'user' ? '我' : 'AI')
    );

    const body = ui.create('div', 'message-body');
    const meta = ui.create(
      'div',
      'message-meta',
      (message.role === 'user' ? '你' : '驾考知识助手') +
        (message.at ? ' · ' + formatTime(message.at) : '')
    );
    body.appendChild(meta);

    const bubble = ui.create('div', 'message-bubble');
    if (message.error) {
      bubble.classList.add('is-error');
      bubble.textContent = message.text;
    } else if (message.role === 'user') {
      bubble.textContent = message.text;
    } else if (message.welcome) {
      renderWelcome(bubble);
    } else if (message.data && message.data.topics && message.data.topics.length) {
      renderStructuredAnswer(bubble, message.data);
    } else {
      const text =
        message.text ||
        (message.data && message.data.reply_markdown) ||
        '暂时没有可展示的回答。';
      ui.renderPlainReply(bubble, text);
      if (message.data && message.data.suggestions && message.data.suggestions.length) {
        const chips = ui.create('div', 'topic-suggestions');
        message.data.suggestions.slice(0, 4).forEach(function (question) {
          const chip = ui.create('button', 'suggestion-chip', question);
          chip.type = 'button';
          chip.addEventListener('click', function () {
            sendMessage(question);
          });
          chips.appendChild(chip);
        });
        bubble.appendChild(chips);
      }
      if (message.data && message.data.disclaimer) {
        bubble.appendChild(
          ui.create('p', 'chat-disclaimer', message.data.disclaimer)
        );
      }
    }

    body.appendChild(bubble);
    wrapper.appendChild(body);
    els.messages.appendChild(wrapper);
  }

  function renderAll() {
    ui.clear(els.messages);
    state.messages.forEach(renderMessage);
    scrollToBottom();
  }

  function removeTyping() {
    if (state.typingEl && state.typingEl.parentNode) {
      state.typingEl.parentNode.removeChild(state.typingEl);
    }
    state.typingEl = null;
  }

  function showTyping() {
    removeTyping();
    const wrapper = ui.create('div', 'message is-assistant');
    wrapper.appendChild(ui.create('span', 'message-avatar', 'AI'));
    const body = ui.create('div', 'message-body');
    body.appendChild(ui.create('div', 'message-meta', '驾考知识助手 · 检索中'));
    const bubble = ui.create('div', 'message-bubble');
    const typing = ui.create('span', 'typing');
    typing.setAttribute('aria-label', '正在检索知识库');
    typing.appendChild(ui.create('i'));
    typing.appendChild(ui.create('i'));
    typing.appendChild(ui.create('i'));
    bubble.appendChild(typing);
    body.appendChild(bubble);
    wrapper.appendChild(body);
    els.messages.appendChild(wrapper);
    state.typingEl = wrapper;
    scrollToBottom();
  }

  function buildHistory() {
    return state.messages
      .filter(function (message) {
        return !message.welcome && !message.error;
      })
      .slice(-config.CHAT_HISTORY_SEND)
      .map(function (message) {
        let content = message.text;
        if (message.role === 'assistant' && message.data) {
          content = message.data.reply_markdown || content;
        }
        return {
          role: message.role,
          content: String(content || '（无内容）').slice(0, 4000)
        };
      });
  }

  function updateSendState() {
    if (!els.sendBtn || !els.input) return;
    els.sendBtn.disabled =
      state.loading || els.input.value.trim().length === 0;
  }

  function autoResize() {
    if (!els.input) return;
    els.input.style.height = 'auto';
    els.input.style.height = Math.min(els.input.scrollHeight, 130) + 'px';
  }

  async function sendMessage(rawText) {
    const text = String(rawText || '').trim();
    if (!text) return;
    if (state.loading) {
      ui.toast('上一条问题正在检索，请稍候。', 'error', 2200);
      return;
    }
    if (text.length > 1000) {
      ui.toast('问题过长，请控制在 1000 字以内。', 'error');
      return;
    }

    const history = buildHistory();
    const userMessage = addMessage('user', text);
    renderMessage(userMessage);
    els.input.value = '';
    autoResize();
    saveHistory();
    scrollToBottom();

    state.loading = true;
    updateSendState();
    showTyping();

    try {
      const data = await api.sendChat({
        message: text,
        history: history,
        session_id: state.sessionId
      });
      removeTyping();
      const assistantMessage = addMessage(
        'assistant',
        (data && data.reply_markdown) || '',
        { data: data }
      );
      renderMessage(assistantMessage);
      saveHistory();
      scrollToBottom();
    } catch (error) {
      removeTyping();
      const errorMessage = {
        role: 'assistant',
        error: true,
        text: error.message || '回答失败，请稍后重试。',
        at: new Date().toISOString()
      };
      state.messages.push(errorMessage);
      renderMessage(errorMessage);
      scrollToBottom();
      if (error.code === 'NETWORK' || error.code === 'TIMEOUT') {
        ui.toast(error.message, 'error', 5000);
      }
    } finally {
      state.loading = false;
      updateSendState();
      els.input.focus();
    }
  }

  function clearHistory() {
    const hasMessages = state.messages.some(function (message) {
      return !message.welcome;
    });
    if (hasMessages && !window.confirm('确定清空全部聊天记录吗？此操作不可恢复。')) {
      return;
    }
    ui.removeStorage(config.CHAT_STORAGE_KEY);
    state.sessionId = ui.uid('chat');
    state.messages = [buildWelcome()];
    renderAll();
    ui.toast('聊天记录已清空。', 'success');
  }

  function handleSubmit(event) {
    event.preventDefault();
    sendMessage(els.input.value);
  }

  function handleKeydown(event) {
    if (event.key !== 'Enter' || event.shiftKey) return;
    if (event.isComposing || event.keyCode === 229) return;
    event.preventDefault();
    if (!state.loading && els.input.value.trim()) {
      sendMessage(els.input.value);
    }
  }

  function bindEvents() {
    els.form.addEventListener('submit', handleSubmit);
    els.input.addEventListener('keydown', handleKeydown);
    els.input.addEventListener('input', function () {
      autoResize();
      updateSendState();
    });
    els.clearBtn.addEventListener('click', clearHistory);
  }

  async function init() {
    if (state.initialized) return;
    state.initialized = true;
    cacheElements();
    bindEvents();

    if (!state.sessionId) state.sessionId = ui.uid('chat');
    const storedMessages = loadStoredHistory();
    state.messages = [buildWelcome()];
    storedMessages.forEach(function (message) {
      state.messages.push(message);
    });
    renderAll();
    updateSendState();

    try {
      state.suggestions = await api.getChatSuggestions();
      renderSidebar();
      if (state.messages[0] && state.messages[0].welcome) {
        state.messages[0] = buildWelcome();
      }
      renderAll();
    } catch (error) {
      renderSidebar();
    }
  }

  function onShow() {
    scrollToBottom();
    if (els.input) els.input.focus();
  }

  DKA.chat = { init: init, onShow: onShow };
})(window);
