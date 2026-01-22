import {
  findClosestIonContent,
  scrollToTop
} from "./chunk-U6MZRPXL.js";
import {
  readTask,
  writeTask
} from "./chunk-K5V26ZHC.js";
import {
  componentOnReady
} from "./chunk-J5OOJT5F.js";
import "./chunk-CRGITIGP.js";
import "./chunk-HYZMROOS.js";

// ../../node_modules/@ionic/core/components/status-tap.js
var startStatusTap = () => {
  const win = window;
  win.addEventListener("statusTap", () => {
    readTask(() => {
      const width = win.innerWidth;
      const height = win.innerHeight;
      const el = document.elementFromPoint(width / 2, height / 2);
      if (!el) {
        return;
      }
      const contentEl = findClosestIonContent(el);
      if (contentEl) {
        new Promise((resolve) => componentOnReady(contentEl, resolve)).then(() => {
          writeTask(async () => {
            contentEl.style.setProperty("--overflow", "hidden");
            await scrollToTop(contentEl, 300);
            contentEl.style.removeProperty("--overflow");
          });
        });
      }
    });
  });
};
export {
  startStatusTap
};
//# sourceMappingURL=status-tap-6FMHJINH.js.map
