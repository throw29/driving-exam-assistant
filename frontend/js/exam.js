/**
 * 功能一：一键生成驾考试卷 + Markdown 下载
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  const api = DKA.api;
  const ui = DKA.ui;

  const TYPE_ORDER = ['single', 'judge', 'multiple'];
  const NUMERALS = ['一', '二', '三', '四', '五', '六', '七', '八'];
  const QUICK_COUNTS = [10, 20, 30, 50, 100];

  const state = {
    initialized: false,
    meta: null,
    subjectKey: 'subject1',
    types: new Set(),
    chapters: new Set(),
    count: 20,
    exam: null,
    generating: false
  };

  let els = {};

  function cacheElements() {
    els = {
      form: ui.$('#examForm'),
      subjectOptions: ui.$('#subjectOptions'),
      countInput: ui.$('#questionCount'),
      quickCounts: ui.$('#quickCounts'),
      countHint: ui.$('#countHint'),
      typeOptions: ui.$('#typeOptions'),
      chapterOptions: ui.$('#chapterOptions'),
      selectAll: ui.$('#selectAllChapters'),
      clearChapters: ui.$('#clearChapters'),
      shuffle: ui.$('#shuffleQuestions'),
      generateBtn: ui.$('#generateBtn'),
      error: ui.$('#examError'),
      empty: ui.$('#examEmpty'),
      loading: ui.$('#examLoading'),
      result: ui.$('#examResult'),
      previewCard: ui.$('#examPreview'),
      subjectBadge: ui.$('#examSubjectBadge'),
      title: ui.$('#examTitle'),
      meta: ui.$('#examMeta'),
      rules: ui.$('#examRules'),
      questions: ui.$('#examQuestions'),
      answerKey: ui.$('#examAnswerKey'),
      downloadBtn: ui.$('#downloadExamBtn'),
      blankBtn: ui.$('#downloadBlankBtn'),
      markdownToggle: ui.$('#toggleMarkdownBtn'),
      markdownSource: ui.$('#markdownSource'),
      markdownCode: ui.$('#markdownCode'),
      copyMarkdown: ui.$('#copyMarkdownBtn'),
      closeMarkdown: ui.$('#closeMarkdownBtn'),
      bankTotal: ui.$('#bankTotal')
    };
  }

  function getSubject() {
    if (!state.meta) return null;
    return state.meta.subjects.find(function (item) {
      return item.key === state.subjectKey;
    }) || null;
  }

  function selectedTypes() {
    return TYPE_ORDER.filter(function (type) {
      return state.types.has(type);
    });
  }

  function availableCount() {
    const subject = getSubject();
    if (!subject) return 0;
    const types = selectedTypes();
    if (!types.length || !state.chapters.size) return 0;
    let total = 0;
    subject.chapters.forEach(function (chapter) {
      if (!state.chapters.has(chapter.name)) return;
      types.forEach(function (type) {
        total += Number(chapter.counts[type] || 0);
      });
    });
    return total;
  }

  function chapterCount(chapter) {
    const types = selectedTypes();
    return types.reduce(function (sum, type) {
      return sum + Number(chapter.counts[type] || 0);
    }, 0);
  }

  function showError(message) {
    if (!els.error) return;
    els.error.textContent = message;
    els.error.hidden = false;
  }

  function clearError() {
    if (!els.error) return;
    els.error.textContent = '';
    els.error.hidden = true;
  }

  function updateCountHint() {
    if (!els.countHint || !state.meta) return;
    els.countHint.classList.remove('is-warning');
    if (!selectedTypes().length) {
      els.countHint.textContent = '请至少选择一种题型';
      els.countHint.classList.add('is-warning');
      return;
    }
    if (!state.chapters.size) {
      els.countHint.textContent = '请至少选择一个章节';
      els.countHint.classList.add('is-warning');
      return;
    }
    const available = availableCount();
    const count = Number(els.countInput.value);
    if (!Number.isFinite(count) || count < 1) {
      els.countHint.textContent = '请输入有效的题目数量';
      els.countHint.classList.add('is-warning');
      return;
    }
    if (count > available) {
      els.countHint.textContent = '当前筛选只有 ' + available + ' 题可用，请减少题量或放宽筛选';
      els.countHint.classList.add('is-warning');
      return;
    }
    els.countHint.textContent =
      '当前筛选可用 ' + available + ' 题 · 满分 100 分，90 分及格';
  }

  function updateGenerateState() {
    if (!els.generateBtn) return;
    els.generateBtn.disabled = !state.meta || availableCount() === 0;
  }

  function renderSubjects() {
    if (!state.meta || !els.subjectOptions) return;
    ui.clear(els.subjectOptions);
    state.meta.subjects.forEach(function (subject) {
      const selected = subject.key === state.subjectKey;
      const label = ui.create('label', 'subject-card' + (selected ? ' is-selected' : ''));
      const input = ui.create('input');
      input.type = 'radio';
      input.name = 'exam-subject';
      input.value = subject.key;
      input.checked = selected;
      input.addEventListener('change', function () {
        if (input.checked) selectSubject(subject.key);
      });

      const name = ui.create('span', 'subject-card-name');
      name.appendChild(ui.create('span', '', subject.name));
      name.appendChild(
        ui.create('em', '', subject.total + ' 题')
      );

      const desc = ui.create('p', 'subject-card-desc', subject.description);
      const meta = ui.create(
        'p',
        'subject-card-meta',
        subject.chapters.length + ' 个章节 · 标准卷 ' + subject.exam_question_count + ' 题'
      );

      label.appendChild(input);
      label.appendChild(name);
      label.appendChild(desc);
      label.appendChild(meta);
      els.subjectOptions.appendChild(label);
    });
  }

  function renderTypes() {
    const subject = getSubject();
    if (!subject || !els.typeOptions) return;
    ui.clear(els.typeOptions);
    const supported = new Set(
      subject.supported_types.map(function (item) {
        return item.key;
      })
    );

    TYPE_ORDER.forEach(function (type) {
      const isSupported = supported.has(type);
      const checked = isSupported && state.types.has(type);
      const label = ui.create(
        'label',
        'check-card' +
          (checked ? ' is-selected' : '') +
          (isSupported ? '' : ' is-disabled')
      );
      if (!isSupported) {
        label.title = subject.name + '不包含该题型';
      }

      const input = ui.create('input');
      input.type = 'checkbox';
      input.value = type;
      input.checked = checked;
      input.disabled = !isSupported;
      input.addEventListener('change', function () {
        if (input.checked) state.types.add(type);
        else state.types.delete(type);
        label.classList.toggle('is-selected', input.checked);
        renderChapters();
        onFiltersChanged();
        clearError();
      });

      label.appendChild(input);
      label.appendChild(ui.create('span', '', ui.normalizeTypeName(type)));
      label.appendChild(
        ui.create('em', '', String(subject.type_counts[type] || 0) + ' 题')
      );
      els.typeOptions.appendChild(label);
    });
  }

  function renderChapters() {
    const subject = getSubject();
    if (!subject || !els.chapterOptions) return;
    ui.clear(els.chapterOptions);
    subject.chapters.forEach(function (chapter) {
      const checked = state.chapters.has(chapter.name);
      const count = chapterCount(chapter);
      const label = ui.create(
        'label',
        'chapter-item' + (checked ? ' is-selected' : '')
      );
      const input = ui.create('input');
      input.type = 'checkbox';
      input.value = chapter.name;
      input.checked = checked;
      input.addEventListener('change', function () {
        if (input.checked) state.chapters.add(chapter.name);
        else state.chapters.delete(chapter.name);
        label.classList.toggle('is-selected', input.checked);
        onFiltersChanged();
        clearError();
      });

      label.appendChild(input);
      label.appendChild(ui.create('span', '', chapter.name));
      label.appendChild(ui.create('em', '', count + ' 题'));
      els.chapterOptions.appendChild(label);
    });
  }

  function renderQuickCounts() {
    if (!els.quickCounts) return;
    ui.clear(els.quickCounts);
    const available = availableCount();
    if (!available) {
      els.quickCounts.appendChild(ui.create('span', 'loading-text', '暂无可选题目'));
      return;
    }
    const values = QUICK_COUNTS.filter(function (value) {
      return value <= available;
    });
    if (values.indexOf(available) === -1) values.push(available);

    values.forEach(function (value) {
      const button = ui.create(
        'button',
        Number(els.countInput.value) === value ? 'is-active' : '',
        value === available ? '全部 ' + available : String(value)
      );
      button.type = 'button';
      button.addEventListener('click', function () {
        els.countInput.value = String(value);
        state.count = value;
        renderQuickCounts();
        updateCountHint();
        clearError();
      });
      els.quickCounts.appendChild(button);
    });
  }

  function onFiltersChanged() {
    const available = availableCount();
    let count = Number(els.countInput.value);
    if (!Number.isFinite(count) || count < 1) count = 1;
    if (available > 0 && count > available) {
      count = available;
      els.countInput.value = String(count);
    }
    state.count = count;
    renderQuickCounts();
    updateCountHint();
    updateGenerateState();
  }

  function selectSubject(key) {
    const subject = state.meta.subjects.find(function (item) {
      return item.key === key;
    });
    if (!subject) return;
    state.subjectKey = key;
    state.types = new Set(
      subject.supported_types.map(function (item) {
        return item.key;
      })
    );
    state.chapters = new Set(
      subject.chapters.map(function (item) {
        return item.name;
      })
    );
    state.count = Math.min(Math.max(state.count || 20, 1), subject.total);
    els.countInput.value = String(state.count);
    els.countInput.max = String(subject.total);

    renderSubjects();
    renderTypes();
    renderChapters();
    renderQuickCounts();
    updateCountHint();
    updateGenerateState();
    clearError();
  }

  function renderExam(exam) {
    if (!exam || !els.result) return;
    state.exam = exam;

    els.subjectBadge.textContent = exam.subject.name;
    els.title.textContent = exam.title;

    ui.clear(els.meta);
    [
      ['题量', exam.question_count + ' 题'],
      ['总分', exam.total_score + ' 分'],
      ['及格', exam.pass_score + ' 分'],
      ['建议用时', exam.duration_minutes + ' 分钟'],
      ['编号', exam.exam_id],
      ['覆盖章节', exam.covered_chapters.join('、')]
    ].forEach(function (pair) {
      const chip = ui.create('span', 'chip');
      chip.appendChild(ui.create('strong', '', pair[0] + '：'));
      chip.appendChild(ui.create('span', '', pair[1]));
      els.meta.appendChild(chip);
    });

    ui.clear(els.rules);
    const rulesList = ui.create('ul');
    (exam.rules || []).forEach(function (rule) {
      rulesList.appendChild(ui.create('li', '', rule));
    });
    els.rules.appendChild(rulesList);

    ui.clear(els.questions);
    (exam.sections || []).forEach(function (section, index) {
      const sectionQuestions = exam.questions.filter(function (question) {
        return question.type === section.type;
      });
      if (!sectionQuestions.length) return;

      const heading = ui.create('h3', 'section-heading');
      heading.appendChild(
        document.createTextNode(
          (NUMERALS[index] || String(index + 1)) + '、' + section.type_name
        )
      );
      heading.appendChild(
        ui.create(
          'span',
          '',
          '共 ' + sectionQuestions.length + ' 题 · 每题 ' +
            ui.formatScore(sectionQuestions[0].score) + ' 分'
        )
      );
      els.questions.appendChild(heading);

      sectionQuestions.forEach(function (question) {
        els.questions.appendChild(buildQuestionCard(question));
      });
    });

    ui.clear(els.answerKey);
    els.answerKey.appendChild(ui.create('h3', '', '答案速查'));
    const grid = ui.create('div', 'answer-grid');
    exam.questions.forEach(function (question) {
      const cell = ui.create('div', 'answer-cell');
      cell.appendChild(ui.create('span', '', '第 ' + question.number + ' 题'));
      cell.appendChild(ui.create('strong', '', question.answer.join('、')));
      grid.appendChild(cell);
    });
    els.answerKey.appendChild(grid);

    els.markdownCode.textContent = exam.markdown || '';
    els.markdownSource.hidden = true;
    els.markdownToggle.textContent = '查看 MD 源码';

    els.empty.hidden = true;
    els.loading.hidden = true;
    els.result.hidden = false;
  }

  function buildQuestionCard(question) {
    const card = ui.create('article', 'question-card');

    const head = ui.create('div', 'q-head');
    head.appendChild(ui.create('span', 'q-number', String(question.number)));
    head.appendChild(
      ui.create('span', 'q-type ' + ui.typeClass(question.type), question.type_name)
    );
    head.appendChild(ui.create('span', 'q-chapter', question.chapter));
    head.appendChild(
      ui.create('span', 'q-score', '本题 ' + ui.formatScore(question.score) + ' 分')
    );
    card.appendChild(head);

    card.appendChild(ui.create('p', 'q-stem', question.stem));

    const optionList = ui.create('ul', 'option-list');
    question.options.forEach(function (option) {
      const item = ui.create('li', 'option-item');
      item.appendChild(ui.create('span', 'option-key', option.key));
      item.appendChild(ui.create('span', 'option-text', option.text));
      optionList.appendChild(item);
    });
    card.appendChild(optionList);

    const answerBlock = ui.create('div', 'answer-block');
    const answerLine = ui.create('div', 'answer-line');
    answerLine.appendChild(ui.create('span', 'label', '标准答案：'));
    answerLine.appendChild(
      ui.create('span', 'answer-value', question.answer.join('、'))
    );
    answerBlock.appendChild(answerLine);

    const explanation = ui.create('div', 'explanation');
    explanation.appendChild(ui.create('strong', '', '解析：'));
    explanation.appendChild(document.createTextNode(question.explanation || '暂无解析。'));
    answerBlock.appendChild(explanation);
    card.appendChild(answerBlock);

    return card;
  }

  async function generateExam(event) {
    event.preventDefault();
    if (state.generating) return;
    clearError();

    if (!state.meta) {
      showError('题库信息尚未加载完成，请检查后端服务后刷新页面。');
      return;
    }
    const types = selectedTypes();
    if (!types.length) {
      showError('请至少选择一种题型后再生成试卷。');
      return;
    }
    if (!state.chapters.size) {
      showError('请至少选择一个章节后再生成试卷。');
      return;
    }

    const count = Number(els.countInput.value);
    const available = availableCount();
    if (!Number.isInteger(count) || count < 1) {
      showError('题目数量必须是大于 0 的整数。');
      els.countInput.focus();
      return;
    }
    if (count > 200) {
      showError('题目数量不能超过 200 题。');
      return;
    }
    if (count > available) {
      showError(
        '当前筛选条件下只有 ' + available + ' 道可用试题，无法生成 ' + count + ' 题试卷。请减少题量或放宽筛选。'
      );
      return;
    }

    const payload = {
      subject: state.subjectKey,
      question_count: count,
      question_types: types,
      chapters: Array.from(state.chapters),
      shuffle: els.shuffle.checked
    };

    state.generating = true;
    els.empty.hidden = true;
    els.result.hidden = true;
    els.loading.hidden = false;
    ui.setBusy(els.generateBtn, true, '正在组卷…');

    try {
      const exam = await api.generateExam(payload);
      renderExam(exam);
      ui.toast('试卷生成成功，共 ' + exam.question_count + ' 题。', 'success');
      if (window.innerWidth < 1080) {
        els.previewCard.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }
    } catch (error) {
      els.loading.hidden = true;
      if (state.exam) {
        els.result.hidden = false;
      } else {
        els.empty.hidden = false;
      }
      showError(error.message || '试卷生成失败，请稍后重试。');
      ui.toast(error.message || '试卷生成失败', 'error', 4800);
    } finally {
      state.generating = false;
      ui.setBusy(els.generateBtn, false);
      updateGenerateState();
    }
  }

  function fallbackFilename(includeAnswers) {
    if (!state.exam) return '驾考模拟试卷.md';
    const suffix = includeAnswers ? '' : '_空白卷';
    return (
      state.exam.subject.name +
      '_驾考模拟试卷' +
      suffix +
      '_' +
      state.exam.exam_id +
      '.md'
    );
  }

  async function downloadExam(includeAnswers, button) {
    if (!state.exam) {
      ui.toast('请先生成试卷。', 'error');
      return;
    }
    const originalText = button.textContent;
    ui.setBusy(button, true, '下载中…');
    try {
      const filename = await api.downloadExam(
        state.exam.exam_id,
        includeAnswers,
        fallbackFilename(includeAnswers)
      );
      ui.toast('已开始下载：' + filename, 'success');
    } catch (error) {
      ui.toast(error.message || '下载失败，请稍后重试。', 'error', 5000);
      if (error.code === 4040) {
        showError('试卷已过期，请重新生成后再下载。');
      }
    } finally {
      ui.setBusy(button, false);
      button.textContent = originalText;
    }
  }

  async function copyMarkdown() {
    const text = els.markdownCode.textContent || '';
    if (!text) {
      ui.toast('暂无可复制的 Markdown 内容。', 'error');
      return;
    }
    try {
      if (navigator.clipboard && window.isSecureContext) {
        await navigator.clipboard.writeText(text);
      } else {
        const textarea = ui.create('textarea');
        textarea.value = text;
        textarea.style.position = 'fixed';
        textarea.style.opacity = '0';
        document.body.appendChild(textarea);
        textarea.select();
        document.execCommand('copy');
        textarea.remove();
      }
      ui.toast('Markdown 源码已复制到剪贴板。', 'success');
    } catch (error) {
      ui.toast('复制失败，请手动选择源码复制。', 'error');
    }
  }

  function toggleMarkdown(force) {
    if (!state.exam) return;
    const shouldShow =
      typeof force === 'boolean' ? force : els.markdownSource.hidden;
    els.markdownSource.hidden = !shouldShow;
    els.markdownToggle.textContent = shouldShow ? '收起 MD 源码' : '查看 MD 源码';
    if (shouldShow) {
      els.markdownSource.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  function bindEvents() {
    els.form.addEventListener('submit', generateExam);

    els.countInput.addEventListener('input', function () {
      state.count = Number(els.countInput.value);
      renderQuickCounts();
      updateCountHint();
      updateGenerateState();
      clearError();
    });
    els.countInput.addEventListener('blur', function () {
      let value = Number(els.countInput.value);
      const available = availableCount();
      if (!Number.isFinite(value) || value < 1) value = 1;
      if (available > 0 && value > available) value = available;
      els.countInput.value = String(value);
      state.count = value;
      renderQuickCounts();
      updateCountHint();
      updateGenerateState();
    });

    els.selectAll.addEventListener('click', function () {
      const subject = getSubject();
      if (!subject) return;
      state.chapters = new Set(
        subject.chapters.map(function (chapter) {
          return chapter.name;
        })
      );
      renderChapters();
      onFiltersChanged();
      clearError();
    });

    els.clearChapters.addEventListener('click', function () {
      state.chapters.clear();
      renderChapters();
      onFiltersChanged();
      clearError();
    });

    els.downloadBtn.addEventListener('click', function () {
      downloadExam(true, els.downloadBtn);
    });
    els.blankBtn.addEventListener('click', function () {
      downloadExam(false, els.blankBtn);
    });
    els.markdownToggle.addEventListener('click', function () {
      toggleMarkdown();
    });
    els.closeMarkdown.addEventListener('click', function () {
      toggleMarkdown(false);
    });
    els.copyMarkdown.addEventListener('click', copyMarkdown);
  }

  async function init() {
    if (state.initialized) return;
    state.initialized = true;
    cacheElements();
    bindEvents();

    try {
      const meta = await api.getExamMeta();
      state.meta = meta;
      if (els.bankTotal) els.bankTotal.textContent = String(meta.total_questions);
      const subject = getSubject() || meta.subjects[0];
      state.subjectKey = subject.key;
      state.types = new Set(
        subject.supported_types.map(function (item) {
          return item.key;
        })
      );
      state.chapters = new Set(
        subject.chapters.map(function (item) {
          return item.name;
        })
      );
      state.count = Math.min(20, subject.total);
      els.countInput.value = String(state.count);
      els.countInput.max = String(subject.total);

      renderSubjects();
      renderTypes();
      renderChapters();
      renderQuickCounts();
      updateCountHint();
      updateGenerateState();
    } catch (error) {
      ui.clear(els.subjectOptions);
      ui.clear(els.typeOptions);
      ui.clear(els.chapterOptions);
      els.subjectOptions.appendChild(
        ui.create('p', 'form-error', '题库信息加载失败：' + (error.message || '未知错误'))
      );
      els.typeOptions.appendChild(ui.create('p', 'loading-text', '—'));
      els.chapterOptions.appendChild(ui.create('p', 'loading-text', '—'));
      els.generateBtn.disabled = true;
      showError('无法加载题库信息，请确认后端服务与 API-KEY 配置正确。');
      ui.toast('题库信息加载失败', 'error', 5000);
    }
  }

  DKA.exam = { init: init };
})(window);
