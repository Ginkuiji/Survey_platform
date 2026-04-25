/* ============================================================
   МОДУЛЬ МОКОВ API (frontend-friendly)
   Совместим с реальным Django API и легко заменяется на fetch()
   ============================================================ */

/* ------------------------------------------------------------
   1) AUTH
   ------------------------------------------------------------ */

let mockCurrentUser = {
  id: 1,
  first_name: "Иван",
  last_name: "Иванов",
  email: "ivan@example.com",
  role: "admin",
  date_joined: "2025-01-01",
  is_blocked: false,
  avatar: "https://i.pravatar.cc/150?img=5"
};

export function fetchUserProfile() {
  return Promise.resolve({ ...mockCurrentUser });
}

export function mockUpdateUserProfile(data) {
  mockCurrentUser = { ...mockCurrentUser, ...data };
  return Promise.resolve({ ...mockCurrentUser });
}

/* ------------------------------------------------------------
   2) USERS
   (для админ-панели)
   ------------------------------------------------------------ */

let mockUsers = [
  { id: 1, email: "ivan@example.com", first_name: "Иван", last_name: "Иванков", date_joined: "2025-02-03", role: "organizer", is_blocked: false },
  { id: 2, email: "petr@example.com", first_name: "Пётр", last_name: "Петров", date_joined: "2025-02-02", role: "respondent", is_blocked: true },
  { id: 3, email: "maria@example.com", first_name: "Мария", last_name: "Смирнова", date_joined: "2025-02-01", role: "respondent", is_blocked: false },
];

export function fetchAllUsers() {
  return Promise.resolve([...mockUsers]);
}

export function fetchRecentUsers() {
  return Promise.resolve([...mockUsers].slice(-3));
}

export function blockUser(id) {
  const u = mockUsers.find(x => x.id === Number(id));
  if (u) u.is_blocked = true;
  return Promise.resolve(true);
}

export function unblockUser(id) {
  const u = mockUsers.find(x => x.id === Number(id));
  if (u) u.is_blocked = false;
  return Promise.resolve(true);
}

export function deleteUser(id) {
  mockUsers = mockUsers.filter(u => u.id !== Number(id));
  return Promise.resolve(true);
}

/* ------------------------------------------------------------
   3) SURVEYS (Owner / Organizer / Admin)
   ------------------------------------------------------------ */

let mockSurveys = [
  {
    id: 1,
    title: "Опрос о питании",
    description: "Ваши пищевые привычки",
    status: "active",
    category: "здоровье",
    created_at: "2025-01-10",
    starts_at: "2025-01-15",
    ends_at: "2025-02-01",
    authors: ["ivan@example.com"],
    responses_count: 32,
    questions: [
      {
        id: 101,
        text: "Ваш любимый фрукт?",
        type: "single",
        options: [
          { id: 1001, text: "Яблоко" },
          { id: 1002, text: "Банан" },
          { id: 1003, text: "Апельсин" }
        ]
      },
      {
        id: 102,
        text: "Сколько раз в неделю вы едите овощи?",
        type: "number"
      }
    ]
  },

  {
    id: 2,
    title: "Удовлетворенность сервисом",
    description: "Оценка качества",
    status: "draft",
    category: "образование",
    created_at: "2025-01-05",
    starts_at: "2025-01-15",
    ends_at: "2025-02-01",
    author: "ivan@example.com",
    responses_count: 12,
    questions: []
  },

  {
    id: 3,
    title: "Пример опроса 1",
    description: "Описание опроса 1",
    status: "draft",
    category: "образование",
    created_at: "2025-01-05",
    starts_at: "2025-01-15",
    ends_at: "2025-02-01",
    author: "ivan@example.com",
    responses_count: 12,
    questions: []
  },
  {
    id: 4,
    title: "Пример опроса номер 2",
    description: "Описание опроса 2",
    status: "draft",
    category: "образование",
    created_at: "2025-01-05",
    starts_at: "2025-01-15",
    ends_at: "2025-02-01",
    author: "ivan@example.com",
    responses_count: 12,
    questions: []
  },
  {
    id: 5,
    title: "Опрос номер 3",
    description: "Описание опроса 3",
    status: "finished",
    category: "образование",
    created_at: "2025-01-05",
    starts_at: "2025-01-15",
    ends_at: "2025-02-01",
    author: "ivan@example.com",
    responses_count: 12,
    questions: []
  }
];

export function fetchSurveys() {
  return Promise.resolve([...mockSurveys]);
}

export function fetchSurveyById(id) {
  return Promise.resolve(
    mockSurveys.find(s => s.id === Number(id)) || null
  );
}

export function saveSurveyChanges(updated) {
  const index = mockSurveys.findIndex(s => s.id === updated.id);
  if (index !== -1) mockSurveys[index] = { ...updated };
  return Promise.resolve(true);
}

export function addQuestionToSurvey(surveyId, type) {
  const newQ = {
    id: Date.now(),
    text: "",
    type,
    options: type === "single" || type === "multi" ? [] : [],
    qsettings: type === "scale" ? { min: 1, max: 5, step: 1 } : {}
  };

  const survey = mockSurveys.find(s => s.id === Number(surveyId));
  if (survey) survey.questions.push(newQ);

  return Promise.resolve(newQ);
}

export function updateSurveyAuthors(id, authors) {
  const s = mockSurveys.find(s => s.id === Number(id));
  if (s) s.authors = [...authors];
  return Promise.resolve(true);
}


/* ------------------------------------------------------------
   4) SURVEY PASSING (Respondent)
   ------------------------------------------------------------ */

// export function fetchSurveyForPassing(id) {
//   const survey = mockSurveys.find(s => s.id === Number(id));
//   if (!survey) return Promise.resolve(null);

//   return Promise.resolve({
//     id: survey.id,
//     title: survey.title,
//     description: survey.description,
//     questions: survey.questions
//   });
// }

export function fetchSurveyForPassing(id) {
  return Promise.resolve({
    id,
    title: "Опрос о питании",
    description: "Ваши пищевые привычки",
    questions: [
      {
        id: 1,
        text: "Сколько раз в неделю вы едите овощи?",
        type: "number"
      },
      {
        id: 2,
        text: "Ваш любимый напиток?",
        type: "text"
      },
      {
        id: 3,
        text: "Какой завтрак вы предпочитаете?",
        type: "single",
        options: [
          { id: 1, text: "Каша" },
          { id: 2, text: "Яичница" },
          { id: 3, text: "Тосты" }
        ]
      },
      {
        id: 4,
        text: "Что вы добавляете в кофе?",
        type: "multi",
        options: [
          {id: 1, text: "Вода"},
          {id: 2, text: "Молоко"},
          {id: 3, text: "Сахар"},
          {id: 4, text: "Сливки"},
          {id: 5, text: "Корица"}
        ]
      },
      {
        id:5,
        text: "Сколько кофе вы пьете?",
        type: "scale",
        qsettings: {
          min: 100,
          max: 500,
          step: 50
        }
      }
    ]
  });
}

/* ------------------------------------------------------------
   5) ANALYTICS (Admin)
   ------------------------------------------------------------ */

const responsesByDay = [
  { date: "02-01", count: 12 },
  { date: "02-02", count: 18 },
  { date: "02-03", count: 25 }
];

export function fetchResponsesByDay() {
  return Promise.resolve(responsesByDay);
}

const surveyStatusData = [
  { name: "Активные", value: 12 },
  { name: "Черновики", value: 8 },
  { name: "Завершённые", value: 15 }
];

export function fetchSurveyStatusData() {
  return Promise.resolve(surveyStatusData);
}

const registrations = [
  { date: "02-01", users: 4 },
  { date: "02-02", users: 7 },
  { date: "02-03", users: 5 }
];

export function fetchRegistrations() {
  return Promise.resolve(registrations);
}

/* ------------------------------------------------------------
   6) SYSTEM STATS (Admin dashboard)
   ------------------------------------------------------------ */

const systemStats = {
  totalUsers: 150,
  activeUsers: 130,
  totalSurveys: 48,
  activeSurveys: 12,
  todaysResponses: 84
};

export function fetchSystemStats() {
  return Promise.resolve(systemStats);
}

/* ------------------------------------------------------------
   7) ANALYTICS (Organizer stats)
   ------------------------------------------------------------ */

export function fetchQuestionAnalytics(questionId) {
  // На основе структуры Django Analytics — см. analytics.py
  // Сейчас просто моки

  const example = {
    question: questionId,
    text: "Пример вопроса",
    type: "single",
    total_responses: 32,
    options: [
      { id: 1, text: "Вариант A", count: 10, percent: 31 },
      { id: 2, text: "Вариант B", count: 12, percent: 38 },
      { id: 3, text: "Вариант C", count: 10, percent: 31 },
    ]
  };

  return Promise.resolve(example);
}

/* ------------------------------------------------------------
   8) RESPONSES (для аналитики)
   ------------------------------------------------------------ */

let mockResponses = {
  1: [
    {
      id: 10001,
      user: "Anastasia@example.com",
      finished_at: "2025-02-05 12:10",
      answers: [
        { question: 101, type: "single", value: "Банан" },
        { question: 102, type: "number", value: 5 }
      ]
    },
    {
      id: 10002,
      user: "maria@example.com",
      finished_at: "2025-02-05 13:05",
      answers: [
        { question: 101, type: "single", value: "Яблоко" },
        { question: 102, type: "number", value: 3 }
      ]
    }
  ],

  2: []
};

export function fetchSurveyResponses(surveyId) {
  return Promise.resolve(mockResponses[surveyId] || []);
}


/* ============================================================
   END: Mock API
   ============================================================ */
