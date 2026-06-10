import { BrowserRouter, Routes, Route } from 'react-router-dom';
import SurveyListPage from './pages/SurveyListPage';
import SurveyEditorPage from './pages/SurveyEditorPage';
import SurveyResponsesPage from './pages/analytics/SurveyResponsesPage';
import SurveyPassPage from './pages/SurveyPassPage';
import LoginPage from './pages/LoginPage';
import UserProfilePage from './pages/UserProfilePage';
import RegisterPage from './pages/RegisterPage';
import AdminDashboardPage from "./admin/AdminDashboardPage";
import MainLayout from "./layout/MainLayout";
import AdminUsersPage from './admin/AdminUsersPage';
import AdminUserProfilePage from './admin/AdminUserProfilePage';
import AdminSurveysPage from './admin/AdminSurveysPage';
import AdminSurveyEditorPage from './admin/AdminSurveyEditorPage';
import AdminResponsesPage from './admin/AdminResponsesPage';
import AdminDetRespPage from './admin/AdminDetRespPage';
import SurveyAnalyticsListPage from './pages/analytics/SurveyAnalyticsListPage';
import SurveyAnalyticsPage from './pages/analytics/SurveyAnalyticPage';
import ReportBuilderPage from "./pages/analytics/ReportBuilderPage";
import ReportResultPage from "./pages/analytics/ReportResultPage";
import CreateSurveyPage from './pages/CreateSurveyPage';
import RequireRole from './components/RequireRole';

const adminOnly = ["admin"];
const organizerOrAdmin = ["admin", "organizer"];

export default function App() {
  return(
    <BrowserRouter>
      <Routes>
        <Route path="/" element={<MainLayout><SurveyListPage/></MainLayout>}/>
        <Route path='/editor/:id' element={<MainLayout><SurveyEditorPage/></MainLayout>}/>
        <Route path='/surveys/:id' element={<SurveyPassPage/>}/>
        <Route path='/login' element={<LoginPage/>}/>
        <Route path='/register' element={<RegisterPage/>}/>
        <Route path='/profile' element={<MainLayout><UserProfilePage/></MainLayout>}/>
        
        <Route path='/management/dashboard' element={<RequireRole allowedRoles={adminOnly}><MainLayout><AdminDashboardPage/></MainLayout></RequireRole>}/>
        <Route path='/management/users' element={<RequireRole allowedRoles={adminOnly}><MainLayout><AdminUsersPage/></MainLayout></RequireRole>}/>
        <Route path='/management/users/:id' element={<RequireRole allowedRoles={adminOnly}><MainLayout><AdminUserProfilePage/></MainLayout></RequireRole>} />
        <Route path='/management/surveys' element={<RequireRole allowedRoles={organizerOrAdmin}><MainLayout><AdminSurveysPage/></MainLayout></RequireRole>}/>
        <Route path='/management/surveys/:id' element={<RequireRole allowedRoles={organizerOrAdmin}><MainLayout><AdminSurveyEditorPage/></MainLayout></RequireRole>}/>
        
        <Route path='/analytics/surveys' element={<MainLayout><SurveyAnalyticsListPage/></MainLayout>}/>
        <Route path='/analytics/surveys/:id' element={<MainLayout><SurveyAnalyticsPage/></MainLayout>}/>
        <Route path="/analytics/surveys/:id/report-builder" element={<MainLayout><ReportBuilderPage /></MainLayout>}/>
        <Route path="/analytics/surveys/:id/report-result/:reportId" element={<MainLayout><ReportResultPage /></MainLayout>}/>
        <Route path='/analytics/surveys/:id/responses' element={<MainLayout><AdminResponsesPage/></MainLayout>}/>
        <Route path='/analytics/surveys/:id/responses/:responseId' element={<MainLayout><AdminDetRespPage/></MainLayout>}/>

        <Route path="/create" element={<MainLayout><CreateSurveyPage /></MainLayout>}/>

      </Routes>
    </BrowserRouter>
  )
}
