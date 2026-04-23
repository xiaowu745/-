/**
 * 荆工智匠 - 前端应用逻辑
 */

const API_BASE = window.location.hostname === "localhost"
  ? "http://localhost:8000/api"
  : "/api";

// ============ 全局状态 ============

const state = {
  // 学生信息
  profile: {
    nickname: "",
    major: "",
    grade: "",
    school_tier: "普通本科",
  },
  // 测评
  sessionId: "",
  questions: [],
  currentQuestionIndex: 0,
  answers: [],
  quickResult: null,
  // 对话
  freeChatSessionId: "",
  interviewSessionId: "",
  selectedPosition: "",
  selectedInterviewType: "technical",
};

// ============ 页面导航 ============

function showPage(pageId) {
  document.querySelectorAll(".page").forEach((p) => p.classList.remove("active"));
  document.getElementById(pageId).classList.add("active");
  window.scrollTo(0, 0);
}

// ============ 选择器交互 ============

document.querySelectorAll(".select-grid").forEach((grid) => {
  grid.addEventListener("click", (e) => {
    const item = e.target.closest(".select-item");
    if (!item) return;

    // 单选模式
    grid.querySelectorAll(".select-item").forEach((i) => i.classList.remove("selected"));
    item.classList.add("selected");
  });
});

// ============ 测评流程 ============

function startAssessment() {
  showPage("page-profile");
}

function submitProfile() {
  const nickname = document.getElementById("input-nickname").value.trim();
  const majorEl = document.querySelector("#major-select .selected");
  const gradeEl = document.querySelector("#grade-select .selected");
  const schoolEl = document.querySelector("#school-select .selected");

  if (!nickname) return alert("请输入昵称");
  if (!majorEl) return alert("请选择专业");
  if (!gradeEl) return alert("请选择年级");

  state.profile.nickname = nickname;
  state.profile.major = majorEl.dataset.value;
  state.profile.grade = gradeEl.dataset.value;
  state.profile.school_tier = schoolEl ? schoolEl.dataset.value : "普通本科";

  loadQuestions();
}

async function loadQuestions() {
  showPage("page-quiz");

  try {
    const res = await fetch(`${API_BASE}/assessment/questions/${state.profile.major}`);
    const data = await res.json();

    // 合并所有题目
    state.questions = [
      ...(data.common_questions || []),
      ...(data.major_questions || []),
    ];
    state.currentQuestionIndex = 0;
    state.answers = [];

    renderQuestion();
  } catch (err) {
    // API不可用时使用内置题库
    loadBuiltinQuestions();
  }
}

function loadBuiltinQuestions() {
  // 内置精简题库（API不可用时的兜底）
  const dims = ["theory", "programming", "hardware", "tools", "project", "soft_skill"];
  const dimNames = {
    theory: "理论基础", programming: "编程能力", hardware: "硬件实操",
    tools: "工具掌握", project: "项目经验", soft_skill: "职业素养"
  };

  state.questions = [
    { id: "B01", dimension: "theory", question: "关于你的专业核心课程，以下哪个最符合你？", options: [
      { text: "很多课只是及格水平，核心概念记不太清", score: 1 },
      { text: "大部分课能拿70-80分，基本概念都了解", score: 2 },
      { text: "核心课85分以上，能深入理解和应用", score: 3 },
      { text: "专业课名列前茅，能给同学讲解原理", score: 4 }
    ]},
    { id: "B02", dimension: "theory", question: "关于计算机网络/电路基础，以下哪个最符合你？", options: [
      { text: "学过但基本还给老师了", score: 1 },
      { text: "能说清基本概念和原理", score: 2 },
      { text: "能分析中等复杂度的问题", score: 3 },
      { text: "能独立设计方案或解决实际问题", score: 4 }
    ]},
    { id: "B03", dimension: "programming", question: "关于编程能力（C/Python/Java等），以下哪个最符合你？", options: [
      { text: "学过语法但写代码经常报错", score: 1 },
      { text: "能独立完成课程实验，但超过300行就吃力", score: 2 },
      { text: "做过1-2个完整小项目，能熟练调试", score: 3 },
      { text: "参加过编程竞赛/写过开源项目/有实习开发经验", score: 4 }
    ]},
    { id: "B04", dimension: "programming", question: "关于Python编程，以下哪个最符合你？", options: [
      { text: "没学过/刚开始学", score: 1 },
      { text: "能写简单脚本，用过几个常用库", score: 2 },
      { text: "做过完整项目（爬虫/数据分析/Web等）", score: 3 },
      { text: "熟练使用多个框架，能写自动化工具", score: 4 }
    ]},
    { id: "B05", dimension: "hardware", question: "关于动手实操能力，以下哪个最符合你？", options: [
      { text: "基本没怎么动过手，实验课跟着做完就忘", score: 1 },
      { text: "能按照教程完成实验，脱离教程就不太行", score: 2 },
      { text: "能独立完成实训项目，会使用常用仪器", score: 3 },
      { text: "自己做过完整的硬件/网络/系统项目", score: 4 }
    ]},
    { id: "B06", dimension: "hardware", question: "关于专业设备操作（网络设备/PLC/示波器/机床等），以下哪个最符合你？", options: [
      { text: "基本没碰过真设备", score: 1 },
      { text: "在实验课上操作过，按指导书能完成", score: 2 },
      { text: "能独立操作和配置，做过调试", score: 3 },
      { text: "熟练操作，能处理故障和复杂任务", score: 4 }
    ]},
    { id: "B07", dimension: "tools", question: "关于Linux操作系统，以下哪个最符合你？", options: [
      { text: "没用过/只知道有这个东西", score: 1 },
      { text: "装过虚拟机，会基本命令(ls/cd/mkdir)", score: 2 },
      { text: "能在Linux下编译程序、配置服务", score: 3 },
      { text: "熟练使用Linux做开发/运维", score: 4 }
    ]},
    { id: "B08", dimension: "tools", question: "关于行业专用工具/软件，以下哪个最符合你？", options: [
      { text: "基本没用过专业工具", score: 1 },
      { text: "会用1-2个工具做基本操作", score: 2 },
      { text: "能熟练使用核心工具完成任务", score: 3 },
      { text: "精通工具链，能选择和组合不同工具", score: 4 }
    ]},
    { id: "B09", dimension: "project", question: "关于项目经验，以下哪个最符合你？", options: [
      { text: "只做过课程作业，没有独立项目", score: 1 },
      { text: "参加过课程设计或实训", score: 2 },
      { text: "独立完成过1-2个完整项目", score: 3 },
      { text: "做过3个以上项目/参加竞赛获奖/有实习经验", score: 4 }
    ]},
    { id: "B10", dimension: "project", question: "你的简历上项目经历情况？", options: [
      { text: "还没写过简历", score: 1 },
      { text: "有简历，但项目经历只有课程设计", score: 2 },
      { text: "简历上有1-2个拿得出手的项目", score: 3 },
      { text: "简历充实，有项目+实习+竞赛", score: 4 }
    ]},
    { id: "B11", dimension: "soft_skill", question: "关于团队协作和沟通，以下哪个最符合你？", options: [
      { text: "不太善于表达，团队合作中偏被动", score: 1 },
      { text: "能完成分配的任务，有基本沟通能力", score: 2 },
      { text: "能主动协调团队，清楚表达技术方案", score: 3 },
      { text: "有带队经验，能做技术汇报和方案讲解", score: 4 }
    ]},
    { id: "B12", dimension: "soft_skill", question: "关于技术文档写作，以下哪个最符合你？", options: [
      { text: "实验报告都写得很痛苦", score: 1 },
      { text: "能写出结构清楚的实验报告", score: 2 },
      { text: "能写技术方案文档", score: 3 },
      { text: "写过正式项目文档/技术博客/论文", score: 4 }
    ]},
  ];

  state.currentQuestionIndex = 0;
  state.answers = [];
  renderQuestion();
}

function renderQuestion() {
  const q = state.questions[state.currentQuestionIndex];
  if (!q) return;

  const total = state.questions.length;
  const current = state.currentQuestionIndex + 1;

  document.getElementById("quiz-progress").textContent = `${current}/${total}`;
  document.getElementById("quiz-progress-bar").style.width = `${(current / total) * 100}%`;

  const dimNames = {
    theory: "理论基础", programming: "编程能力", hardware: "硬件实操",
    tools: "工具掌握", project: "项目经验", soft_skill: "职业素养"
  };

  document.getElementById("question-dim").textContent = dimNames[q.dimension] || q.dimension;
  document.getElementById("question-text").textContent = q.question;

  const container = document.getElementById("options-container");
  container.innerHTML = q.options
    .map((opt, i) => `<div class="option-item" onclick="selectOption(${i})">${opt.text}</div>`)
    .join("");
}

function selectOption(index) {
  const q = state.questions[state.currentQuestionIndex];
  state.answers.push({ question_id: q.id, selected_option: index });

  // 标记选中动画
  const items = document.querySelectorAll(".option-item");
  items[index].classList.add("selected");

  // 延迟进入下一题
  setTimeout(() => {
    state.currentQuestionIndex++;
    if (state.currentQuestionIndex >= state.questions.length) {
      finishQuickAssessment();
    } else {
      renderQuestion();
    }
  }, 300);
}

async function finishQuickAssessment() {
  // 尝试调用API
  try {
    const res = await fetch(`${API_BASE}/assessment/quick`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ student: state.profile, answers: state.answers }),
    });

    if (res.ok) {
      const data = await res.json();
      state.sessionId = data.session_id;
      state.quickResult = data;
      showQuickResult(data);
      return;
    }
  } catch (err) {
    console.log("API not available, calculating locally");
  }

  // 本地计算
  const localResult = calculateLocal();
  state.quickResult = localResult;
  showQuickResult(localResult);
}

function calculateLocal() {
  const dimScores = {};
  const dimCounts = {};
  const dimNames = {
    theory: "理论基础", programming: "编程能力", hardware: "硬件实操",
    tools: "工具掌握", project: "项目经验", soft_skill: "职业素养"
  };

  state.answers.forEach((ans) => {
    const q = state.questions.find((q) => q.id === ans.question_id);
    if (!q) return;
    const score = q.options[ans.selected_option].score;
    dimScores[q.dimension] = (dimScores[q.dimension] || 0) + score;
    dimCounts[q.dimension] = (dimCounts[q.dimension] || 0) + 1;
  });

  const dimensionScores = Object.entries(dimScores).map(([dim, total]) => {
    const avg = total / dimCounts[dim];
    const score = Math.round((avg / 4) * 100);
    return { dimension: dim, dimension_name: dimNames[dim], score, level: Math.ceil(score / 20) };
  });

  const overall = Math.round(dimensionScores.reduce((s, d) => s + d.score, 0) / dimensionScores.length);
  const weak = dimensionScores.sort((a, b) => a.score - b.score).slice(0, 2).map((d) => d.dimension_name);

  return { dimension_scores: dimensionScores, overall_score: overall, weak_dimensions: weak };
}

function showQuickResult(data) {
  showPage("page-quick-result");

  // 综合得分
  document.querySelector(".score-number").textContent = data.overall_score;

  // 分数条
  const barsContainer = document.getElementById("score-bars");
  const colors = ["#3b82f6", "#8b5cf6", "#10b981", "#f59e0b", "#ef4444", "#ec4899"];
  barsContainer.innerHTML = data.dimension_scores
    .sort((a, b) => {
      const order = ["theory", "programming", "hardware", "tools", "project", "soft_skill"];
      return order.indexOf(a.dimension) - order.indexOf(b.dimension);
    })
    .map((d, i) => `
      <div class="score-bar-item">
        <span class="bar-label">${d.dimension_name}</span>
        <div class="bar-track"><div class="bar-fill" style="width:${d.score}%;background:${colors[i % 6]}"></div></div>
        <span class="bar-score">${d.score}</span>
      </div>
    `).join("");

  // 雷达图
  drawRadarChart(data.dimension_scores);

  // 薄弱项提示
  document.getElementById("weak-hint").innerHTML =
    `⚠️ 你的薄弱项：<strong>${data.weak_dimensions.join("、")}</strong><br>建议进入AI深度评估，获取更精准的分析和个性化建议。`;
}

function drawRadarChart(scores) {
  const canvas = document.getElementById("radar-chart");
  const ctx = canvas.getContext("2d");
  const size = 300;
  const cx = size / 2, cy = size / 2, r = 100;

  canvas.width = size;
  canvas.height = size;
  ctx.clearRect(0, 0, size, size);

  const dims = ["theory", "programming", "hardware", "tools", "project", "soft_skill"];
  const labels = ["理论基础", "编程能力", "硬件实操", "工具掌握", "项目经验", "职业素养"];
  const n = dims.length;

  // 背景网格
  for (let level = 1; level <= 4; level++) {
    ctx.beginPath();
    for (let i = 0; i <= n; i++) {
      const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
      const lr = (r * level) / 4;
      const x = cx + lr * Math.cos(angle);
      const y = cy + lr * Math.sin(angle);
      i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
    }
    ctx.strokeStyle = "#e2e8f0";
    ctx.stroke();
  }

  // 轴线
  for (let i = 0; i < n; i++) {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    ctx.beginPath();
    ctx.moveTo(cx, cy);
    ctx.lineTo(cx + r * Math.cos(angle), cy + r * Math.sin(angle));
    ctx.strokeStyle = "#e2e8f0";
    ctx.stroke();
  }

  // 数据多边形
  const scoreMap = {};
  scores.forEach((s) => (scoreMap[s.dimension] = s.score));

  ctx.beginPath();
  dims.forEach((dim, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const val = (scoreMap[dim] || 0) / 100;
    const x = cx + r * val * Math.cos(angle);
    const y = cy + r * val * Math.sin(angle);
    i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y);
  });
  ctx.closePath();
  ctx.fillStyle = "rgba(37, 99, 235, 0.15)";
  ctx.fill();
  ctx.strokeStyle = "#2563eb";
  ctx.lineWidth = 2;
  ctx.stroke();

  // 数据点
  dims.forEach((dim, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const val = (scoreMap[dim] || 0) / 100;
    const x = cx + r * val * Math.cos(angle);
    const y = cy + r * val * Math.sin(angle);
    ctx.beginPath();
    ctx.arc(x, y, 4, 0, Math.PI * 2);
    ctx.fillStyle = "#2563eb";
    ctx.fill();
  });

  // 标签
  ctx.fillStyle = "#334155";
  ctx.font = "12px sans-serif";
  ctx.textAlign = "center";
  labels.forEach((label, i) => {
    const angle = (Math.PI * 2 * i) / n - Math.PI / 2;
    const x = cx + (r + 24) * Math.cos(angle);
    const y = cy + (r + 24) * Math.sin(angle);
    ctx.fillText(label, x, y + 4);
  });
}

// ============ 深度对话 ============

async function startDeepChat() {
  showPage("page-deep-chat");
  const container = document.getElementById("deep-chat-messages");
  container.innerHTML = "";

  if (!state.sessionId) {
    // 没有API session，用本地模式
    appendMessage(container, "bot",
      `好的，${state.profile.nickname}，我来根据你的自评结果做一些深入了解。\n\n` +
      `从结果来看，你的薄弱项是：${state.quickResult.weak_dimensions.join("、")}。\n\n` +
      `我想先了解一下——你平时在学校有去实训室或实验室练习的习惯吗？还是主要以上课和看书为主？`
    );
    return;
  }

  try {
    const res = await fetch(`${API_BASE}/assessment/deep/start/${state.sessionId}`, { method: "POST" });
    const data = await res.json();
    appendMessage(container, "bot", data.message);
  } catch {
    appendMessage(container, "bot", "AI助手暂时无法连接，请稍后再试。你也可以直接查看基础报告。");
  }
}

async function sendDeepChat() {
  const input = document.getElementById("deep-chat-input");
  const message = input.value.trim();
  if (!message) return;

  const container = document.getElementById("deep-chat-messages");
  appendMessage(container, "user", message);
  input.value = "";

  const btn = document.getElementById("btn-deep-send");
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/assessment/deep/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ session_id: state.sessionId, message }),
    });
    const data = await res.json();
    appendMessage(container, "bot", data.message);

    if (data.is_complete) {
      setTimeout(() => {
        appendMessage(container, "bot", "评估完成！点击下方按钮查看你的完整报告 👇");
        const reportBtn = document.createElement("button");
        reportBtn.className = "btn-primary";
        reportBtn.textContent = "查看测评报告 →";
        reportBtn.onclick = () => generateReport();
        reportBtn.style.margin = "8px 0";
        container.appendChild(reportBtn);
      }, 500);
    }
  } catch {
    appendMessage(container, "bot", "网络异常，请重试。");
  }

  btn.disabled = false;
}

function skipToReport() {
  generateReport();
}

async function generateReport() {
  showPage("page-report");
  const container = document.getElementById("report-content");
  container.innerHTML = '<div class="loading-spinner">报告生成中...</div>';

  if (state.sessionId) {
    try {
      const res = await fetch(`${API_BASE}/report/generate/${state.sessionId}`, { method: "POST" });
      const data = await res.json();
      container.innerHTML = formatReport(data.report);
      return;
    } catch {}
  }

  // 本地生成简易报告
  container.innerHTML = formatReport(generateLocalReport());
}

function generateLocalReport() {
  const r = state.quickResult;
  const sorted = [...r.dimension_scores].sort((a, b) => b.score - a.score);
  const best = sorted[0];
  const worst = sorted[sorted.length - 1];

  return `📊 技能测评报告
━━━━━━━━━━━━━━━━━━━━

👤 ${state.profile.nickname}
📚 专业：${getMajorName(state.profile.major)} · ${getGradeName(state.profile.grade)}
🏫 ${state.profile.school_tier}

📈 综合得分：${r.overall_score} / 100

━━━ 各维度分析 ━━━

${r.dimension_scores.map(d => `${d.dimension_name}：${d.score}分 ${"█".repeat(Math.round(d.score/10))}${"░".repeat(10-Math.round(d.score/10))}`).join("\n")}

━━━ 优势与短板 ━━━

✅ 最大优势：${best.dimension_name}（${best.score}分）
这是你当前最突出的能力，在求职中可以作为核心竞争力来展示。

⚠️ 最需提升：${worst.dimension_name}（${worst.score}分）
建议在这个方向投入更多时间，${worst.dimension === "project" ? "尽快启动一个完整项目" : worst.dimension === "hardware" ? "多去实训室动手练习" : worst.dimension === "tools" ? "学习行业主流工具" : "加强基础学习"}。

━━━ 建议下一步 ━━━

1. 确定一个主攻方向，不要什么都学
2. ${worst.dimension === "project" ? "本月内启动一个小项目，从头到尾做完" : "每周至少花5小时在" + worst.dimension_name + "上"}
3. 关注行业动态，了解目标岗位的真实要求
4. 考虑参加实训营或实习，获取实战经验

💡 想获取更详细的方向推荐和个性化学习路径，
请使用 AI 深度评估功能。`;
}

function formatReport(text) {
  return text
    .replace(/\n/g, "<br>")
    .replace(/(━+)/g, '<span style="color:#94a3b8">$1</span>')
    .replace(/(📊|👤|📚|🏫|📈|✅|⚠️|💡|🥇|🥈|🥉)/g, '<span style="font-size:1.2em">$1</span>');
}

// ============ 自由问答 ============

async function sendFreeChat() {
  const input = document.getElementById("free-chat-input");
  const message = input.value.trim();
  if (!message) return;

  const container = document.getElementById("free-chat-messages");
  appendMessage(container, "user", message);
  input.value = "";

  const btn = document.getElementById("btn-free-send");
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/chat/free`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ message, session_id: state.freeChatSessionId }),
    });
    const data = await res.json();
    state.freeChatSessionId = data.session_id;
    appendMessage(container, "bot", data.message);
  } catch {
    appendMessage(container, "bot",
      "抱歉，AI助手暂时无法连接。\n\n请确保后端服务已启动：\nuvicorn main:app --reload --port 8000"
    );
  }

  btn.disabled = false;
}

// ============ 面试模拟 ============

function startInterview() {
  const posEl = document.querySelector("#position-select .selected");
  const typeEl = document.querySelector("#interview-type-select .selected");

  if (!posEl) return alert("请选择目标岗位");

  state.selectedPosition = posEl.dataset.value;
  state.selectedInterviewType = typeEl ? typeEl.dataset.value : "technical";

  const typeNames = { technical: "技术面试", hr: "HR面试", project: "项目答辩" };
  document.getElementById("interview-title").textContent =
    `${state.selectedPosition} · ${typeNames[state.selectedInterviewType]}`;

  showPage("page-interview");

  const container = document.getElementById("interview-messages");
  container.innerHTML = "";

  doStartInterview(container);
}

async function doStartInterview(container) {
  try {
    const res = await fetch(`${API_BASE}/interview/start`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        session_id: state.sessionId,
        target_position: state.selectedPosition,
        interview_type: state.selectedInterviewType,
      }),
    });
    const data = await res.json();
    state.interviewSessionId = data.interview_session_id;
    appendMessage(container, "bot", data.message);
  } catch {
    appendMessage(container, "bot",
      `你好，我是今天的面试官。\n\n本次面试针对「${state.selectedPosition}」岗位。\n\n请先做一个简短的自我介绍，包括你的专业背景和为什么想做这个方向。\n\n（提示：后端服务未启动，当前为离线模式）`
    );
  }
}

async function sendInterviewChat() {
  const input = document.getElementById("interview-input");
  const message = input.value.trim();
  if (!message) return;

  const container = document.getElementById("interview-messages");
  appendMessage(container, "user", message);
  input.value = "";

  const btn = document.getElementById("btn-interview-send");
  btn.disabled = true;

  try {
    const res = await fetch(`${API_BASE}/interview/chat`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        interview_session_id: state.interviewSessionId,
        message,
      }),
    });
    const data = await res.json();
    appendMessage(container, "bot", data.message);

    if (data.is_complete) {
      appendMessage(container, "bot", "面试结束。以上是对你表现的详细评估，希望对你有帮助！");
    }
  } catch {
    appendMessage(container, "bot", "网络异常，请确认后端服务已启动。");
  }

  btn.disabled = false;
}

function endInterview() {
  if (confirm("确定要结束面试吗？")) {
    sendInterviewChat_internal("面试结束，请给出评估");
    showPage("page-home");
  }
}

// ============ 工具函数 ============

function appendMessage(container, role, text) {
  const div = document.createElement("div");
  div.className = `message ${role}`;
  div.innerHTML = `<div class="message-content">${escapeHtml(text)}</div>`;
  container.appendChild(div);
  container.scrollTop = container.scrollHeight;
}

function escapeHtml(text) {
  return text
    .replace(/&/g, "&amp;")
    .replace(/</g, "&lt;")
    .replace(/>/g, "&gt;")
    .replace(/\n/g, "<br>");
}

function getMajorName(value) {
  const names = {
    computer_science: "计算机科学与技术", software_engineering: "软件工程",
    network_engineering: "网络工程", electronic_info: "电子信息工程",
    communication: "通信工程", automation: "自动化",
    electrical: "电气工程", iot: "物联网工程",
    mechanical: "机械/机电", ai: "人工智能"
  };
  return names[value] || value;
}

function getGradeName(value) {
  const names = { freshman: "大一", sophomore: "大二", junior: "大三", senior: "大四" };
  return names[value] || value;
}

// 回车发送
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    const activeEl = document.activeElement;
    if (activeEl.id === "free-chat-input") { e.preventDefault(); sendFreeChat(); }
    if (activeEl.id === "deep-chat-input") { e.preventDefault(); sendDeepChat(); }
    if (activeEl.id === "interview-input") { e.preventDefault(); sendInterviewChat(); }
  }
});
