export function fetchSurveys() {
  return Promise.resolve(surveys);
}

const surveys = [
  {
    id: 1,
    title: "Опрос о питании",
    description: "Ваши пищевые привычки",
    status: "active",
    author: "ivan@example.com",
    created_at: "2025-10-11",
    responses_count: 32,
    questions: [
      { id: 101, text: "Ваш любимый фрукт?", type: "single", options: [
        { id: 1001, text: "Яблоко" },
        { id: 1002, text: "Банан" },
        { id: 1003, text: "Апельсин" }
      ]},
      { id: 102, text: "Сколько раз в неделю вы едите овощи?", type: "number" }
    ]
  },

  {
    id: 2,
    title: "Удовлетворенность услугами",
    description: "Оцените качество",
    status: "active",
    author: "ivan@example.com",
    created_at: "2025-10-09",
    responses_count: 80,
    questions: []
  },

  {
    id: 3,
    title: "Оценка продукта",
    description: "Фидбек",
    status: "closed",
    author: "organizer1@example.com",
    created_at: "2025-01-20",
    responses_count: 54,
    questions: []
  }
];


export function fetchSurveyById(id) {
  return Promise.resolve(
    surveys.find(s => s.id == id)
  );
}

export function saveSurveyChanges(survey) {
  console.log("Сохранено:", survey);
  return Promise.resolve(true);
}

export function addQuestionToSurvey(surveyId, type) {
  const q = {
    id: Date.now(),
    text: "",
    type,
    options: type === "scale" ? [] : [],
  };
  return Promise.resolve(q);
}


export function fetchSurveyDetail(id) {
  return Promise.resolve({
    id,
    title: "Опрос о питании",
    description: "Ваши пищевые привычки",
    questions: []
  });
}

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
        text: "Какой объем кофе вы предпочитаете?",
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

const stats = {
    totalUsers: 152,
    activeUsers: 134,
    totalSurveys: 48,
    activeSurveys: 12,
    todaysResponses: 84,
};

export function fetchSystemStats() {
  return Promise.resolve(stats);
};

// Мок-пользователь
let mockUser = {
  id: 1,
  first_name: "Иван",
  last_name: "Иванов",
  patronymic: "Иванович",
  email: "user@example.com",
  role: "admin",
  date_joined: "2025-01-01"
};

// Получение профиля
export function fetchUserProfile() {
  return Promise.resolve(mockUser);
}

// Обновление профиля
export function mockUpdateUserProfile(data) {
  mockUser = { ...mockUser, ...data }; // обновление мок-данных
  return Promise.resolve(mockUser);
}

const users = [
    { id: 1, email: "ivan@example.com", first_name: "Иван", last_name: "Иванков", patronymic: "Иванович", date_joined: "2025-02-03", role: "organizer", is_blocked: false },
    { id: 2, email: "petr@example.com", first_name: "Пётр", last_name: "Петров", patronymic: "Петрович", date_joined: "2025-02-02", role: "respondent", is_blocked: true },
    { id: 3, email: "maria@example.com", first_name: "Мария", last_name: "Смирнова", patronymic: "Мариевна", date_joined: "2025-02-01", role: "respondent", is_blocked: false },
];

export function fetchRecentUsers() {
  return Promise.resolve(users);
};

const responsesByDay = [
    { date: "02-01", count: 12 },
    { date: "02-02", count: 18 },
    { date: "02-03", count: 25 },
    { date: "02-04", count: 20 },
    { date: "02-05", count: 30 },
];

export function fetchResponsesByDay() {
  return Promise.resolve(responsesByDay);
};

const surveyStatusData = [
    { name: "Активные", value: 12 },
    { name: "Черновики", value: 8 },
    { name: "Завершённые", value: 28 },
];

export function fetchSurveyStatusData() {
  return Promise.resolve(surveyStatusData);
};

const registrations = [
    { date: "02-01", users: 4 },
    { date: "02-02", users: 7 },
    { date: "02-03", users: 5 },
    { date: "02-04", users: 8 },
    { date: "02-05", users: 10 },
];

export function fetchRegistrations() {
  return Promise.resolve(registrations);
};

export function blockUser(id) {
  console.log("User blocked:", id);
}

export function unblockUser(id) {
  console.log("User unblocked:", id);
}

export function deleteUser(id) {
  console.log("User deleted:", id);
}
