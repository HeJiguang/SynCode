import type { CodeLanguage, QuestionDetail, QuestionListItem, SubmissionRecord } from "../contracts";

const languageCodes: Record<CodeLanguage, string> = {
  java: `class Solution {
    public int[] twoSum(int[] nums, int target) {
        return new int[] {};
    }
}`,
  cpp: `class Solution {
public:
    vector<int> twoSum(vector<int>& nums, int target) {
        return {};
    }
};`,
  python: `class Solution:
    def twoSum(self, nums: list[int], target: int) -> list[int]:
        return []`,
  go: `func twoSum(nums []int, target int) []int {
    return nil
}`,
  javascript: `var twoSum = function(nums, target) {
  return [];
};`
};

export const questions: QuestionListItem[] = [
  {
    questionId: "two-sum",
    title: "两数之和",
    difficulty: "Easy",
    tags: ["数组", "哈希表"],
    estimatedMinutes: 15,
    trainingRecommended: true,
    acceptanceRate: "62%",
    status: "尝试中",
    heat: 98
  },
  {
    questionId: "merge-intervals",
    title: "合并区间",
    difficulty: "Medium",
    tags: ["排序", "数组"],
    estimatedMinutes: 25,
    trainingRecommended: true,
    acceptanceRate: "47%",
    status: "未开始",
    heat: 83
  },
  {
    questionId: "lru-cache",
    title: "LRU 缓存",
    difficulty: "Medium",
    tags: ["设计", "哈希表", "链表"],
    estimatedMinutes: 35,
    trainingRecommended: false,
    acceptanceRate: "39%",
    status: "未开始",
    heat: 79
  },
  {
    questionId: "n-queens",
    title: "N 皇后",
    difficulty: "Hard",
    tags: ["回溯", "搜索"],
    estimatedMinutes: 45,
    trainingRecommended: false,
    acceptanceRate: "31%",
    status: "已解决",
    heat: 65
  }
];

export const hotQuestions: QuestionListItem[] = [...questions].sort((left, right) => right.heat - left.heat);

export const questionDetails: Record<string, QuestionDetail> = {
  "two-sum": {
    ...questions[0],
    summary: "一题看似简单，但非常适合校准哈希表写法、边界判断和代码提交节奏。",
    content: [
      "给定一个整数数组 nums 和一个整数目标值 target，请你在该数组中找出和为目标值的那两个整数，并返回它们的数组下标。",
      "你可以假设每种输入只会对应一个答案，并且同一个元素不能重复使用。"
    ],
    constraints: ["2 <= nums.length <= 10^4", "-10^9 <= nums[i], target <= 10^9"],
    hints: ["先查后存是最稳妥的哈希表模板。", "重点不是写出答案，而是保证不会用到同一个下标两次。"],
    examples: [
      {
        input: "nums = [2, 7, 11, 15], target = 9",
        output: "[0, 1]",
        note: "因为 nums[0] + nums[1] = 9"
      }
    ],
    starterCode: languageCodes,
    timeLimit: 1000,
    spaceLimit: 262144,
    algorithmTag: "哈希表",
    knowledgeTags: ["数组", "一次遍历", "补数映射"]
  },
  "merge-intervals": {
    ...questions[1],
    summary: "排序之后线性扫描，是建立区间题统一直觉的经典入口。",
    content: [
      "以数组 intervals 表示若干个区间的集合，其中单个区间为 intervals[i] = [start, end]。",
      "请你合并所有重叠的区间，并返回一个不重叠的区间数组，该数组需恰好覆盖输入中的所有区间。"
    ],
    constraints: ["1 <= intervals.length <= 10^4", "0 <= start <= end <= 10^4"],
    hints: ["先按起点排序，再处理当前区间与答案尾部的关系。", "这题适合复习“维护当前合并区间”的模板写法。"],
    examples: [
      {
        input: "intervals = [[1,3],[2,6],[8,10],[15,18]]",
        output: "[[1,6],[8,10],[15,18]]"
      }
    ],
    starterCode: {
      java: `class Solution {
    public int[][] merge(int[][] intervals) {
        return intervals;
    }
}`,
      cpp: `class Solution {
public:
    vector<vector<int>> merge(vector<vector<int>>& intervals) {
        return intervals;
    }
};`,
      python: `class Solution:
    def merge(self, intervals: list[list[int]]) -> list[list[int]]:
        return intervals`,
      go: `func merge(intervals [][]int) [][]int {
    return intervals
}`,
      javascript: `var merge = function(intervals) {
  return intervals;
};`
    },
    timeLimit: 2000,
    spaceLimit: 262144,
    algorithmTag: "排序",
    knowledgeTags: ["区间", "扫描线", "合并策略"]
  },
  "lru-cache": {
    ...questions[2],
    summary: "这题非常像真实面试里的设计题，考的是数据结构组合能力。",
    content: [
      "请你设计并实现一个满足 LRU (最近最少使用) 缓存约束的数据结构。",
      "实现 LRUCache 类，并提供 get 与 put 方法，要求二者平均时间复杂度为 O(1)。"
    ],
    constraints: ["1 <= capacity <= 3000", "最多调用 2 * 10^5 次 get 和 put"],
    hints: ["哈希表负责 O(1) 定位，双向链表负责 O(1) 调整顺序。", "这题很适合拆成“读操作”和“写操作”两个模板函数。"],
    examples: [
      {
        input: '["LRUCache","put","put","get","put","get"]',
        output: "[null,null,null,1,null,-1]"
      }
    ],
    starterCode: {
      java: `class LRUCache {
    public LRUCache(int capacity) {}
    public int get(int key) { return -1; }
    public void put(int key, int value) {}
}`,
      cpp: `class LRUCache {
public:
    LRUCache(int capacity) {}
    int get(int key) { return -1; }
    void put(int key, int value) {}
};`,
      python: `class LRUCache:
    def __init__(self, capacity: int):
        pass

    def get(self, key: int) -> int:
        return -1

    def put(self, key: int, value: int) -> None:
        pass`,
      go: `type LRUCache struct {}

func Constructor(capacity int) LRUCache { return LRUCache{} }
func (this *LRUCache) Get(key int) int { return -1 }
func (this *LRUCache) Put(key int, value int) {}`,
      javascript: `var LRUCache = function(capacity) {};
LRUCache.prototype.get = function(key) { return -1; };
LRUCache.prototype.put = function(key, value) {};`
    },
    timeLimit: 2000,
    spaceLimit: 262144,
    algorithmTag: "设计",
    knowledgeTags: ["双向链表", "哈希表", "缓存淘汰"]
  },
  "n-queens": {
    ...questions[3],
    summary: "用回溯构建搜索树边界感，是训练复杂问题拆解的好题。",
    content: [
      "按照国际象棋的规则，皇后可以攻击与之处于同一行、同一列或同一斜线上的棋子。",
      "给你一个整数 n ，返回所有不同的 n 皇后问题的解决方案。"
    ],
    constraints: ["1 <= n <= 9"],
    hints: ["列、主对角线、副对角线都可以用集合快速判断。", "把“放置皇后”和“撤销状态”拆清楚，代码会更稳定。"],
    examples: [
      {
        input: "n = 4",
        output: '[[".Q..","...Q","Q...","..Q."],["..Q.","Q...","...Q",".Q.."]]'
      }
    ],
    starterCode: {
      java: `class Solution {
    public List<List<String>> solveNQueens(int n) {
        return new ArrayList<>();
    }
}`,
      cpp: `class Solution {
public:
    vector<vector<string>> solveNQueens(int n) {
        return {};
    }
};`,
      python: `class Solution:
    def solveNQueens(self, n: int) -> list[list[str]]:
        return []`,
      go: `func solveNQueens(n int) [][]string {
    return nil
}`,
      javascript: `var solveNQueens = function(n) {
  return [];
};`
    },
    timeLimit: 2000,
    spaceLimit: 262144,
    algorithmTag: "回溯",
    knowledgeTags: ["搜索", "剪枝", "状态回退"]
  }
};

export const submissions: SubmissionRecord[] = [
  {
    submissionId: "sub-2311",
    status: "Wrong Answer",
    language: "Java",
    runtime: "8 ms",
    memory: "41.2 MB",
    submittedAt: "今天 19:42",
    notes: "边界 case: [3,3]"
  },
  {
    submissionId: "sub-2308",
    status: "Accepted",
    language: "Python",
    runtime: "56 ms",
    memory: "15.1 MB",
    submittedAt: "昨天 21:18"
  },
  {
    submissionId: "sub-2297",
    status: "Pending",
    language: "Go",
    runtime: "--",
    memory: "--",
    submittedAt: "刚刚"
  }
];
