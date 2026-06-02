import { BffProvider } from "./bff-provider";
import { dataSource } from "./config";
import { MockProvider } from "./mock-provider";
import { BaseProvider } from "./provider";

let _provider: BaseProvider | null = null;

export function getProvider(): BaseProvider {
  if (!_provider) {
    _provider = dataSource === "mock" ? new MockProvider() : new BffProvider();
  }
  return _provider;
}

export { dataSource } from "./config";
export type { BaseProvider } from "./provider";
