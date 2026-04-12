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
    phone: "",
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
  const phone = document.getElementById("input-phone").value.trim();
  const majorEl = document.querySelector("#major-select .selected");
  const gradeEl = document.querySelector("#grade-select .selected");
  const schoolEl = document.querySelector("#school-select .selected");

  if (!nickname) return alert("请输入昵称");
  if (!phone || !/^1[3-9]\d{9}$/.test(phone)) return alert("请输入正确的11位手机号");
  if (!majorEl) return alert("请选择专业");
  if (!gradeEl) return alert("请选择年级");

  state.profile.nickname = nickname;
  state.profile.phone = phone;
  state.profile.major = majorEl.dataset.value;
  state.profile.grade = gradeEl.dataset.value;
  state.profile.school_tier = schoolEl ? schoolEl.dataset.value : "普通本科";

  // 提前把手机号留资（不需要等到报告前，确保每一个开始测评的人都留下联系方式）
  earlyLeadCapture();

  loadQuestions();
}

async function earlyLeadCapture() {
  try {
    await fetch(`${API_BASE}/leads/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        phone: state.profile.phone,
        consent: true,
        source: "profile_form",
        nickname: state.profile.nickname,
        major: state.profile.major,
        grade: state.profile.grade,
        school_tier: state.profile.school_tier,
      }),
    });
  } catch (e) {
    // 留资失败不影响用户做题
    console.warn("early lead capture failed:", e);
  }
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
    { id: "B01", dimension: "theory", question: "TCP 三次握手的第二步，服务端发送的报文包含哪些标志位？", options: [
      { text: "不确定，TCP 握手的细节记不清了", score: 1 },
      { text: "SYN 和 ACK 都有，但不太清楚序列号的变化", score: 2 },
      { text: "SYN+ACK，序列号为服务端 ISN，确认号为客户端 ISN+1", score: 3 },
      { text: "以上都清楚，还能解释 SYN Flood 攻击原理及防御方法", score: 4 }
    ]},
    { id: "B02", dimension: "theory", question: "OSPF 路由协议中，Router LSA 和 Network LSA 的区别是什么？", options: [
      { text: "知道 OSPF 是路由协议，但 LSA 类型分不清", score: 1 },
      { text: "知道 LSA 有多种类型，大概了解它们作用不同", score: 2 },
      { text: "Router LSA 描述路由器直连链路，Network LSA 描述多路访问网络上的路由器列表", score: 3 },
      { text: "能完整解释 1-5 类 LSA 的产生条件和泛洪范围，并做过多区域 OSPF 的实际配置", score: 4 }
    ]},
    { id: "B03", dimension: "programming", question: "Python 中 list 和 tuple 的核心区别以及使用场景？", options: [
      { text: "知道都是容器类型，但说不清具体区别", score: 1 },
      { text: "list 可变、tuple 不可变，语法上一个用 [] 一个用 ()", score: 2 },
      { text: "理解不可变性带来的 hashable 特性（tuple 可做 dict 的 key），以及性能差异", score: 3 },
      { text: "还能解释 namedtuple/dataclass 的使用场景，以及在多线程环境下不可变对象的优势", score: 4 }
    ]},
    { id: "B04", dimension: "programming", question: "用 C 语言实现一个链表的节点删除操作，你能做到什么程度？", options: [
      { text: "链表的结构体定义都写不太出来", score: 1 },
      { text: "能写出结构体和简单的遍历，但删除节点时指针操作经常出错", score: 2 },
      { text: "能正确处理头节点/尾节点/中间节点的删除，会用 free() 释放内存", score: 3 },
      { text: "还能实现双向链表、环形链表的增删改查，理解内存泄漏检测和 valgrind 使用", score: 4 }
    ]},
    { id: "B05", dimension: "hardware", question: "使用万用表测量一个未知电阻，你的操作流程是？", options: [
      { text: "万用表的档位选择都不太确定", score: 1 },
      { text: "知道选电阻档、调零、读数，但实际操作不太熟练", score: 2 },
      { text: "能正确选档、短接调零、读取色环/数值、判断误差范围，会区分二线/四线测量法", score: 3 },
      { text: "能用万用表做完整的电路故障排查（测通断、电压、电流），还会用示波器分析信号波形", score: 4 }
    ]},
    { id: "B06", dimension: "hardware", question: "交换机上配置 VLAN 时，Access 口和 Trunk 口的区别？", options: [
      { text: "听过 VLAN 但没实际配置过，不清楚端口类型", score: 1 },
      { text: "知道 Access 口只属于一个 VLAN，Trunk 口可以传多个 VLAN 的数据", score: 2 },
      { text: "理解 802.1Q 标签的添加/剥离过程，能在真实设备上做 VLAN 划分和跨交换机互通", score: 3 },
      { text: "能做三层交换+VLAN 间路由+DHCP Relay，处理过生产环境的 VLAN 故障", score: 4 }
    ]},
    { id: "B07", dimension: "tools", question: "在 Linux 下查看某个端口被哪个进程占用，你会用什么命令？", options: [
      { text: "不太会在 Linux 下操作，可能要搜一下", score: 1 },
      { text: "知道可以用 netstat 或 ss 命令，但具体参数记不住", score: 2 },
      { text: "ss -tlnp 或 netstat -tlnp 直接查看，还会用 lsof -i :端口号", score: 3 },
      { text: "熟练使用 systemd/journalctl/iptables/tcpdump 等做系统级排查和服务管理", score: 4 }
    ]},
    { id: "B08", dimension: "tools", question: "关于 Git 版本管理，以下哪个最符合你的水平？", options: [
      { text: "没用过 Git，代码用 U 盘或微信传", score: 1 },
      { text: "会 git add/commit/push 基本流程，但遇到冲突就慌", score: 2 },
      { text: "能处理合并冲突、用分支管理功能开发、会 git log/diff/stash", score: 3 },
      { text: "熟练使用 rebase/cherry-pick/子模块、参与过多人协作项目的 PR/Code Review 流程", score: 4 }
    ]},
    { id: "B09", dimension: "project", question: "你独立做过的最完整的技术项目是什么级别？", options: [
      { text: "只做过课堂练习和课后作业", score: 1 },
      { text: "做过课程设计，但主要是改模板/参考代码", score: 2 },
      { text: "从零开始做过一个完整项目（有需求分析、架构设计、编码、测试、部署全流程）", score: 3 },
      { text: "做过 3+ 个独立项目 / 竞赛获省级以上奖项 / 有企业实习开发经验", score: 4 }
    ]},
    { id: "B10", dimension: "project", question: "如果让你现在面试，能讲清楚一个技术项目的完整架构和难点吗？", options: [
      { text: "没有可以讲的项目", score: 1 },
      { text: "能说出做了什么，但技术细节和为什么这样设计说不太清", score: 2 },
      { text: "能讲清架构选型原因、关键技术难点及解决方案、数据流向", score: 3 },
      { text: "能从业务需求→技术选型→实现→性能优化→踩坑经验完整复盘，有量化成果", score: 4 }
    ]},
    { id: "B11", dimension: "soft_skill", question: "如果团队项目中，一个同学代码写得有问题导致整体延期，你会怎么处理？", options: [
      { text: "不知道怎么开口，可能就自己默默帮改或等他自己发现", score: 1 },
      { text: "会直接指出来但不太会顾及对方感受，容易引起冲突", score: 2 },
      { text: "先私下沟通指出具体问题，一起讨论解决方案，帮他排查而不是代写", score: 3 },
      { text: "有过多次团队管理经验，会做 Code Review 制度，用流程规避而不是靠人情", score: 4 }
    ]},
    { id: "B12", dimension: "soft_skill", question: "让你写一份「校园网络改造方案」的技术文档，你能做到什么程度？", options: [
      { text: "不知道技术文档该包含哪些内容", score: 1 },
      { text: "能列出目录结构（需求、方案、预算），但内容比较空泛", score: 2 },
      { text: "能写出完整的文档（含拓扑图、IP规划表、设备选型、施工计划、预算清单）", score: 3 },
      { text: "写过正式投标/验收文档，能做答辩汇报，文档通过了甲方或评委的审核", score: 4 }
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
        reportBtn.onclick = () => requestLeadBeforeReport();
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
  // 不直接生成报告，先走留资弹窗
  requestLeadBeforeReport();
}

// ============ 留资弹窗（看报告前拦截） ============

// 同一次会话内已经留过资就不重复弹窗
let leadCaptured = false;

function requestLeadBeforeReport() {
  if (leadCaptured) {
    generateReport();
    return;
  }
  showLeadModal();
}

function showLeadModal() {
  const modal = document.getElementById("lead-modal");
  if (!modal) {
    generateReport();
    return;
  }
  modal.classList.add("show");
  document.getElementById("lead-error").textContent = "";
  // 预填 profile 阶段已收集的手机号
  document.getElementById("lead-phone").value = state.profile.phone || "";
  document.getElementById("lead-consent").checked = !!state.profile.phone;
  if (state.profile.phone) {
    // 已经有手机号，聚焦到提交按钮
    document.getElementById("lead-submit-btn").focus();
  } else {
    setTimeout(() => document.getElementById("lead-phone").focus(), 100);
  }
}

function hideLeadModal() {
  document.getElementById("lead-modal").classList.remove("show");
}

async function submitLead() {
  const phoneEl = document.getElementById("lead-phone");
  const consentEl = document.getElementById("lead-consent");
  const errorEl = document.getElementById("lead-error");
  const btn = document.getElementById("lead-submit-btn");

  const phone = (phoneEl.value || "").trim();
  errorEl.textContent = "";

  if (!/^1[3-9]\d{9}$/.test(phone)) {
    errorEl.textContent = "请输入正确的 11 位手机号";
    phoneEl.focus();
    return;
  }
  if (!consentEl.checked) {
    errorEl.textContent = "请先勾选同意隐私条款";
    return;
  }

  btn.disabled = true;
  const originalText = btn.textContent;
  btn.textContent = "提交中...";

  try {
    const payload = {
      phone,
      consent: true,
      session_id: state.sessionId || null,
      source: "report_gate",
      nickname: state.profile.nickname || null,
      major: state.profile.major || null,
      grade: state.profile.grade || null,
      school_tier: state.profile.school_tier || null,
      overall_score: state.quickResult ? state.quickResult.overall_score : null,
      weak_dimensions: state.quickResult ? state.quickResult.weak_dimensions : null,
    };

    const res = await fetch(`${API_BASE}/leads/submit`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
    });

    if (!res.ok) {
      const err = await res.json().catch(() => ({}));
      errorEl.textContent = err.detail || "提交失败，请稍后再试";
      btn.disabled = false;
      btn.textContent = originalText;
      return;
    }

    // 成功：关闭弹窗，继续看报告
    leadCaptured = true;
    hideLeadModal();
    generateReport();
  } catch (e) {
    // 网络异常：允许用户继续看报告（不阻断），但也不标记为已留资
    console.warn("lead submit failed:", e);
    errorEl.textContent = "网络异常，点击下方按钮可直接查看报告";
    btn.textContent = "跳过，直接看报告";
    btn.disabled = false;
    btn.onclick = () => {
      hideLeadModal();
      btn.onclick = submitLead;
      btn.textContent = originalText;
      generateReport();
    };
  }
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

// ============ 微信小程序环境检测 ============

// 检测是否在微信/小程序 web-view 中打开
function isWeChatEnv() {
  const ua = navigator.userAgent.toLowerCase();
  return ua.indexOf("micromessenger") !== -1 || ua.indexOf("miniprogram") !== -1;
}

// 小程序通过 URL 参数传入 wx_code，H5 自动换取 openid
(async function initWxLogin() {
  const params = new URLSearchParams(window.location.search);
  const wxCode = params.get("wx_code");
  if (!wxCode) return;

  try {
    const res = await fetch(`${API_BASE}/wechat/code2session`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ code: wxCode }),
    });
    if (res.ok) {
      const data = await res.json();
      state.wxOpenId = data.openid;
      console.log("[WX] openid obtained");
    }
  } catch (e) {
    console.warn("[WX] code2session failed:", e);
  }
})();

// 回车发送
document.addEventListener("keydown", (e) => {
  if (e.key === "Enter" && !e.shiftKey) {
    const activeEl = document.activeElement;
    if (activeEl.id === "free-chat-input") { e.preventDefault(); sendFreeChat(); }
    if (activeEl.id === "deep-chat-input") { e.preventDefault(); sendDeepChat(); }
    if (activeEl.id === "interview-input") { e.preventDefault(); sendInterviewChat(); }
  }
});
