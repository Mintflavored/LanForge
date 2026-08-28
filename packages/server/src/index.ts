import { createLanForgeServer } from "./server.js";

const PORT = parseInt(process.env.PORT || "8787", 10);
const server = createLanForgeServer(PORT);

server.start().catch((err) => {
  console.error("Failed to start LANForge server:", err);
  process.exit(1);
});
