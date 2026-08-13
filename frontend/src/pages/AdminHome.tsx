import { Link } from "react-router-dom";

export default function AdminHome() {
  return (
    <main className="page">
      <nav className="top-nav">
        <Link to="/">学生端</Link>
        <Link to="/admin">管理后台</Link>
      </nav>
      <section className="hero-tile light">
        <h1>AI Tutor 管理后台</h1>
        <p>项目初始化完成，管理端骨架已就绪。</p>
      </section>
    </main>
  );
}

