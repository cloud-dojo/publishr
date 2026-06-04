import type { User } from "./types";
import { OWNER } from "./books";

/*
 * デモ主人公（デモ素材「デモペルソナ.md」準拠）。
 * 佐倉美咲・35歳・食品メーカー「マルミナ食品」マーケティング担当・2026年4月に課長昇格・部下7名。
 */

export const user: User = {
  uid: OWNER,
  displayName: "佐倉 美咲",
  email: "publishr.demo.misa@gmail.com",
  role: "マルミナ食品 マーケティング課長",
  avatarChar: "咲",
  initialProfile: {
    industry: "食品・飲料",
    jobType: "マーケティング・ブランド",
    position: "課長・マネージャー",
    recentInterests: [
      "新任マネジメント・チームづくり",
      "メンバー育成・1on1",
      "評価・フィードバック",
      "マーケティング・ブランディング",
    ],
    readingGenres: ["すぐ使える実践書・ハウツー", "事例・ストーリーで学ぶ"],
  },
  favoriteAuthors: [
    {
      personaId: "p03",
      name: "御園 隆司",
      style: "大局派 / 品格 / 長期視点",
      savedAt: "2026-05-19T08:00:00+09:00",
    },
  ],
};
