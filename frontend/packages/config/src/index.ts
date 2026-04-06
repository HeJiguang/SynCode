export const productName = "SynCode";
export const productTagline = "编程训练与题库平台";
export const frontendPreviewMode = process.env.NEXT_PUBLIC_SYNCODE_PREVIEW_MODE === "1";
export const frontendPreviewLabel = "Preview Mode";

export const githubUrl = "https://github.com/HeJiguang/SynCode";

export const webNav = [
  { label: "开始体验", href: "/app" },
  { label: "GitHub", href: githubUrl }
];

export const appNav = [
  { label: "工作台", href: "/" },
  { label: "题库", href: "/problems" },
  { label: "训练", href: "/training" },
  { label: "考试", href: "/exams" },
  { label: "我的", href: "/me" }
];

export const appQuickLinks = [
  { label: "返回首页", href: "/" },
  { label: "系统公告", href: "/app#announcements" },
  { label: "个人设置", href: "/app/settings" }
];

export const adminNav = [
  { label: "概览", href: "/" },
  { label: "公告管理", href: "/notices" },
  { label: "题目管理", href: "/questions" },
  { label: "考试管理", href: "/exams" },
  { label: "用户管理", href: "/users" }
];
