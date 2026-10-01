// Compatibility entry point: v2 browser-independent decision/data regression suite.
const {spawnSync}=require("node:child_process");
const path=require("node:path");
process.exit(spawnSync(process.execPath,["--test",path.join(__dirname,"v2.test.mjs")],{stdio:"inherit"}).status??1);
