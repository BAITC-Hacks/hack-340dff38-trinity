// Vite's optional Windows network-drive discovery requires subprocess pipes.
// Skip only this optimization in restricted sandboxes; use normal realpath resolution.
import childProcess from "node:child_process";
import { syncBuiltinESMExports } from "node:module";
import { EventEmitter } from "node:events";
const exec = childProcess.exec;
childProcess.exec = function (command, ...args) {
  if (command === "net use") {
    const callback = args.find((value) => typeof value === "function");
    queueMicrotask(() =>
      callback?.(new Error("Optional network-drive discovery disabled"), ""),
    );
    return new EventEmitter();
  }
  return exec.call(this, command, ...args);
};
syncBuiltinESMExports();
