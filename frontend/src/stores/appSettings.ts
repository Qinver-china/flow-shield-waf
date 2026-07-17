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
    loaded: false,
  }),
  actions: {
    async fetch() {
      const resp = await api.get<{
        timezone: string;
        timezone_options: TimezoneOption[];
      }>("/api/v1/settings/display");
      this.timezone = resp.data.timezone || DEFAULT_TIMEZONE;
      this.timezoneOptions = resp.data.timezone_options || [];
      setAppTimezone(this.timezone);
      this.loaded = true;
    },
    async updateTimezone(timezone: string) {
      const resp = await api.put<{
        timezone: string;
        timezone_options: TimezoneOption[];
      }>("/api/v1/settings/display", { timezone });
      this.timezone = resp.data.timezone;
      this.timezoneOptions = resp.data.timezone_options || this.timezoneOptions;
      setAppTimezone(this.timezone);
    },
  },
});
