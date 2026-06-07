import { BffProvider } from "./bff-provider";
import { dataSource } from "./config";
import { FirestoreProvider } from "./firestore-provider";
import { MockProvider } from "./mock-provider";
import { BaseProvider } from "./provider";

let _provider: BaseProvider | null = null;

function createProvider(): BaseProvider {
  switch (dataSource) {
    case "mock":
      return new MockProvider();
    // firestore 選択時のみ実体化。
    // SSR（window 未定義）では FirestoreProvider を作れないので MockProvider で代替。
    // クライアント側の load() + setOwnerUid() で Firestore 購読が張り直される。
    case "firestore":
      if (typeof window === "undefined") return new MockProvider();
      return new FirestoreProvider();
    default:
      return new BffProvider();
  }
}

export function getProvider(): BaseProvider {
  if (!_provider) {
    _provider = createProvider();
  }
  return _provider;
}

export { dataSource } from "./config";
export type { BaseProvider } from "./provider";
