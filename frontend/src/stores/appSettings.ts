import { defineStore } from "pinia";
import { api } from "@/api";
import { DEFAULT_TIMEZONE, setAppTimezone } from "@/utils/datetime";

export interface TimezoneOption {
  value: string;
  label: string;
}

export const useAppSettingsStore = defineStore("appSettings", {
  state: () => ({
    timezone: DEFAULT_TIMEZONE,
    timezoneOptions: [] as TimezoneOption[],
    panelPublicUrl: "",
    loaded: false,
  }),
  actions: {
    async fetch() {
      const resp = await api.get<{
        timezone: string;
        timezone_options: TimezoneOption[];
        panel_public_url: string;
      }>("/api/v1/settings/display");
      this.timezone = resp.data.timezone || DEFAULT_TIMEZONE;
      this.timezoneOptions = resp.data.timezone_options || [];
      this.panelPublicUrl = resp.data.panel_public_url || "";
      setAppTimezone(this.timezone);
      this.loaded = true;
    },
    async updateDisplay(payload: { timezone: string; panel_public_url: string }) {
      const resp = await api.put<{
        timezone: string;
        timezone_options: TimezoneOption[];
        panel_public_url: string;
      }>("/api/v1/settings/display", payload);
      this.timezone = resp.data.timezone;
      this.timezoneOptions = resp.data.timezone_options || this.timezoneOptions;
      this.panelPublicUrl = resp.data.panel_public_url;
      setAppTimezone(this.timezone);
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
