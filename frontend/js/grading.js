/**
 * 功能三：上传自定义题库 -> 在线作答 -> 自动阅卷 -> 错题 MD 导出
 */
(function (window) {
  'use strict';

  const DKA = window.DKA;
  const api = DKA.api;
  const ui = DKA.ui;

  const MAX_FILE_BYTES = 2 * 1024 * 1024;
  const ALLOWED_EXTENSIONS = ['.txt', '.md', '.markdown'];
  const TYPE_ORDER = ['single', 'judge', 'multiple'];

  const state = {
    initialized: false,
    file: null,
    paper: null,
    answers: new Map(),
    result: null,
    startedAt: 0,
    uploading: false,
    submitting: false,
    allDetailsRendered: false
  };

  let els = {};
  let reportExpanded = false;

  function cacheElements() {
    els = {
      uploadView: ui.$('#gradingUploadView'),
      dropZone: ui.$('#dropZone'),
      fileInput: ui.$('#fileInput'),
      pendingFile: ui.$('#pendingFile'),
      uploadBtn: ui.$('#uploadBtn'),
      resetUploadBtn: ui.$('#resetUploadBtn'),
      uploadError: ui.$('#uploadError'),
      uploadProgress: ui.$('#uploadProgress'),

      paperView: ui.$('#gradingPaperView'),
      paperTitle: ui.$('#paperTitle'),
      paperMeta: ui.$('#paperMeta'),
      paperQuestions: ui.$('#paperQuestions'),
      newPaperBtn: ui.$('#newPaperBtn'),
      progressText: ui.$('#answerProgressText'),
      progressBar: ui.$('#answerProgressBar'),
      totalCount: ui.$('#paperTotalCount'),
      answeredCount: ui.$('#paperAnsweredCount'),
      unansweredCount: ui.$('#paperUnansweredCount'),
      submitPaperBtn: ui.$('#submitPaperBtn'),
      clearAnswersBtn: ui.$('#clearAnswersBtn'),
      parseReport: ui.$('#parseReport'),
      toggleReportBtn: ui.$('#toggleReportBtn'),
      reportCount: ui.$('#reportCount'),
      parseReportBody: ui.$('#parseReportBody'),

      resultView: ui.$('#gradingResultView'),
      scoreRing: ui.$('#scoreRing'),
      resultScore: ui.$('#resultScore'),
      gradeBadge: ui.$('#resultGradeBadge'),
      resultSummary: ui.$('#resultSummary'),
      accuracy: ui.$('#resultAccuracy'),
      correct: ui.$('#resultCorrect'),
      wrong: ui.$('#resultWrong'),
      duration: ui.$('#resultDuration'),
      downloadWrongBtn: ui.$('#downloadWrongBtn'),
      retryPaperBtn: ui.$('#retryPaperBtn'),
      newUploadBtn: ui.$('#newUploadBtn'),
      wrongCountBadge: ui.$('#wrongCountBadge'),
      wrongList: ui.$('#wrongList'),
      toggleAllDetails: ui.$('#toggleAllDetails'),
      allDetails: ui.$('#allDetails')
    };
  }

  /* ============================ 上传 ============================ */

  function showUploadError(message) {
    els.uploadError.textContent = message;
    els.uploadError.hidden = false;
  }

  function clearUploadError() {
    els.uploadError.textContent = '';
    els.uploadError.hidden = true;
  }

  function validateFile(file) {
    if (!file) return '请选择要上传的题库文件。';
    const name = String(file.name || '').toLowerCase();
    const dot = name.lastIndexOf('.');
    const ext = dot >= 0 ? name.slice(dot) : '';
    if (ALLOWED_EXTENSIONS.indexOf(ext) === -1) {
      return '仅支持 .txt / .md 格式的题库文件，当前文件：' + file.name;
    }
    if (!file.size) return '文件为空，请检查后重新选择。';
    if (file.size > MAX_FILE_BYTES) {
      return '文件大小超过 2 MB，请精简题库后重新上传。';
    }
    return '';
  }

  function renderPendingFile() {
    if (!state.file) {
      els.pendingFile.hidden = true;
      els.pendingFile.textContent = '';
      els.uploadBtn.disabled = true;
      els.resetUploadBtn.disabled = true;
      return;
    }
    els.pendingFile.textContent =
      '已选择：' + state.file.name + ' · ' + ui.formatBytes(state.file.size);
    els.pendingFile.hidden = false;
    els.uploadBtn.disabled = false;
    els.resetUploadBtn.disabled = false;
  }

  function selectFile(file) {
    clearUploadError();
    const error = validateFile(file);
    if (error) {
      state.file = null;
      els.fileInput.value = '';
      renderPendingFile();
      showUploadError(error);
      ui.toast(error, 'error', 4000);
      return;
    }
    state.file = file;
    els.fileInput.value = '';
    renderPendingFile();
    ui.toast('已选择文件，点击「上传并解析」开始。', 'success', 2200);
  }

  function resetFileSelection() {
    state.file = null;
    els.fileInput.value = '';
    renderPendingFile();
    clearUploadError();
    els.uploadProgress.hidden = true;
  }

  async function uploadPaper() {
    if (!state.file || state.uploading) return;
    clearUploadError();
    state.uploading = true;
    els.uploadProgress.hidden = false;
    els.uploadBtn.disabled = true;
    els.resetUploadBtn.disabled = true;
    ui.setBusy(els.uploadBtn, true, '解析中…');

    try {
      const paper = await api.uploadQuestions(state.file);
      state.paper = paper;
      state.answers.clear();
      state.result = null;
      state.startedAt = Date.now();
      renderPaper(paper);
      showPaperView();
      ui.toast(
        '题库解析成功：共 ' + paper.question_count + ' 题。',
        'success'
      );
    } catch (error) {
      showUploadError(error.message || '题库解析失败，请检查格式后重试。');
      ui.toast(error.message || '题库解析失败', 'error', 5200);
    } finally {
      state.uploading = false;
      els.uploadProgress.hidden = true;
      ui.setBusy(els.uploadBtn, false);
      renderPendingFile();
      renderReport(state.paper ? state.paper.parse_report : null);
    }
  }

  /* ============================ 视图切换 ============================ */

  function showUploadView() {
    els.uploadView.hidden = false;
    els.paperView.hidden = true;
    els.resultView.hidden = true;
    resetFileSelection();
    state.paper = null;
    state.answers.clear();
    state.result = null;
    state.startedAt = 0;
    ui.scrollToTop();
  }

  function showPaperView() {
    els.uploadView.hidden = true;
    els.resultView.hidden = true;
    els.paperView.hidden = false;
    ui.scrollToTop();
  }

  function showResultView() {
    els.uploadView.hidden = true;
    els.paperView.hidden = true;
    els.resultView.hidden = false;
    ui.scrollToTop();
  }

  function confirmLeavePaper() {
    if (!state.paper || state.result) return true;
    const answered = state.answers.size;
    if (!answered) return true;
    return window.confirm('当前作答尚未提交，离开后答案将丢失。确定继续吗？');
  }

  /* ============================ 作答 ============================ */

  function buildPaperMeta(paper) {
    ui.clear(els.paperMeta);
    const typeText = TYPE_ORDER.filter(function (type) {
      return paper.type_counts && paper.type_counts[type];
    })
      .map(function (type) {
        return ui.normalizeTypeName(type) + ' ' + paper.type_counts[type];
      })
      .join(' · ');

    const chips = [
      ['文件', paper.filename],
      ['题量', paper.question_count + ' 题'],
      ['题型', typeText || '—'],
      ['满分', paper.total_score + ' 分'],
      ['及格', paper.pass_score + ' 分'],
      ['章节', (paper.chapters || []).join('、') || '未分类']
    ];
    chips.forEach(function (pair) {
      const chip = ui.create('span', 'chip');
      chip.appendChild(ui.create('strong', '', pair[0] + '：'));
      chip.appendChild(ui.create('span', '', pair[1]));
      els.paperMeta.appendChild(chip);
    });
  }

  function renderPaper(paper) {
    if (!paper) return;
    els.paperTitle.textContent = paper.title || paper.filename || '自定义题库';
    buildPaperMeta(paper);

    ui.clear(els.paperQuestions);
    paper.questions.forEach(function (question) {
      els.paperQuestions.appendChild(buildPaperQuestion(question));
    });

    renderReport(paper.parse_report);
    updateProgress();
    els.allDetails.hidden = true;
    state.allDetailsRendered = false;
    els.toggleAllDetails.textContent = '查看全部题目详情';
    els.toggleAllDetails.setAttribute('aria-expanded', 'false');
  }

  function buildPaperQuestion(question) {
    const article = ui.create('article', 'paper-question');
    article.dataset.qid = question.id;

    const head = ui.create('div', 'paper-q-head');
    head.appendChild(ui.create('span', 'q-index', '第 ' + question.number + ' 题'));
    head.appendChild(
      ui.create('span', 'q-type ' + ui.typeClass(question.type), question.type_name)
    );
    head.appendChild(ui.create('span', 'q-chapter', question.chapter));
    if (question.type === 'multiple') {
      head.appendChild(ui.create('span', 'q-chapter', '可多选'));
    }
    article.appendChild(head);
    article.appendChild(ui.create('p', 'paper-q-stem', question.stem));

    const optionsWrap = ui.create('div', 'answer-options');
    const isMultiple = question.type === 'multiple';
    const inputType = isMultiple ? 'checkbox' : 'radio';

    question.options.forEach(function (option) {
      const label = ui.create(
        'label',
        'answer-option' + (isMultiple ? ' is-checkbox' : '')
      );
      label.dataset.key = option.key;

      const input = ui.create('input');
      input.type = inputType;
      input.name = 'q_' + question.id;
      input.value = option.key;
      input.addEventListener('change', function () {
        const current = state.answers.get(question.id) || [];
        if (isMultiple) {
          const index = current.indexOf(option.key);
          if (input.checked && index === -1) current.push(option.key);
          if (!input.checked && index !== -1) current.splice(index, 1);
        } else {
          current.length = 0;
          current.push(option.key);
        }
        const sorted = current.slice().sort();
        if (sorted.length) state.answers.set(question.id, sorted);
        else state.answers.delete(question.id);

        const labels = optionsWrap.querySelectorAll('.answer-option');
        Array.prototype.forEach.call(labels, function (node) {
          node.classList.toggle(
            'is-selected',
            (state.answers.get(question.id) || []).indexOf(node.dataset.key) !== -1
          );
        });
        updateProgress();
      });

      label.appendChild(input);
      label.appendChild(ui.create('span', 'option-key', option.key));
      label.appendChild(ui.create('span', 'option-text', option.text));
      optionsWrap.appendChild(label);
    });

    article.appendChild(optionsWrap);
    return article;
  }

  function updateProgress() {
    const total = state.paper ? state.paper.question_count : 0;
    const answered = state.answers.size;
    const remaining = Math.max(total - answered, 0);
    const percent = total ? Math.round((answered / total) * 100) : 0;

    if (els.progressText) els.progressText.textContent = answered + ' / ' + total;
    if (els.progressBar) els.progressBar.style.width = percent + '%';
    if (els.totalCount) els.totalCount.textContent = String(total);
    if (els.answeredCount) els.answeredCount.textContent = String(answered);
    if (els.unansweredCount) els.unansweredCount.textContent = String(remaining);
    if (els.submitPaperBtn) els.submitPaperBtn.disabled = total === 0;

    const hint = els.submitPaperBtn && els.submitPaperBtn.parentNode
      ? els.submitPaperBtn.parentNode.querySelector('.field-hint')
      : null;
    if (hint) {
      hint.textContent = remaining
        ? '还有 ' + remaining + ' 题未作答；满分 100 分，90 分及格。'
        : '已全部作答，可以提交阅卷；满分 100 分，90 分及格。';
      hint.classList.toggle('is-warning', remaining > 0);
    }
  }

  function clearAnswers() {
    if (!state.paper) return;
    if (state.answers.size && !window.confirm('确定清空当前所有作答吗？')) return;
    state.answers.clear();
    renderPaper(state.paper);
    ui.scrollToTop();
    ui.toast('已清空作答。', 'success', 2000);
  }

  async function submitPaper() {
    if (!state.paper || state.submitting) return;
    const total = state.paper.question_count;
    const unanswered = total - state.answers.size;
    if (
      unanswered > 0 &&
      !window.confirm('还有 ' + unanswered + ' 题未作答，未作答题目将计 0 分。确定提交阅卷吗？')
    ) {
      return;
    }

    const answers = state.paper.questions.map(function (question) {
      return {
        question_id: question.id,
        answer: state.answers.get(question.id) || []
      };
    });
    const duration = state.startedAt
      ? Math.max(0, Math.round((Date.now() - state.startedAt) / 1000))
      : null;

    state.submitting = true;
    ui.setBusy(els.submitPaperBtn, true, '正在阅卷…');
    try {
      const result = await api.submitGrading({
        paper_id: state.paper.paper_id,
        answers: answers,
        duration_seconds: duration
      });
      state.result = result;
      renderResult(result);
      showResultView();
      ui.toast(
        '阅卷完成：' + ui.formatScore(result.score) + ' 分 · ' + result.grade,
        result.passed ? 'success' : 'error',
        4500
      );
    } catch (error) {
      ui.toast(error.message || '阅卷失败，请稍后重试。', 'error', 5200);
      if (error.code === 4041 || error.status === 404) {
        if (window.confirm('题库已过期或不存在，需要重新上传题库。是否现在重新上传？')) {
          showUploadView();
        }
      }
    } finally {
      state.submitting = false;
      ui.setBusy(els.submitPaperBtn, false);
    }
  }

  /* ============================ 解析报告 ============================ */

  function renderReport(report) {
    if (!report || (!report.errors.length && !report.warnings.length)) {
      els.parseReport.hidden = true;
      return;
    }
    const errors = report.errors || [];
    const warnings = report.warnings || [];
    const total = errors.length + warnings.length;

    els.parseReport.hidden = false;
    els.reportCount.textContent = '（' + total + ' 条）';
    ui.clear(els.parseReportBody);

    const list = ui.create('ul');
    errors.forEach(function (error) {
      const item = ui.create(
        'li',
        'is-error',
        '第 ' + (error.source_number || '?') + ' 题（第 ' + (error.line || '?') + ' 行）：' + error.reason
      );
      list.appendChild(item);
    });
    warnings.forEach(function (warning) {
      list.appendChild(ui.create('li', '', warning));
    });
    els.parseReportBody.appendChild(list);

    reportExpanded = errors.length > 0;
    els.parseReportBody.hidden = !reportExpanded;
    els.toggleReportBtn.setAttribute('aria-expanded', String(reportExpanded));
  }

  /* ============================ 阅卷结果 ============================ */

  function buildReviewOptions(question) {
    const container = ui.create('div', 'review-options');
    const correct = question.correct_answer || [];
    const user = question.user_answer || [];

    (question.options || []).forEach(function (option) {
      const isCorrect = correct.indexOf(option.key) !== -1;
      const isUser = user.indexOf(option.key) !== -1;
      const row = ui.create(
        'div',
        'review-option' +
          (isCorrect ? ' is-correct-option' : '') +
          (isUser ? ' is-user-option' : '')
      );
      row.appendChild(ui.create('span', 'option-key', option.key));
      row.appendChild(ui.create('span', 'option-text', option.text));

      const marks = [];
      if (isCorrect) marks.push('正确答案');
      if (isUser) marks.push('你的选择');
      if (marks.length) {
        row.appendChild(ui.create('span', 'option-mark', marks.join(' / ')));
      }
      container.appendChild(row);
    });
    return container;
  }

  function buildAnswerCompare(question) {
    const compare = ui.create('div', 'answer-compare');
    const userBox = ui.create('div', 'compare-box is-user');
    userBox.appendChild(ui.create('strong', '', '你的答案：'));
    userBox.appendChild(document.createTextNode(question.user_answer_text || '未作答'));
    compare.appendChild(userBox);

    const correctBox = ui.create('div', 'compare-box is-correct');
    correctBox.appendChild(ui.create('strong', '', '正确答案：'));
    correctBox.appendChild(
      document.createTextNode(question.correct_answer_text || question.correct_answer.join('、'))
    );
    compare.appendChild(correctBox);
    return compare;
  }

  function buildWrongItem(question, index) {
    const item = ui.create('div', 'wrong-item');
    const head = ui.create('div', 'wrong-item-head');
    head.appendChild(
      ui.create(
        'span',
        'wrong-number',
        '错题 ' + (index + 1) + ' · 原题第 ' + question.number + ' 题'
      )
    );
    head.appendChild(
      ui.create('span', 'q-type ' + ui.typeClass(question.type), question.type_name)
    );
    head.appendChild(ui.create('span', 'q-chapter', question.chapter));
    item.appendChild(head);

    item.appendChild(ui.create('p', 'wrong-stem', question.stem));
    item.appendChild(buildReviewOptions(question));
    item.appendChild(buildAnswerCompare(question));

    const explanation = ui.create('div', 'wrong-explanation');
    explanation.appendChild(ui.create('strong', '', '解析：'));
    explanation.appendChild(
      document.createTextNode(question.explanation || '暂无解析，建议回看对应章节。')
    );
    item.appendChild(explanation);
    return item;
  }

  function buildAllDetail(question) {
    const item = ui.create('div', 'all-detail');
    const head = ui.create('div', 'all-detail-head');
    head.appendChild(
      ui.create(
        'span',
        'result-icon ' + (question.is_correct ? 'is-correct' : 'is-wrong'),
        question.is_correct ? '✓' : '✕'
      )
    );
    head.appendChild(
      ui.create('span', 'q-index', '第 ' + question.number + ' 题')
    );
    head.appendChild(
      ui.create('span', 'q-type ' + ui.typeClass(question.type), question.type_name)
    );
    head.appendChild(ui.create('span', 'q-chapter', question.chapter));
    item.appendChild(head);

    item.appendChild(ui.create('p', 'paper-q-stem', question.stem));
    item.appendChild(buildReviewOptions(question));
    item.appendChild(buildAnswerCompare(question));

    const explanation = ui.create('div', 'wrong-explanation');
    explanation.appendChild(ui.create('strong', '', '解析：'));
    explanation.appendChild(
      document.createTextNode(question.explanation || '暂无解析。')
    );
    item.appendChild(explanation);
    return item;
  }

  function renderResult(result) {
    const score = Number(result.score) || 0;
    els.resultScore.textContent = ui.formatScore(score);
    els.scoreRing.style.setProperty('--score', String(score));
    els.scoreRing.classList.toggle('is-failed', !result.passed);

    els.gradeBadge.className = 'grade-badge';
    if (score >= 95) els.gradeBadge.classList.add('is-excellent');
    else if (result.passed) els.gradeBadge.classList.add('is-pass');
    else els.gradeBadge.classList.add('is-fail');
    els.gradeBadge.textContent = result.grade;

    els.resultSummary.textContent =
      '共 ' + result.total_questions + ' 题，答对 ' + result.correct_count +
      ' 题，答错 ' + result.wrong_count + ' 题' +
      (result.unanswered_count ? '，未作答 ' + result.unanswered_count + ' 题' : '') +
      '。' +
      (result.passed
        ? '成绩达到 ' + result.pass_score + ' 分合格线。'
        : '成绩未达到 ' + result.pass_score + ' 分合格线，继续加油。');

    els.accuracy.textContent = result.accuracy + '%';
    els.correct.textContent = result.correct_count + ' 题';
    els.wrong.textContent = result.wrong_count + ' 题';
    els.duration.textContent = result.duration_text || '未记录';
    els.wrongCountBadge.textContent = String(result.wrong_count);

    ui.clear(els.wrongList);
    if (!result.wrong_questions.length) {
      const empty = ui.create('div', 'empty-correct');
      const icon = ui.create('div', 'empty-icon');
      icon.innerHTML =
        '<svg viewBox="0 0 48 48" aria-hidden="true"><path d="M14 25l7 7 14-16"/></svg>';
      empty.appendChild(icon);
      empty.appendChild(ui.create('h3', '', '本次作答全部正确'));
      empty.appendChild(
        ui.create('p', '', '没有错题，继续保持！可重新作答巩固知识点。')
      );
      els.wrongList.appendChild(empty);
      els.downloadWrongBtn.disabled = true;
      els.downloadWrongBtn.title = '本次没有错题，无需导出';
    } else {
      result.wrong_questions.forEach(function (question, index) {
        els.wrongList.appendChild(buildWrongItem(question, index));
      });
      els.downloadWrongBtn.disabled = false;
      els.downloadWrongBtn.title = '';
    }

    els.allDetails.hidden = true;
    ui.clear(els.allDetails);
    state.allDetailsRendered = false;
    els.toggleAllDetails.textContent = '查看全部题目详情';
    els.toggleAllDetails.setAttribute('aria-expanded', 'false');
  }

  function toggleAllDetails() {
    if (!state.result) return;
    if (!state.allDetailsRendered) {
      ui.clear(els.allDetails);
      state.result.details.forEach(function (question) {
        els.allDetails.appendChild(buildAllDetail(question));
      });
      state.allDetailsRendered = true;
    }
    const shouldOpen = els.allDetails.hidden;
    els.allDetails.hidden = !shouldOpen;
    els.toggleAllDetails.setAttribute('aria-expanded', String(shouldOpen));
    els.toggleAllDetails.textContent = shouldOpen ? '收起全部题目详情' : '查看全部题目详情';
    if (shouldOpen) {
      els.allDetails.scrollIntoView({ behavior: 'smooth', block: 'nearest' });
    }
  }

  async function downloadWrongAnswers() {
    if (!state.result) {
      ui.toast('请先完成阅卷。', 'error');
      return;
    }
    if (!state.result.wrong_count) {
      ui.toast('本次没有错题，无需导出。', 'success');
      return;
    }
    const fallback =
      '错题集_' +
      (state.paper ? state.paper.title : '题库') +
      '_' +
      state.result.result_id +
      '.md';
    ui.setBusy(els.downloadWrongBtn, true, '正在导出…');
    try {
      const filename = await api.downloadWrongAnswers(
        state.result.result_id,
        fallback
      );
      ui.toast('已开始下载：' + filename, 'success');
    } catch (error) {
      ui.toast(error.message || '错题导出失败，请稍后重试。', 'error', 5000);
    } finally {
      ui.setBusy(els.downloadWrongBtn, false);
      els.downloadWrongBtn.disabled = !state.result || !state.result.wrong_count;
    }
  }

  function retryPaper() {
    if (!state.paper) {
      ui.toast('题库已失效，请重新上传。', 'error');
      return;
    }
    state.answers.clear();
    state.result = null;
    state.startedAt = Date.now();
    renderPaper(state.paper);
    showPaperView();
    ui.toast('已重置作答，可以重新开始。', 'success', 2200);
  }

  function newUpload() {
    if (!confirmLeavePaper()) return;
    showUploadView();
  }

  /* ============================ 事件绑定 ============================ */

  function bindEvents() {
    els.dropZone.addEventListener('click', function (event) {
      if (event.target === els.fileInput) return;
      if (!state.uploading) els.fileInput.click();
    });
    els.dropZone.addEventListener('keydown', function (event) {
      if (event.key === 'Enter' || event.key === ' ') {
        event.preventDefault();
        if (!state.uploading) els.fileInput.click();
      }
    });
    els.fileInput.addEventListener('change', function () {
      if (els.fileInput.files && els.fileInput.files[0]) {
        selectFile(els.fileInput.files[0]);
      }
    });

    ['dragenter', 'dragover'].forEach(function (type) {
      els.dropZone.addEventListener(type, function (event) {
        event.preventDefault();
        event.stopPropagation();
        if (event.dataTransfer) event.dataTransfer.dropEffect = 'copy';
        els.dropZone.classList.add('is-dragover');
      });
    });
    ['dragleave', 'dragend'].forEach(function (type) {
      els.dropZone.addEventListener(type, function (event) {
        event.preventDefault();
        event.stopPropagation();
        els.dropZone.classList.remove('is-dragover');
      });
    });
    els.dropZone.addEventListener('drop', function (event) {
      event.preventDefault();
      event.stopPropagation();
      els.dropZone.classList.remove('is-dragover');
      if (state.uploading) return;
      if (event.dataTransfer && event.dataTransfer.files && event.dataTransfer.files[0]) {
        selectFile(event.dataTransfer.files[0]);
      }
    });

    window.addEventListener('dragover', function (event) {
      event.preventDefault();
    });
    window.addEventListener('drop', function (event) {
      event.preventDefault();
    });

    els.uploadBtn.addEventListener('click', uploadPaper);
    els.resetUploadBtn.addEventListener('click', resetFileSelection);
    els.newPaperBtn.addEventListener('click', function () {
      if (confirmLeavePaper()) showUploadView();
    });
    els.clearAnswersBtn.addEventListener('click', clearAnswers);
    els.submitPaperBtn.addEventListener('click', submitPaper);
    els.toggleReportBtn.addEventListener('click', function () {
      reportExpanded = !reportExpanded;
      els.parseReportBody.hidden = !reportExpanded;
      els.toggleReportBtn.setAttribute('aria-expanded', String(reportExpanded));
    });

    els.downloadWrongBtn.addEventListener('click', downloadWrongAnswers);
    els.retryPaperBtn.addEventListener('click', function () {
      if (state.result) {
        if (!window.confirm('重新作答将清空本次答案，但保留当前题库。确定继续吗？')) return;
      }
      retryPaper();
    });
    els.newUploadBtn.addEventListener('click', newUpload);
    els.toggleAllDetails.addEventListener('click', toggleAllDetails);
  }

  function init() {
    if (state.initialized) return;
    state.initialized = true;
    cacheElements();
    bindEvents();
    renderPendingFile();
    els.uploadView.hidden = false;
    els.paperView.hidden = true;
    els.resultView.hidden = true;
  }

  DKA.grading = { init: init };
})(window);
