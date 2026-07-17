import { createPinia } from "pinia";
import { createApp } from "vue";
import Antd from "ant-design-vue";
import "ant-design-vue/dist/reset.css";
import "./styles/tokens.css";
import "./styles/global.css";
import "./styles/form-surfaces.css";
import "./styles/transitions.css";
import App from "./App.vue";
import router from "./router";
import { useThemeStore } from "./stores/theme";
import { DEFAULT_TIMEZONE, setAppTimezone } from "./utils/datetime";

setAppTimezone(DEFAULT_TIMEZONE);

const app = createApp(App);
const pinia = createPinia();
app.use(pinia);
app.use(router);
app.use(Antd);

// Apply persisted theme before mount
useThemeStore(pinia);

app.mount("#app");
