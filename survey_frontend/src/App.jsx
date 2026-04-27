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
        
        <Route path='/admin/dashboard' element={<MainLayout><AdminDashboardPage/></MainLayout>}/>
        <Route path='/admin/users' element={<MainLayout><AdminUsersPage/></MainLayout>}/>
        <Route path='/admin/users/:id' element={<MainLayout><AdminUserProfilePage/></MainLayout>} />
        <Route path='/admin/surveys' element={<MainLayout><AdminSurveysPage/></MainLayout>}/>
        <Route path='/admin/surveys/:id' element={<MainLayout><AdminSurveyEditorPage/></MainLayout>}/>
        
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
