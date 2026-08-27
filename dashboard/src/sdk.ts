export type Component = (props?: Record<string, unknown>) => unknown;

interface HermesSdk {
  React: {
    createElement: (...args: unknown[]) => unknown;
  };
  hooks: {
    useState: <T>(value: T) => [T, (value: T | ((old: T) => T)) => void];
    useEffect: (effect: () => void | (() => void), deps: unknown[]) => void;
    useMemo: <T>(factory: () => T, deps: unknown[]) => T;
  };
  components: Record<string, Component>;
  fetchJSON: <T>(path: string, init?: RequestInit) => Promise<T>;
  utils: {
    cn: (...values: Array<string | false | null | undefined>) => string;
    timeAgo?: (value: string | number) => string;
  };
}

interface HermesPluginRegistry {
  register(name: string, component: Component): void;
  registerSlot?(name: string, slot: string, component: Component): void;
}

declare global {
  interface Window {
    __HERMES_PLUGIN_SDK__?: HermesSdk;
    __HERMES_PLUGINS__?: HermesPluginRegistry;
  }
}

export function sdk(): HermesSdk {
  const value = window.__HERMES_PLUGIN_SDK__;
  if (!value?.React || !value.hooks || !value.fetchJSON) {
    throw new Error("Hermes dashboard SDK 1.1 is unavailable");
  }
  return value;
}

export const h = (...args: unknown[]): unknown => sdk().React.createElement(...args);

