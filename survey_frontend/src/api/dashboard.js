import { fetchAdminSurveys, fetchSurveyResponses } from "./surveys";
import { fetchAllUsers } from "./users";

function toDate(value) {
  if (!value) return null;
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? null : date;
}

function dateKey(value) {
  const date = toDate(value);
  if (!date) return null;

  const year = date.getFullYear();
  const month = String(date.getMonth() + 1).padStart(2, "0");
  const day = String(date.getDate()).padStart(2, "0");

  return `${year}-${month}-${day}`;
}

function sortByDateDesc(items, field) {
  return [...items].sort((a, b) => {
    const left = toDate(a[field])?.getTime() || 0;
    const right = toDate(b[field])?.getTime() || 0;
    return right - left;
  });
}

function groupByDate(items, field, valueField) {
  const totals = items.reduce((acc, item) => {
    const key = dateKey(item[field]);
    if (!key) return acc;

    acc[key] = (acc[key] || 0) + (valueField ? item[valueField] : 1);
    return acc;
  }, {});

  return Object.entries(totals)
    .sort(([left], [right]) => left.localeCompare(right))
    .map(([date, count]) => ({ date, count }));
}

async function fetchResponsesForSurveys(surveys) {
  const responseGroups = await Promise.all(
    surveys.map(async survey => {
      try {
        const responses = await fetchSurveyResponses(survey.id);
        return responses.map(response => ({
          ...response,
          survey_id: survey.id,
        }));
      } catch {
        return [];
      }
    })
  );

  return responseGroups.flat();
}

export async function fetchDashboardData() {
  const [users, surveys] = await Promise.all([
    fetchAllUsers(),
    fetchAdminSurveys(),
  ]);

  const responses = await fetchResponsesForSurveys(surveys);
  const completedResponses = responses.filter(response => response.is_complete);

  const today = dateKey(new Date());

  const statusLabels = {
    draft: "Черновики",
    active: "Активные",
    closed: "Закрытые",
  };

  const surveyStatusData = Object.entries(statusLabels).map(([status, name]) => ({
    name,
    value: surveys.filter(survey => survey.status === status).length,
  }));

  return {
    users,
    surveys,
    responses,
    stats: {
      totalUsers: users.length,
      activeUsers: users.filter(user => user.is_active).length,
      totalSurveys: surveys.length,
      activeSurveys: surveys.filter(survey => survey.status === "active").length,
      todaysResponses: completedResponses.filter(
        response => dateKey(response.finished_at) === today
      ).length,
    },
    charts: {
      responsesByDay: groupByDate(completedResponses, "finished_at"),
      surveyStatusData,
      registrations: groupByDate(users, "date_joined").map(item => ({
        date: item.date,
        users: item.count,
      })),
    },
    recentUsers: sortByDateDesc(users, "date_joined").slice(0, 5),
    recentSurveys: sortByDateDesc(surveys, "created_at").slice(0, 5),
  };
}
