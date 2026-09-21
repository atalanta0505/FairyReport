import { createApp } from "vue";
import { createPinia } from "pinia";
import App from "./App.vue";
import { invoke } from "@tauri-apps/api/core";

function log(msg: string) {
  try {
    invoke("log_from_js", { msg });
  } catch {
    /* ignore */
  }
}

window.addEventListener("error", (e) => {
  log(`WINDOW ERROR: ${e.message} (${e.filename}:${e.lineno})`);
});
window.addEventListener("unhandledrejection", (e) => {
  log(`UNHANDLED REJECTION: ${e.reason}`);
});

log("Vue app initializing");
const app = createApp(App);
app.config.errorHandler = (err, _instance, info) => {
  log(`VUE ERROR: ${err} (info: ${info})`);
};
app.use(createPinia()).mount("#app");

