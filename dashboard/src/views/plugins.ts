import { Card, DataTable, KeyValues } from "../components/data";
import { arrayValue, evidenceData, objectValue } from "./helpers";

export function PluginsView({ data }: { data: Record<string, unknown> }): unknown {
  const payload = objectValue(evidenceData(data, {}));
  const plugins = arrayValue(payload.plugins);
  return Card({
    title: `User plugins · ${plugins.length}`,
    status: String(data.status ?? "UNKNOWN"),
    children: plugins.length
      ? DataTable({
          rows: plugins,
          columns: [
            { key: "name", label: "Plugin" },
            { key: "version", label: "Version" },
            { key: "status", label: "Status" },
            { key: "dashboard_manifest", label: "Dashboard" },
            { key: "is_symlink", label: "Symlink" },
          ],
          empty: "No user plugins discovered.",
        })
      : KeyValues({ value: payload }),
  });
}

