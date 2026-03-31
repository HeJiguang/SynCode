import type { PublicMessage } from "../contracts";

export const publicMessages: PublicMessage[] = [
  {
    textId: "msg-1",
    title: "系统公告：工作区改版预览已上线",
    content: "新的刷题工作区已经支持更强的布局层级和多语言代码编辑体验，本周内会继续接入真实判题与消息接口。",
    category: "公告",
    publishedAt: "今天 18:30",
    pinned: true
  },
  {
    textId: "msg-2",
    title: "训练更新：热题榜按最近访问热度刷新",
    content: "工作台上的热题模块已按热门问题列表预留数据结构，后续将对齐 /friend/question/semiLogin/hotList。",
    category: "更新",
    publishedAt: "今天 14:10",
    pinned: false
  },
  {
    textId: "msg-3",
    title: "考试提醒：周末算法冲刺测将在明晚开始",
    content: "请提前检查网络、语言模板和本地输入输出习惯，避免在正式考试中消耗额外时间。",
    category: "考试",
    publishedAt: "昨天 21:00",
    pinned: false
  }
];
