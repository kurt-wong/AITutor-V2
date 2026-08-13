import { Link, Route, Routes } from "react-router-dom";

import AdminHome from "./pages/AdminHome";
import StudentHome from "./pages/StudentHome";

export default function App() {
  return (
    <Routes>
      <Route path="/admin" element={<AdminHome />} />
      <Route path="*" element={<StudentHome />} />
    </Routes>
  );
}

