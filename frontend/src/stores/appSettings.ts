import { defineStore } from "pinia";
import { api } from "@/api";
import { DEFAULT_TIMEZONE, setAppTimezone } from "@/utils/datetime";

export interface TimezoneOption {
  value: string;
  label: string;
}

interface DisplaySettingsPayload {
  timezone: string;
  timezone_options: TimezoneOption[];
  panel_public_url: string;
  backend_port?: number;
  panel_port?: number | null;
}

export const useAppSettingsStore = defineStore("appSettings", {
  state: () => ({
    timezone: DEFAULT_TIMEZONE,
    timezoneOptions: [] as TimezoneOption[],
    panelPublicUrl: "",
    backendPort: 0,
    panelPort: null as number | null,
    loaded: false,
  }),
  actions: {
    applyDisplay(data: DisplaySettingsPayload) {
      this.timezone = data.timezone || DEFAULT_TIMEZONE;
      this.timezoneOptions = data.timezone_options || [];
      this.panelPublicUrl = data.panel_public_url || "";
      this.backendPort = Number(data.backend_port) || 0;
      this.panelPort = data.panel_port ?? null;
      setAppTimezone(this.timezone);
    },
    async fetch() {
      const resp = await api.get<DisplaySettingsPayload>("/api/v1/settings/display");
      this.applyDisplay(resp.data);
      this.loaded = true;
    },
    async updateDisplay(payload: { timezone: string; panel_public_url: string }) {
      const resp = await api.put<DisplaySettingsPayload>("/api/v1/settings/display", payload);
      this.applyDisplay({
        ...resp.data,
        timezone_options: resp.data.timezone_options || this.timezoneOptions,
      });
    },
    /** @deprecated use updateDisplay */
    async updateTimezone(timezone: string) {
      await this.updateDisplay({
        timezone,
        panel_public_url: this.panelPublicUrl || "http://127.0.0.1:9000",
      });
    },
  },
});
