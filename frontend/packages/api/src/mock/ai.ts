import type { AiMessage } from "../contracts";

export const aiMessages: AiMessage[] = [
  {
    id: "ai-1",
    role: "assistant",
    title: "思路提示",
    content: "这题最稳的起手式是哈希表。遍历当前元素前先查补数，再把当前值写入映射，可以避免使用同一个下标两次。"
  },
  {
    id: "user-1",
    role: "user",
    content: "为什么我的代码在 [3,3] 这个 case 上会错？"
  },
  {
    id: "ai-2",
    role: "assistant",
    title: "错误分析",
    content: "你现在的写法是先把当前值写入 map，再查补数，所以当 target = 6 且当前值是 3 时，会错误地命中自己。可以把顺序调整成“先查后存”。"
  }
];
