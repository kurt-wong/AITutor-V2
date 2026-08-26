import { Link, Route, Routes } from "react-router-dom";

import AdminHome from "./pages/AdminHome";
import StudentHome from "./pages/StudentHome";
import QuestionBankPage from "./pages/QuestionBankPage";

export default function App() {
  return (
    <Routes>
      <Route index element={<AdminHome />} />
      <Route path="/admin" element={<AdminHome />} />
      <Route path="/admin/questions" element={<QuestionBankPage />} />
      <Route path="/student" element={<StudentHome />} />
      <Route path="*" element={<AdminHome />} />
    </Routes>
  );
}
